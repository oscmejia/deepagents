"""
DeepAgents Unified Middleware.

Comprehensive monitoring and logging for DeepAgents:
- LLM call monitoring (message counts, tool calls, token usage)
- Planning tool tracking (write_todos, write_file, edit_file, task)
- Native external tool tracking (internet_search, url_fetch, web_scrape, api_call)

This middleware provides visibility into agent decision-making without
performing RT messaging, DB storage, or credit deduction.
"""

import json
from typing import Any

import structlog
from langchain.agents.middleware.types import AgentMiddleware

logger = structlog.get_logger(__name__)


class DeepAgentMiddleware(AgentMiddleware):
    """Unified middleware for comprehensive DeepAgent monitoring."""

    # ========================================================================
    # LLM CALL MONITORING
    # ========================================================================

    def wrap_model_call(self, request: Any, handler: Any) -> Any:
        """
        Intercept synchronous LLM calls.

        Args:
            request: Model request with messages
            handler: Function to execute the actual LLM call

        Returns:
            Model response
        """
        # Get agent name from state (if available)
        agent_name = request.state.get('agent_name', 'unknown') if hasattr(request, 'state') else 'unknown'

        message_count = len(request.messages) if hasattr(request, 'messages') else 0

        # Execute the model
        response = handler(request)
        logger.info(" ")
        try:
            # Extract AIMessage from ModelResponse structure
            # Response structure: ModelResponse(result=[AIMessage(...)])
            if hasattr(response, 'result') and response.result:
                ai_message = response.result[0]

                # Collect LLM response info
                log_data = {}

                # Extract content (LLM intention/thinking)
                if hasattr(ai_message, 'content') and ai_message.content:
                    content = str(ai_message.content).strip()
                    if content:
                        log_data['content'] = content

                # Extract tool calls
                if hasattr(ai_message, 'tool_calls') and ai_message.tool_calls:
                    tool_count = len(ai_message.tool_calls)
                    tool_names = [
                        tool_call.get('name') if isinstance(tool_call, dict) else tool_call.name
                        for tool_call in ai_message.tool_calls
                    ]
                    log_data['tool_count'] = tool_count
                    log_data['tools'] = tool_names

                # Log combined LLM response (intention + tool calls)
                if log_data:
                    logger.info("🧠 LLM Response", agent=agent_name, **log_data)

                # Log token usage separately
                if hasattr(ai_message, 'response_metadata'):
                    token_usage = ai_message.response_metadata.get('token_usage', {})
                    if token_usage:
                        logger.info(
                            "🧠 Token Usage",
                            agent=agent_name,
                            prompt_tokens=token_usage.get('prompt_tokens', 0),
                            completion_tokens=token_usage.get('completion_tokens', 0),
                            total_tokens=token_usage.get('total_tokens', 0)
                        )
        except Exception as e:
            logger.warning("🧠⚠️ Could not parse LLM response", error=str(e))

        logger.info(" ")
        return response

    async def awrap_model_call(self, request: Any, handler: Any) -> Any:
        """Async model wrapper - adds warning if this path is ever used."""
        logger.warning("🧠⚠️ ASYNC LLM CALL DETECTED")
        return await handler(request)

    # ========================================================================
    # TOOL CALL MONITORING
    # ========================================================================

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        """
        Intercept synchronous tool calls for all tool types.

        Args:
            request: ToolCallRequest with tool_call dict containing name, args, id
            handler: Function to execute the actual tool call

        Returns:
            Tool result (usually ToolMessage)
        """
        # Get agent name from state (try runtime.state first, then request.state)
        agent_name = 'unknown'
        if hasattr(request, 'runtime') and hasattr(request.runtime, 'state'):
            agent_name = request.runtime.state.get('agent_name', 'unknown')
        elif hasattr(request, 'state'):
            agent_name = request.state.get('agent_name', 'unknown')

        # Execute the tool
        result = handler(request)

        # Extract tool info from request (result may be Command object without 'name')
        tool_name = request.tool_call.get('name', 'Unknown')
        output_type = type(result).__name__

        # Route to appropriate handler
        if tool_name == 'write_todos':
            self._handle_write_todos(request, result, output_type, agent_name)
        elif tool_name == 'write_file':
            self._handle_write_file(request, result, output_type, agent_name)
        elif tool_name == 'edit_file':
            self._handle_edit_file(request, result, output_type, agent_name)
        elif tool_name == 'read_file':
            self._handle_read_file(request, result, output_type, agent_name)
        elif tool_name == 'task':
            self._handle_task(request, result, output_type, agent_name)
        elif tool_name == 'internet_search':
            self._handle_internet_search(request, result, output_type, agent_name)
        # TODO: Implement url_fetch handler (expected args: url)
        # TODO: Implement web_scrape handler (expected args: url, selectors)
        # TODO: Implement api_call handler (expected args: endpoint, method, params)
        else:
            # Warn for unknown tools (helps discover new tools to add)
            logger.warning("⚠️ UNKNOWN DeepAgent TOOL COMPLETED", tool_name=tool_name, output_type=output_type, result=result)
            logger.warning(request)

        return result

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        """Async tool wrapper - adds warning if this path is ever used."""
        tool_name = getattr(request, 'tool_call', {}).get('name', 'Unknown')
        logger.warning("⚠️ ASYNC TOOL CALL DETECTED", tool_name=tool_name)
        logger.warning(request)
        return await handler(request)

    # ========================================================================
    # PLANNING TOOL HANDLERS
    # ========================================================================

    def _handle_write_todos(self, request: Any, result: Any, output_type: str, agent_name: str) -> None:
        """Handle write_todos tool - show detailed task list with status."""
        try:
            if hasattr(request, 'tool_call') and 'args' in request.tool_call:
                todos = request.tool_call['args'].get('todos', [])
                task_count = len(todos)

                # Log structured data
                logger.info("🦊 Planning todos created", agent=agent_name, task_count=task_count, output_type=output_type)

                # Display formatted todo list
                print(f"   📋 Tasks ({task_count}):")
                for i, todo in enumerate(todos, 1):
                    status = todo.get('status', 'pending')
                    content = todo.get('content', 'unknown task')

                    # Status emoji mapping
                    status_emoji = {
                        'pending': '⏳',
                        'in_progress': '🔄',
                        'completed': '✅'
                    }.get(status, '❓')

                    print(f"   {i}. {status_emoji} {content}")
        except Exception as e:
            logger.warning("🦊⚠️ Could not parse write_todos args", error=str(e))

    def _handle_write_file(self, request: Any, result: Any, output_type: str, agent_name: str) -> None:
        """Handle write_file tool - show file path, content preview, and size."""
        try:
            if hasattr(request, 'tool_call') and 'args' in request.tool_call:
                file_path = request.tool_call['args'].get('file_path', 'unknown')
                content = request.tool_call['args'].get('content', '')
                content_preview = content[:100] + '...' if len(content) > 100 else content
                logger.info(
                    "🦊 File written",
                    agent=agent_name,
                    file_path=file_path,
                    content_preview=content_preview,
                    size_chars=len(content)
                )
        except Exception as e:
            logger.warning("🦊⚠️ Could not parse write_file args", error=str(e))

    def _handle_edit_file(self, request: Any, result: Any, output_type: str, agent_name: str) -> None:
        """Handle edit_file tool - show file path, content preview, and size."""
        try:
            if hasattr(request, 'tool_call') and 'args' in request.tool_call:
                file_path = request.tool_call['args'].get('file_path', 'unknown')
                new_string = request.tool_call['args'].get('new_string', '')
                content_preview = new_string[:100] + '...' if len(new_string) > 100 else new_string
                logger.info(
                    "🦊 File edited",
                    agent=agent_name,
                    file_path=file_path,
                    content_preview=content_preview,
                    size_chars=len(new_string)
                )
        except Exception as e:
            logger.warning("🦊⚠️ Could not parse edit_file args", error=str(e))

    def _handle_read_file(self, request: Any, result: Any, output_type: str, agent_name: str) -> None:
        """Handle read_file tool - show file path and content size."""
        try:
            if hasattr(request, 'tool_call') and 'args' in request.tool_call:
                file_path = request.tool_call['args'].get('file_path', 'unknown')

                # Get content from result (ToolMessage)
                content = result.content if hasattr(result, 'content') else ''
                line_count = content.count('\n') if content else 0

                logger.info(
                    "🦊 File read",
                    agent=agent_name,
                    file_path=file_path,
                    lines=line_count,
                    output_type=output_type
                )
        except Exception as e:
            logger.warning("🦊⚠️ Could not parse read_file args", error=str(e))

    def _handle_task(self, request: Any, result: Any, output_type: str, agent_name: str) -> None:
        """Handle task tool - show subagent delegation."""
        try:
            if hasattr(request, 'tool_call') and 'args' in request.tool_call:
                subagent_type = request.tool_call['args'].get('subagent_type', 'unknown')
                description = request.tool_call['args'].get('description', '')
                description_preview = description[:100] + '...' if len(description) > 100 else description
                logger.info(
                    "🦊 Subagent task delegated",
                    agent=agent_name,
                    subagent=subagent_type,
                    description=description_preview,
                    output_type=output_type
                )
        except Exception as e:
            logger.warning("🦊⚠️ Could not parse task args", error=str(e))

    # ========================================================================
    # NATIVE EXTERNAL TOOL HANDLERS
    # ========================================================================

    def _handle_internet_search(self, request: Any, result: Any, output_type: str, agent_name: str) -> None:
        """Handle internet_search tool - parse JSON and show query + result count."""
        try:
            # Parse result content (may be JSON string or dict)
            content_data = json.loads(result.content) if isinstance(result.content, str) else result.content
            query = content_data.get('query', 'unknown query')
            result_count = len(content_data.get('results', []))

            # Calculate approximate word count (similar to google_serper)
            # Estimate: each result has ~100 words on average
            word_count = result_count * 100
        except Exception:
            query = 'unknown query'
            result_count = 0
            word_count = 0

        # Match google_serper format from Pydantic AI callbacks
        logger.info(
            f"🐶 Búsqueda web completada: '{query}' (~{word_count} palabras encontradas)",
            agent=agent_name,
            tool="internet_search",
            query=query,
            result_count=result_count,
            output_type=output_type
        )
