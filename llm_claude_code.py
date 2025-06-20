import time
from typing import AsyncGenerator

import anyio
import llm
from claude_code_sdk import ClaudeCodeOptions, query


class CLINotFoundError(Exception):
    """Claude CLI not found error"""

    pass


class CLIConnectionError(Exception):
    """Claude CLI connection error"""

    pass


class ProcessError(Exception):
    """Process execution error"""

    pass


class ClaudeCode(llm.Model):
    model_id = "claude-code"
    can_stream = True

    def execute(self, prompt, stream, response, conversation=None):
        """Execute prompt using Claude Code SDK"""
        start_time = time.time()

        try:
            if stream:
                return self._sync_stream_execute(prompt, response, start_time)
            else:
                result = anyio.run(self._execute_single, prompt)
                response.response_json = {
                    "execution_time": time.time() - start_time,
                    "model_id": self.model_id,
                }
                return [result]

        except Exception as e:
            error_msg = f"Error executing Claude Code: {str(e)}"
            response.response_json = {
                "error": error_msg,
                "execution_time": time.time() - start_time,
            }
            raise ProcessError(error_msg)

    def _sync_stream_execute(self, prompt, response, start_time):
        """Synchronous wrapper for streaming execution"""

        def stream_generator():
            try:

                async def async_gen():
                    async for chunk in self._stream_execute(prompt):
                        yield chunk

                for chunk in anyio.run(self._collect_async_generator, async_gen()):
                    yield chunk

                response.response_json = {
                    "execution_time": time.time() - start_time,
                    "model_id": self.model_id,
                }
            except Exception as e:
                error_msg = f"Error streaming Claude Code: {str(e)}"
                response.response_json = {
                    "error": error_msg,
                    "execution_time": time.time() - start_time,
                }
                raise ProcessError(error_msg)

        return stream_generator()

    async def _collect_async_generator(self, async_gen):
        """Collect all items from an async generator"""
        results = []
        async for item in async_gen:
            results.append(item)
        return results

    async def _execute_single(self, prompt) -> str:
        """Execute single prompt without streaming"""
        try:
            messages = []

            async for message in query(
                prompt=prompt.prompt,
                options=ClaudeCodeOptions(max_turns=1, allowed_tools=[]),
            ):
                messages.append(message)

            # Extract text content from messages
            result_text = ""
            for message in messages:
                if hasattr(message, "content") and message.content:
                    if isinstance(message.content, str):
                        result_text += message.content
                    elif hasattr(message.content, "text"):
                        result_text += message.content.text
                    elif isinstance(message.content, list):
                        # Handle list of TextBlock objects
                        for block in message.content:
                            if hasattr(block, "text"):
                                result_text += block.text
                            else:
                                result_text += str(block)
                    else:
                        result_text += str(message.content)

            return self._format_output(result_text)

        except Exception as e:
            raise ProcessError(f"Failed to execute Claude Code SDK: {str(e)}")

    async def _stream_execute(self, prompt) -> AsyncGenerator[str, None]:
        """Execute prompt with streaming"""
        try:
            async for message in query(
                prompt=prompt.prompt,
                options=ClaudeCodeOptions(max_turns=1, allowed_tools=[]),
            ):
                if hasattr(message, "content") and message.content:
                    if isinstance(message.content, str):
                        formatted_text = self._format_output(message.content)
                        if formatted_text.strip():
                            yield formatted_text
                    elif hasattr(message.content, "text"):
                        formatted_text = self._format_output(message.content.text)
                        if formatted_text.strip():
                            yield formatted_text
                    elif isinstance(message.content, list):
                        # Handle list of TextBlock objects
                        for block in message.content:
                            if hasattr(block, "text"):
                                formatted_text = self._format_output(block.text)
                                if formatted_text.strip():
                                    yield formatted_text
                            else:
                                formatted_text = self._format_output(str(block))
                                if formatted_text.strip():
                                    yield formatted_text
                    else:
                        formatted_text = self._format_output(str(message.content))
                        if formatted_text.strip():
                            yield formatted_text

        except Exception as e:
            raise ProcessError(f"Failed to stream Claude Code SDK: {str(e)}")

    def _format_output(self, output: str) -> str:
        """Format output with color coding"""
        if not output.strip():
            return ""

        lines = output.strip().split("\n")
        formatted_lines = []

        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue

            # Color coding for different message types
            if line.startswith("[Tool:"):
                # Blue color for tool messages
                formatted_lines.append(f"\033[34m{line}\033[0m")
            elif "error" in line.lower() or "failed" in line.lower():
                # Red color for errors
                formatted_lines.append(f"\033[31m{line}\033[0m")
            elif line.startswith("✓"):
                # Green color for success messages
                formatted_lines.append(f"\033[32m{line}\033[0m")
            else:
                # Default color for assistant messages
                formatted_lines.append(line)

        return "\n".join(formatted_lines)


@llm.hookimpl
def register_models(register):
    register(ClaudeCode(), aliases=("cc",))
