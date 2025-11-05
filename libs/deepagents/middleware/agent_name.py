"""
Agent Name Middleware for tracking agent identity in monitoring.

This middleware injects the agent name into the state so that monitoring
middleware can identify which agent (main or subagent) is making calls.
"""

from typing import Any

from langchain.agents.middleware.types import AgentMiddleware


class AgentNameMiddleware(AgentMiddleware):
    """Middleware to inject agent name into state for tracking.

    This middleware adds an 'agent_name' key to the agent state, making it
    accessible to other middleware (like monitoring middleware) to identify
    which agent is currently executing.

    Args:
        agent_name: The name of the agent (e.g., "main", "research-agent", "critique-agent")

    Example:
        ```python
        from deepagents import create_deep_agent
        from deepagents.middleware.agent_name import AgentNameMiddleware
        from deepagents.middleware.monitoring import DeepAgentMiddleware

        # Create main agent with name tracking
        agent = create_deep_agent(
            tools=[internet_search],
            system_prompt=research_instructions,
            middleware=[
                AgentNameMiddleware("main-agent"),
                DeepAgentMiddleware(),
            ],
            subagents=[
                {
                    "name": "research-agent",
                    "description": "Research subagent",
                    "system_prompt": "You are a researcher",
                    "tools": [internet_search],
                    "middleware": [AgentNameMiddleware("research-agent")],
                }
            ],
        )
        ```
    """

    def __init__(self, agent_name: str):
        """Initialize the AgentNameMiddleware.

        Args:
            agent_name: The name to assign to this agent.
        """
        super().__init__()
        self.agent_name = agent_name

    def before_agent(self, state: dict, config: Any) -> dict | None:
        """Inject agent name into state before agent runs.

        Args:
            state: Current agent state.
            config: Agent configuration.

        Returns:
            State update with agent_name injected.
        """
        # Always set agent_name to ensure subagents get their own name
        # (subagents inherit parent state, so we must overwrite)
        return {"agent_name": self.agent_name}
