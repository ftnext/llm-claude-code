# llm-claude-code

[![PyPI](https://img.shields.io/pypi/v/llm-claude-code.svg)](https://pypi.org/project/llm-claude-code/)
[![Changelog](https://img.shields.io/github/v/release/ftnext/llm-claude-code?include_prereleases&label=changelog)](https://github.com/ftnext/llm-claude-code/releases)
[![Tests](https://github.com/ftnext/llm-claude-code/actions/workflows/test.yml/badge.svg)](https://github.com/ftnext/llm-claude-code/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/ftnext/llm-claude-code/blob/main/LICENSE)

LLM plugin to use Claude Code

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/).
```bash
llm install llm-claude-code
```
## Usage

Usage instructions go here.

## Development

To set up this plugin locally, first checkout the code:
```bash
cd llm-claude-code
```
Then create a new virtual environment and install the dependencies and test dependencies:
```bash
uv sync --extra test
```
To run the tests:
```bash
uv run pytest
```
