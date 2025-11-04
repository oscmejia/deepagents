# Solution: Agent Name Tracking in Middleware

## Problem Solved
The `DeepAgentMiddleware` needed to identify which agent (main or subagent) was making LLM calls and tool calls for comprehensive monitoring. The agent `name` parameter from `create_deep_agent()` was not automatically accessible in middleware.

## Solution Implemented

### 1. Created `AgentNameMiddleware`
**File**: `libs/deepagents/middleware/agent_name.py`

This middleware injects the agent name into the state dictionary, making it accessible to all other middleware:

```python
class AgentNameMiddleware(AgentMiddleware):
    def __init__(self, agent_name: str):
        super().__init__()
        self.agent_name = agent_name

    def before_agent(self, state: dict, config: Any) -> dict | None:
        if "agent_name" not in state:
            return {"agent_name": self.agent_name}
        return None
```

### 2. Updated `DeepAgentMiddleware`
**File**: `libs/deepagents/middleware/monitoring.py`

Modified to read `agent_name` from state and include it in all logs:

**In `wrap_model_call`**:
```python
agent_name = request.state.get('agent_name', 'unknown') if hasattr(request, 'state') else 'unknown'
logger.info("🧠 LLM Response", agent=agent_name, **log_data)
```

**In `wrap_tool_call`**:
```python
agent_name = 'unknown'
if hasattr(request, 'runtime') and hasattr(request.runtime, 'state'):
    agent_name = request.runtime.state.get('agent_name', 'unknown')
elif hasattr(request, 'state'):
    agent_name = request.state.get('agent_name', 'unknown')
logger.info("🦊 File written", agent=agent_name, ...)
```

### 3. Updated Research Agent Example
**File**: `examples/research/research_agent.py`

Demonstrates proper usage:

```python
from deepagents.middleware.agent_name import AgentNameMiddleware
from deepagents.middleware.monitoring import DeepAgentMiddleware

# Main agent
agent = create_deep_agent(
    tools=[internet_search],
    system_prompt=research_instructions,
    middleware=[
        AgentNameMiddleware("main-research-agent"),
        DeepAgentMiddleware(),
    ],
    subagents=[
        {
            "name": "research-agent",
            "middleware": [AgentNameMiddleware("research-agent")],
            ...
        },
        {
            "name": "critique-agent",
            "middleware": [AgentNameMiddleware("critique-agent")],
            ...
        }
    ],
)
```

## How It Works

1. **AgentNameMiddleware** runs first and injects `agent_name` into state
2. State is shared across all middleware
3. **DeepAgentMiddleware** reads `agent_name` from state
4. All logs now include the `agent` field identifying which agent made the call

## Benefits

✅ **Clear agent identification** - All logs show which agent (main or subagent) performed each action
✅ **No magic** - Explicit middleware usage, easy to understand
✅ **Flexible** - Can be applied to any agent at any level
✅ **Backward compatible** - Falls back to "unknown" if agent name not set
✅ **Testable** - Simple state-based mechanism

## Usage Pattern

For **any agent** that needs monitoring with agent identification:

1. Import both middleware:
   ```python
   from deepagents.middleware.agent_name import AgentNameMiddleware
   from deepagents.middleware.monitoring import DeepAgentMiddleware
   ```

2. Apply to main agent:
   ```python
   middleware=[
       AgentNameMiddleware("your-agent-name"),
       DeepAgentMiddleware(),
   ]
   ```

3. Apply to each subagent:
   ```python
   subagents=[{
       "name": "subagent-name",
       "middleware": [AgentNameMiddleware("subagent-name")],
       ...
   }]
   ```

## Log Output Example

With agent name tracking, logs now show:

```
🧠 LLM Response agent=main-research-agent tools=['task', 'internet_search']
🦊 Subagent task delegated agent=main-research-agent subagent=research-agent
🧠 LLM Response agent=research-agent tools=['internet_search']
🐶 Búsqueda web completada agent=research-agent query='AI trends 2024'
🧠 Token Usage agent=research-agent prompt_tokens=1234 total_tokens=2000
```

## Files Changed

1. ✅ `libs/deepagents/middleware/agent_name.py` - NEW
2. ✅ `libs/deepagents/middleware/monitoring.py` - UPDATED
3. ✅ `examples/research/research_agent.py` - UPDATED
4. ✅ `AGENT_NAME_INVESTIGATION.md` - NEW (documentation)
5. ✅ `SOLUTION_SUMMARY.md` - NEW (this file)
