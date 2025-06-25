# llm-claude-code

[![PyPI](https://img.shields.io/pypi/v/llm-claude-code.svg)](https://pypi.org/project/llm-claude-code/)
[![Changelog](https://img.shields.io/github/v/release/ftnext/llm-claude-code?include_prereleases&label=changelog)](https://github.com/ftnext/llm-claude-code/releases)
[![Tests](https://github.com/ftnext/llm-claude-code/actions/workflows/test.yml/badge.svg)](https://github.com/ftnext/llm-claude-code/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/ftnext/llm-claude-code/blob/main/LICENSE)

LLM plugin for Claude Code SDK integration

## Overview

`llm-claude-code` is a plugin for [Simon Willison's LLM tool](https://llm.datasette.io/) that enables you to use Claude Code through the LLM command-line interface. This plugin leverages the Claude Code CLI to provide AI assistance with coding tasks.

## Prerequisites

Before using this plugin, ensure you have:

- **Claude Code CLI installed**: Install with `npm install -g @anthropic-ai/claude-code`
- **Node.js**: Required for Claude Code CLI
- **Anthropic API Key configured**: Set up through environment variables or Claude Code settings
- **Python 3.10 or higher**

To install Claude Code, visit the [official documentation](https://docs.anthropic.com/en/docs/claude-code).

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/):

```bash
llm install llm-claude-code
```

## Usage

### Basic Usage

Use the `claude-code` model with the LLM command:

```bash
# Basic usage
llm -m claude-code "Write a Python function to calculate fibonacci numbers"

# Using the alias 'cc'
llm -m cc "Create a hello world script"
```

### Features

- **Streaming Support**: Real-time output display during generation
- **Color-coded Output**: Different message types are displayed with distinct colors:
  - Tool messages: Blue
  - Error messages: Red  
  - Success messages: Green
  - Regular messages: Default color
- **Error Handling**: Comprehensive error reporting for CLI issues

### Model Aliases

The plugin provides the following model identifiers:

- Primary: `claude-code`
- Alias: `cc`

### Tool Usage

The initial implementation disables tool usage (`--no-tools` flag) to focus on text generation. Future versions may include configurable tool support.

## Error Handling

The plugin includes comprehensive error handling for common issues:

- **`CLINotFoundError`**: Raised when Claude Code CLI is not installed or not found in PATH
- **`CLIConnectionError`**: Raised when there are connection issues with the Claude Code service
- **`ProcessError`**: Raised when there are errors during command execution

## Troubleshooting

### SDK Import Errors

If you encounter import errors with the Claude Code SDK:

1. Ensure you have Python 3.10 or higher
2. Install the plugin with `llm install llm-claude-code`
3. Verify that `claude-code-sdk` is properly installed

### Connection Issues

If you experience connection timeouts:

1. Check your internet connection
2. Verify your Anthropic API key is valid
3. Ensure you're not hitting rate limits

## Development

To set up this plugin locally, first checkout the code:
```bash
cd llm-claude-code
```
Then create a new virtual environment and install the dependencies and test dependencies:
```bash
uv sync --extra test --extra dev
```
To run the tests:
```bash
uv run pytest
```

## Future Enhancements

The plugin is designed with extensibility in mind. Planned future features include:

- **Tool Usage Configuration**: Enable specific tools via command-line options
- **Advanced Options**: Custom system prompts, max turns, working directory settings
- **Session Management**: Conversation continuity and state preservation

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
