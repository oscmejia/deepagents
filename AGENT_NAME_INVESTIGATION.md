# Investigation: Accessing Agent Name in Middleware

## Problem
The `DeepAgentMiddleware` needs to identify which agent (main or subagent) is making LLM calls and tool calls for proper monitoring and logging.

## What's Available in Middleware

### ModelRequest (in `wrap_model_call`)
Available attributes:
- `request.state` - Agent state dictionary (shared across middleware)
- `request.messages` - Message history
- `request.system_prompt` - System prompt
- `request.config` - *(potentially available)* Configuration dict

### ToolCallRequest (in `wrap_tool_call`)
Available attributes:
- `request.state` - Agent state dictionary
- `request.runtime` - ToolRuntime object with:
  - `request.runtime.state` - Same as request.state
  - `request.runtime.config` - Configuration dict
  - `request.runtime.tool_call_id` - Tool call ID
- `request.tool_call` - Tool call dict with `name`, `args`, `id`
- `request.tool` - Tool object

## Findings

### 1. Agent Name from `create_deep_agent(name="...")`
The `name` parameter in `create_deep_agent()` is passed to `create_agent()` but:
- ❌ **NOT automatically stored in state**
- ❓ **MAY be accessible via `runtime.config` or graph metadata**
- ✅ **Can be manually injected into state**

### 2. Subagent Names
When subagents are called via the `task` tool:
- ✅ **Subagent type IS available** in `request.tool_call['args']['subagent_type']` when the task tool is called
- ❌ **NOT available during the subagent's own LLM/tool calls** (subagent runs in isolated context)

### 3. State is Shared
- ✅ State dict is accessible in both `wrap_model_call` and `wrap_tool_call`
- ✅ State is shared between main agent and can be passed to subagents (with exclusions)
- ✅ Custom keys can be added to state

## Solutions

### Solution 1: Use `runtime.config` (Needs Testing)
```python
def wrap_model_call(self, request: Any, handler: Any) -> Any:
    agent_name = "main"
    if hasattr(request, 'config') and 'configurable' in request.config:
        # Check if graph name is in config
        agent_name = request.config.get('configurable', {}).get('graph_id', 'main')

    logger.info(f"🧠 LLM call from agent: {agent_name}")
    return handler(request)
```

### Solution 2: Agent Name Injection Middleware (Recommended)
Create a middleware that injects agent name into state:

```python
class AgentNameMiddleware(AgentMiddleware):
    """Middleware to inject agent name into state for tracking."""

    def __init__(self, agent_name: str):
        super().__init__()
        self.agent_name = agent_name

    def before_agent(self, state: dict, config: Any) -> dict | None:
        """Inject agent name into state before agent runs."""
        return {"agent_name": self.agent_name}
```

Then use in monitoring middleware:
```python
def wrap_model_call(self, request: Any, handler: Any) -> Any:
    agent_name = request.state.get('agent_name', 'unknown')
    logger.info(f"🧠 LLM call from agent: {agent_name}")
    return handler(request)
```

### Solution 3: Track Task Tool Calls
Track when subagents are spawned and infer context:

```python
def wrap_tool_call(self, request: Any, handler: Any) -> Any:
    tool_name = request.tool_call.get('name', 'Unknown')

    if tool_name == 'task':
        # Capture subagent name
        subagent_type = request.tool_call['args'].get('subagent_type', 'unknown')
        logger.info(f"🦊 Spawning subagent: {subagent_type}")

    result = handler(request)
    return result
```

## Recommendation

**Use Solution 2 (Agent Name Injection)** because:
1. ✅ Clean and explicit
2. ✅ Works for both main and subagents
3. ✅ No assumptions about internal implementation
4. ✅ Easily testable

## Implementation Steps

1. Create `AgentNameMiddleware` to inject names into state
2. Update `DeepAgentMiddleware` to read from `request.state['agent_name']`
3. Apply `AgentNameMiddleware` to main agent and all subagents
4. Update research_agent.py example to demonstrate usage

## Testing Needed

- [ ] Verify `runtime.config` contains agent/graph name
- [ ] Test state propagation to subagents
- [ ] Confirm agent_name persists across tool calls
