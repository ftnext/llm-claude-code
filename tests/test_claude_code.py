from unittest.mock import MagicMock, patch

import pytest
from llm.plugins import load_plugins, pm

from llm_claude_code import ClaudeCode, ProcessError


def test_plugin_is_installed():
    """Test that the plugin is properly installed"""
    load_plugins()
    names = [mod.__name__ for mod in pm.get_plugins()]
    assert "llm_claude_code" in names


def test_model_registration():
    """Test that the Claude Code model is registered"""
    model = ClaudeCode()
    assert model.model_id == "claude-code"
    assert model.can_stream is True


@pytest.mark.asyncio
@patch("llm_claude_code.query")
async def test_execute_single_success(mock_query):
    """Test successful single execution"""
    # Mock message with content
    mock_message = MagicMock()
    mock_message.content = "Test response from Claude Code"

    # Mock the async generator
    async def mock_async_gen():
        yield mock_message

    mock_query.return_value = mock_async_gen()

    # Mock prompt object
    mock_prompt = MagicMock()
    mock_prompt.prompt = "test prompt"

    model = ClaudeCode()
    result = await model._execute_single(mock_prompt)
    assert "Test response from Claude Code" in result


@pytest.mark.asyncio
@patch("llm_claude_code.query")
async def test_execute_single_error(mock_query):
    """Test single execution with error"""
    mock_query.side_effect = Exception("SDK error")

    # Mock prompt object
    mock_prompt = MagicMock()
    mock_prompt.prompt = "test prompt"

    model = ClaudeCode()

    with pytest.raises(ProcessError, match="Failed to execute Claude Code SDK"):
        await model._execute_single(mock_prompt)


@pytest.mark.asyncio
@patch("llm_claude_code.query")
async def test_stream_execute_success(mock_query):
    """Test successful streaming execution"""
    # Mock messages
    mock_message1 = MagicMock()
    mock_message1.content = "First chunk"
    mock_message2 = MagicMock()
    mock_message2.content = "Second chunk"

    # Mock the async generator
    async def mock_async_gen():
        yield mock_message1
        yield mock_message2

    mock_query.return_value = mock_async_gen()

    # Mock prompt object
    mock_prompt = MagicMock()
    mock_prompt.prompt = "test prompt"

    model = ClaudeCode()
    results = []
    async for chunk in model._stream_execute(mock_prompt):
        results.append(chunk)

    assert len(results) == 2
    assert "First chunk" in results[0]
    assert "Second chunk" in results[1]


def test_format_output_tool_message():
    """Test output formatting for tool messages"""
    model = ClaudeCode()

    output = "[Tool: Read] Reading file"
    result = model._format_output(output)
    assert "\033[34m" in result  # Blue color
    assert "\033[0m" in result  # Reset color


def test_format_output_error_message():
    """Test output formatting for error messages"""
    model = ClaudeCode()

    output = "Error: something failed"
    result = model._format_output(output)
    assert "\033[31m" in result  # Red color


def test_format_output_success_message():
    """Test output formatting for success messages"""
    model = ClaudeCode()

    output = "✓ Task completed successfully"
    result = model._format_output(output)
    assert "\033[32m" in result  # Green color


def test_format_output_regular_message():
    """Test output formatting for regular messages"""
    model = ClaudeCode()

    output = "Regular assistant message"
    result = model._format_output(output)
    assert result == "Regular assistant message"
