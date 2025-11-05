# Critical Bug Fix: Subagent Name Inheritance

## The Bug

### Original Implementation (BROKEN)
```python
def before_agent(self, state: dict, config: Any) -> dict | None:
    # Only inject if not already present (avoid overwriting)
    if "agent_name" not in state:
        return {"agent_name": self.agent_name}
    return None  # ❌ BUG: Doesn't overwrite inherited name
```

### Why It Failed

**Scenario:**
1. Main agent: `AgentNameMiddleware("main-research-agent")`
   - Sets `state["agent_name"] = "main-research-agent"`

2. Main agent spawns subagent via `task` tool
   - `subagents.py:331` creates subagent state:
     ```python
     subagent_state = {k: v for k, v in runtime.state.items() if k not in _EXCLUDED_STATE_KEYS}
     ```
   - `_EXCLUDED_STATE_KEYS = ("messages", "todos")` only
   - **`agent_name` is NOT excluded** → gets copied to subagent ❌

3. Subagent starts with `state["agent_name"] = "main-research-agent"` (inherited)
   - Subagent's `AgentNameMiddleware("research-agent")` runs
   - Checks: `if "agent_name" not in state:` → **False!** (key exists)
   - Returns `None` → **doesn't overwrite**
   - Subagent keeps parent's name ❌

**Result:** All subagents log with the main agent's name!

---

## The Fix

### New Implementation (CORRECT)
```python
def before_agent(self, state: dict, config: Any) -> dict | None:
    # Always set agent_name to ensure subagents get their own name
    # (subagents inherit parent state, so we must overwrite)
    return {"agent_name": self.agent_name}  # ✅ Always overwrite
```

### Why It Works

**Scenario:**
1. Main agent: `AgentNameMiddleware("main-research-agent")`
   - Sets `state["agent_name"] = "main-research-agent"` ✅

2. Main agent spawns subagent
   - Subagent inherits `state["agent_name"] = "main-research-agent"`

3. Subagent's `AgentNameMiddleware("research-agent")` runs
   - **Always returns** `{"agent_name": "research-agent"}` ✅
   - **Overwrites** inherited value
   - Subagent now has its own name ✅

**Result:** Each agent logs with its own name! 🎉

---

## Why This Matters

Without this fix:
```
🧠 LLM Response agent=main-research-agent tools=['task']
🦊 Subagent task delegated agent=main-research-agent subagent=research-agent
🧠 LLM Response agent=main-research-agent tools=['internet_search']  ❌ WRONG!
🐶 Búsqueda web completada agent=main-research-agent  ❌ WRONG!
```

With this fix:
```
🧠 LLM Response agent=main-research-agent tools=['task']
🦊 Subagent task delegated agent=main-research-agent subagent=research-agent
🧠 LLM Response agent=research-agent tools=['internet_search']  ✅ CORRECT!
🐶 Búsqueda web completada agent=research-agent  ✅ CORRECT!
```

---

## Key Insight

**Subagents inherit most parent state** (except "messages" and "todos").

Since `agent_name` is in state:
- ❌ **Conditional check** (`if "agent_name" not in state`) doesn't work
- ✅ **Always overwrite** is the correct approach

This pattern is necessary because:
1. Each agent needs its own identity
2. Subagents receive a copy of parent state
3. State keys are NOT automatically scoped per agent

---

## Files Changed

- `libs/deepagents/middleware/agent_name.py` - Removed conditional check, always set agent_name
