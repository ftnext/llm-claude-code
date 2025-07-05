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

    def _process_message_content(self, content):
        """Process message content and return formatted text"""
        if isinstance(content, str):
            return content
        elif hasattr(content, "text"):
            return content.text
        elif isinstance(content, list):
            # Handle list of TextBlock objects
            result_text = ""
            for block in content:
                # Handle ToolUseBlock
                if hasattr(block, "name") or "ToolUse" in str(type(block)):
                    tool_name = getattr(block, "name", "Unknown")
                    tool_input = getattr(block, "input", {})
                    if tool_name == "Write":
                        file_path = tool_input.get("file_path", "unknown")
                        result_text += (
                            f"\n🔧 [Tool: Write] Creating file '{file_path}'\n"
                        )
                    elif tool_name == "Read":
                        file_path = tool_input.get("file_path", "unknown")
                        result_text += f"\n🔧 [Tool: Read] Reading file '{file_path}'\n"
                    else:
                        result_text += f"\n🔧 [Tool: {tool_name}] Executing\n"
                    continue
                # Handle tool result blocks
                elif hasattr(block, "type") and "tool_result" in str(
                    getattr(block, "type", "")
                ):
                    result_text += "✅ Tool execution completed\n"
                    continue
                # Handle text blocks
                if hasattr(block, "text"):
                    result_text += block.text
                elif hasattr(block, "type") and block.type == "text":
                    result_text += getattr(block, "text", "")
                else:
                    # Only include if it doesn't look like a tool block
                    block_str = str(block)
                    if not block_str.startswith("ToolUse") and not block_str.startswith(
                        "{'tool"
                    ):
                        result_text += block_str
            return result_text
        else:
            return str(content)

    async def _execute_single(self, prompt) -> str:
        """Execute single prompt without streaming"""
        try:
            messages = []

            async for message in query(
                prompt=prompt.prompt,
                options=ClaudeCodeOptions(max_turns=1, allowed_tools=["Read", "Write"]),
            ):
                messages.append(message)

            # Extract text content from messages
            result_text = ""
            for message in messages:
                if hasattr(message, "content") and message.content:
                    result_text += self._process_message_content(message.content)

            return self._format_output(result_text)

        except Exception as e:
            raise ProcessError(f"Failed to execute Claude Code SDK: {str(e)}")

    async def _stream_execute(self, prompt) -> AsyncGenerator[str, None]:
        """Execute prompt with streaming"""
        try:
            async for message in query(
                prompt=prompt.prompt,
                options=ClaudeCodeOptions(max_turns=1, allowed_tools=["Read", "Write"]),
            ):
                if hasattr(message, "content") and message.content:
                    content_text = self._process_message_content(message.content)
                    formatted_text = self._format_output(content_text)
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
            if line.startswith("🔧 [Tool:") or line.startswith("[Tool:"):
                # Blue color for tool messages
                formatted_lines.append(f"\033[34m{line}\033[0m")
            elif line.startswith("✅"):
                # Green color for success messages
                formatted_lines.append(f"\033[32m{line}\033[0m")
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
