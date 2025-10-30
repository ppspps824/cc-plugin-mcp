# cc-plugin-mcp

MCP (Model Context Protocol) server for accessing Claude Code plugins.

## Overview

This MCP server provides an interface to Claude Code's plugin system via the Model Context Protocol, enabling you to retrieve plugin lists and detailed information. It can be used from MCP clients such as Claude Desktop, Cursor, etc.

## Key Features

- **MCP Protocol Support**: Compliant with Model Context Protocol
- **Plugin Management**: Retrieve plugin lists and load elements from Claude Code plugins
- **Security**: Path traversal protection, input validation, error handling
- **Performance**: LRU cache for fast access
- **Operability**: Comprehensive logging, 29 test cases

## MCP Tools

- `list_plugins` - Get a list of available plugins
- `load_elements` - Load elements (skills, agents, commands) from specified plugins

## Configuration

Add the following to your MCP client configuration file (e.g., `claude_desktop_config.json` for Claude Desktop):

```json
{
  "mcpServers": {
    "cc-plugin-mcp": {
      "command": "uvx",
      "args": ["cc-plugin-mcp"]
    }
  }
}
```

## Installation

```bash
# Run directly with uvx (recommended)
uvx cc-plugin-mcp

# Or install from PyPI
pip install cc-plugin-mcp

# For development
git clone https://github.com/ppspps824/cc-plugin-mcp.git
cd cc-plugin-mcp
uv sync --all-extras
```

## Usage

This runs as an MCP server and is called directly by MCP clients. For manual testing:

```bash
# Start MCP server with uvx (recommended)
uvx cc-plugin-mcp

# Or for development
uv run python -m cc_plugin_mcp.main
```

## MCP Integration with AI Tools

For optimal use of this MCP server with AI tools like Cursor, Claude Desktop, or other MCP-compatible clients:

### With Cursor
1. Add the MCP server to your Cursor settings (`.cursor/settings.json` or similar)
2. Include the configuration shown in the Configuration section above
3. **Important**: Make sure to load the MCP server tools in your system prompt or initial message. Tell the AI to use the available MCP tools by instructing it to first call the MCP tools list to discover what's available.

### With Claude Desktop
1. Add the configuration to `claude_desktop_config.json` as shown in the Configuration section
2. Restart Claude Desktop to enable the MCP server
3. The MCP tools will be automatically available for Claude to use

### Best Practices for Using MCP Tools
- **Load the tools first**: Always instruct the AI to first call the available MCP tools to discover what's available
- **Check the system prompt**: Ensure your system prompt or initial instructions include guidance to use MCP tools
- **Discover capabilities**: Use the tools to explore available plugins and their elements before requesting specific functionality

## Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=cc_plugin_mcp
```

## Troubleshooting

### Plugins not found
1. Check if `~/.claude/plugins/` directory exists
2. Verify `marketplace.json` exists in `~/.claude/plugins/marketplaces/`

### MCP client doesn't recognize the server
1. Verify MCP client configuration file is set up correctly
2. Check if `uvx` command is available (`uvx --version`)
3. Check MCP client logs for error messages

### Tests failing
```bash
uv sync --all-extras --refresh
uv run pytest -v
```

## License

MIT

## Repository

https://github.com/ppspps824/cc-plugin-mcp
