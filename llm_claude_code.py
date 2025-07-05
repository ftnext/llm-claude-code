import time
from typing import AsyncGenerator, Optional

import anyio
import llm
from claude_code_sdk import ClaudeCodeOptions, query
from pydantic import Field


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

    class Options(llm.Options):
        debug: Optional[bool] = Field(
            description="Enable debug output to show tool execution details",
            default=False,
        )

    def execute(self, prompt, stream, response, conversation=None):
        """Execute prompt using Claude Code SDK"""
        start_time = time.time()

        # Check for debug option
        debug = False
        if hasattr(prompt, "options") and prompt.options:
            debug = prompt.options.debug or False

        if debug:
            print("🐛 [DEBUG] Starting execution with debug mode enabled")
            print(
                f"🐛 [DEBUG] Prompt: {prompt.prompt[:100]}{'...' if len(prompt.prompt) > 100 else ''}"
            )
            print(f"🐛 [DEBUG] Stream mode: {stream}")

        try:
            if stream:
                return self._sync_stream_execute(prompt, response, start_time, debug)
            else:
                result = anyio.run(self._execute_single, prompt, debug)
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

    def _sync_stream_execute(self, prompt, response, start_time, debug=False):
        """Synchronous wrapper for streaming execution"""

        def stream_generator():
            try:

                async def async_gen():
                    async for chunk in self._stream_execute(prompt, debug):
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

    def _process_message_content(self, content, debug=False):
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
                    if debug:
                        print(
                            f"🐛 [DEBUG] Tool use detected: {getattr(block, 'name', 'Unknown')}"
                        )
                        print(f"🐛 [DEBUG] Tool input: {getattr(block, 'input', {})}")
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
                    elif tool_name == "Bash":
                        command = tool_input.get("command", "unknown command")
                        result_text += f"\n🔧 [Tool: Bash] Executing: {command[:50]}{'...' if len(command) > 50 else ''}\n"
                    elif tool_name == "TodoRead":
                        result_text += "\n🔧 [Tool: TodoRead] Reading todo list\n"
                    elif tool_name == "TodoWrite":
                        todos_count = len(tool_input.get("todos", []))
                        result_text += (
                            f"\n🔧 [Tool: TodoWrite] Writing {todos_count} todo items\n"
                        )
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

    async def _execute_single(self, prompt, debug=False) -> str:
        """Execute single prompt without streaming"""
        try:
            messages = []

            options = ClaudeCodeOptions(
                max_turns=1,
                allowed_tools=["Read", "Write", "Bash", "TodoRead", "TodoWrite"],
            )

            if debug:
                print(f"🐛 [DEBUG] Claude Code SDK options: {options}")

            async for message in query(
                prompt=prompt.prompt,
                options=options,
            ):
                messages.append(message)

            # Extract text content from messages
            result_text = ""
            if debug:
                print(f"🐛 [DEBUG] Processing {len(messages)} messages")

            for message in messages:
                if hasattr(message, "content") and message.content:
                    if debug:
                        print(f"🐛 [DEBUG] Message type: {type(message).__name__}")
                        print(
                            f"🐛 [DEBUG] Content type: {type(message.content).__name__}"
                        )
                    result_text += self._process_message_content(message.content, debug)

            return self._format_output(result_text)

        except Exception as e:
            raise ProcessError(f"Failed to execute Claude Code SDK: {str(e)}")

    async def _stream_execute(self, prompt, debug=False) -> AsyncGenerator[str, None]:
        """Execute prompt with streaming"""
        try:
            options = ClaudeCodeOptions(
                max_turns=1,
                allowed_tools=["Read", "Write", "Bash", "TodoRead", "TodoWrite"],
            )

            if debug:
                print(f"🐛 [DEBUG] Streaming with options: {options}")

            async for message in query(
                prompt=prompt.prompt,
                options=options,
            ):
                if hasattr(message, "content") and message.content:
                    if debug:
                        print(
                            f"🐛 [DEBUG] Streaming message type: {type(message).__name__}"
                        )
                        print(
                            f"🐛 [DEBUG] Streaming content type: {type(message.content).__name__}"
                        )
                    content_text = self._process_message_content(message.content, debug)
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
