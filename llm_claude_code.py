import sys
import time
from collections.abc import AsyncGenerator

import anyio
import llm
from claude_code_sdk import ClaudeCodeOptions, query
from pydantic import Field

# Constants
MAX_PROMPT_DISPLAY_LENGTH = 100
MAX_COMMAND_DISPLAY_LENGTH = 50


class CLINotFoundError(Exception):
    """Claude CLI not found error"""


class CLIConnectionError(Exception):
    """Claude CLI connection error"""


class ProcessError(Exception):
    """Process execution error"""


class ClaudeCode(llm.Model):
    model_id = "claude-code"
    can_stream = True

    class Options(llm.Options):
        debug: bool | None = Field(
            description="Enable debug output to show tool execution details",
            default=False,
        )

    def execute(self, prompt, stream, response, conversation=None):  # noqa: ARG002
        """Execute prompt using Claude Code SDK"""
        start_time = time.time()

        # Check for debug option
        debug = False
        if hasattr(prompt, "options") and prompt.options:
            debug = prompt.options.debug or False

        if debug:
            sys.stderr.write("🐛 [DEBUG] Starting execution with debug mode enabled\n")
            prompt_display = prompt.prompt[:MAX_PROMPT_DISPLAY_LENGTH] + (
                "..." if len(prompt.prompt) > MAX_PROMPT_DISPLAY_LENGTH else ""
            )
            sys.stderr.write(f"🐛 [DEBUG] Prompt: {prompt_display}\n")
            sys.stderr.write(f"🐛 [DEBUG] Stream mode: {stream}\n")

        try:
            if stream:
                return self._sync_stream_execute(prompt, response, start_time, debug=debug)

        except ProcessError:
            raise
        except Exception as e:
            error_msg = f"Error executing Claude Code: {e!s}"
            response.response_json = {
                "error": error_msg,
                "execution_time": time.time() - start_time,
            }
            raise ProcessError(error_msg) from e
        else:
            result = anyio.run(self._execute_single, prompt, debug=debug)
            response.response_json = {
                "execution_time": time.time() - start_time,
                "model_id": self.model_id,
            }
            return [result]

    def _sync_stream_execute(self, prompt, response, start_time, *, debug=False):
        """Synchronous wrapper for streaming execution"""

        def stream_generator():
            try:

                async def async_gen():
                    async for chunk in self._stream_execute(prompt, debug=debug):
                        yield chunk

                yield from anyio.run(self._collect_async_generator, async_gen())

                response.response_json = {
                    "execution_time": time.time() - start_time,
                    "model_id": self.model_id,
                }
            except ProcessError:
                raise
            except Exception as e:
                error_msg = f"Error streaming Claude Code: {e!s}"
                response.response_json = {
                    "error": error_msg,
                    "execution_time": time.time() - start_time,
                }
                raise ProcessError(error_msg) from e

        return stream_generator()

    async def _collect_async_generator(self, async_gen):
        """Collect all items from an async generator"""
        return [item async for item in async_gen]

    def _process_message_content(self, content, *, debug=False):
        """Process message content and return formatted text"""
        if isinstance(content, str):
            return content

        if hasattr(content, "text"):
            return content.text

        if isinstance(content, list):
            # Handle list of TextBlock objects
            result_text = ""
            for block in content:
                # Handle ToolUseBlock
                if hasattr(block, "name") or "ToolUse" in str(type(block)):
                    if debug:
                        sys.stderr.write(f"🐛 [DEBUG] Tool use detected: {getattr(block, 'name', 'Unknown')}\n")
                        sys.stderr.write(f"🐛 [DEBUG] Tool input: {getattr(block, 'input', {})}\n")
                    tool_name = getattr(block, "name", "Unknown")
                    tool_input = getattr(block, "input", {})
                    if tool_name == "Write":
                        file_path = tool_input.get("file_path", "unknown")
                        result_text += f"\n🔧 [Tool: Write] Creating file '{file_path}'\n"
                    elif tool_name == "Read":
                        file_path = tool_input.get("file_path", "unknown")
                        result_text += f"\n🔧 [Tool: Read] Reading file '{file_path}'\n"
                    elif tool_name == "Bash":
                        command = tool_input.get("command", "unknown command")
                        command_display = command[:MAX_COMMAND_DISPLAY_LENGTH] + (
                            "..." if len(command) > MAX_COMMAND_DISPLAY_LENGTH else ""
                        )
                        result_text += f"\n🔧 [Tool: Bash] Executing: {command_display}\n"
                    elif tool_name == "TodoRead":
                        result_text += "\n🔧 [Tool: TodoRead] Reading todo list\n"
                    elif tool_name == "TodoWrite":
                        todos_count = len(tool_input.get("todos", []))
                        result_text += f"\n🔧 [Tool: TodoWrite] Writing {todos_count} todo items\n"
                    else:
                        result_text += f"\n🔧 [Tool: {tool_name}] Executing\n"
                    continue
                # Handle tool result blocks
                if hasattr(block, "type") and "tool_result" in str(getattr(block, "type", "")):
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
                    if not block_str.startswith(("ToolUse", "{'tool")):
                        result_text += block_str
            return result_text

        return str(content)

    async def _execute_single(self, prompt, *, debug=False) -> str:
        """Execute single prompt without streaming"""
        try:
            options = ClaudeCodeOptions(
                max_turns=1,
                allowed_tools=["Read", "Write", "Bash", "TodoRead", "TodoWrite"],
            )

            if debug:
                sys.stderr.write(f"🐛 [DEBUG] Claude Code SDK options: {options}\n")

            messages = [
                message
                async for message in query(
                    prompt=prompt.prompt,
                    options=options,
                )
            ]

            # Extract text content from messages
            result_text = ""
            if debug:
                sys.stderr.write(f"🐛 [DEBUG] Processing {len(messages)} messages\n")

            for message in messages:
                if hasattr(message, "content") and message.content:
                    if debug:
                        sys.stderr.write(f"🐛 [DEBUG] Message type: {type(message).__name__}\n")
                        sys.stderr.write(f"🐛 [DEBUG] Content type: {type(message.content).__name__}\n")
                    result_text += self._process_message_content(message.content, debug=debug)

            return self._format_output(result_text)

        except ProcessError:
            raise
        except Exception as e:
            error_prefix = "Failed to execute Claude Code SDK"
            error_message = f"{error_prefix}: {e!s}"
            raise ProcessError(error_message) from e

    async def _stream_execute(self, prompt, *, debug=False) -> AsyncGenerator[str, None]:
        """Execute prompt with streaming"""
        try:
            options = ClaudeCodeOptions(
                max_turns=1,
                allowed_tools=["Read", "Write", "Bash", "TodoRead", "TodoWrite"],
            )

            if debug:
                sys.stderr.write(f"🐛 [DEBUG] Streaming with options: {options}\n")

            async for message in query(
                prompt=prompt.prompt,
                options=options,
            ):
                if hasattr(message, "content") and message.content:
                    if debug:
                        sys.stderr.write(f"🐛 [DEBUG] Streaming message type: {type(message).__name__}\n")
                        sys.stderr.write(f"🐛 [DEBUG] Streaming content type: {type(message.content).__name__}\n")
                    content_text = self._process_message_content(message.content, debug=debug)
                    formatted_text = self._format_output(content_text)
                    if formatted_text.strip():
                        yield formatted_text

        except ProcessError:
            raise
        except Exception as e:
            error_prefix = "Failed to stream Claude Code SDK"
            error_message = f"{error_prefix}: {e!s}"
            raise ProcessError(error_message) from e

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
            if line.startswith(("🔧 [Tool:", "[Tool:")):
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
