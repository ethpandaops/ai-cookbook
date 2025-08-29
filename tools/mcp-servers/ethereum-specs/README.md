# Ethereum Consensus Specs MCP Server

An MCP (Model Context Protocol) server that provides access to Ethereum consensus specifications for all forks.

## Features

- Access specifications for all Ethereum consensus forks: phase0, altair, bellatrix, capella, deneb, electra, fulu
- Search across all specifications
- Compare specifications between different forks
- Retrieve configuration constants
- Automatic repository updates on startup (configurable)

## Available Tools

### `get_spec`
Retrieve the content of a specific specification document.

**Parameters:**
- `fork` (required): Fork name (phase0, altair, bellatrix, capella, deneb, electra, fulu)
- `topic` (required): Topic name (beacon-chain, fork-choice, p2p-interface, validator, etc.)

**Example:**
```json
{
  "name": "get_spec",
  "arguments": {
    "fork": "fulu",
    "topic": "p2p-interface"
  }
}
```

### `search_specs`
Search for content across specifications.

**Parameters:**
- `query` (required): Search query string
- `fork` (optional): Limit search to a specific fork

**Example:**
```json
{
  "name": "search_specs",
  "arguments": {
    "query": "GetMetadata",
    "fork": "fulu"
  }
}
```

### `list_forks`
List all available forks in the specifications.

**Example:**
```json
{
  "name": "list_forks",
  "arguments": {}
}
```

### `compare_forks`
Compare a specific topic between two different forks.

**Parameters:**
- `fork1` (required): First fork to compare
- `fork2` (required): Second fork to compare
- `topic` (required): Topic to compare

**Example:**
```json
{
  "name": "compare_forks",
  "arguments": {
    "fork1": "deneb",
    "fork2": "fulu",
    "topic": "p2p-interface"
  }
}
```

### `get_constant`
Retrieve configuration constants from the specifications.

**Parameters:**
- `name` (required): Constant name (e.g., MAX_EFFECTIVE_BALANCE)
- `fork` (optional): Specific fork (defaults to searching all forks)

**Example:**
```json
{
  "name": "get_constant",
  "arguments": {
    "name": "MAX_EFFECTIVE_BALANCE",
    "fork": "deneb"
  }
}
```

## Requirements

- Go 1.23+ 
- Git (for cloning and updating the specs repository)

## Building

```bash
make build
```

This will:
1. Download Go dependencies
2. Build the binary to `bin/ethereum-specs-mcp`
3. Make the binary executable

## Installation via AI Cookbook

The ethereum-specs MCP server is automatically configured when installed via the AI Cookbook:

```bash
cd /path/to/ai-cookbook
python3 -m src.ai_cookbook.main
# Select: MCP Servers > Install > ethereum-specs
```

During installation, you'll be prompted for:
- **Auto-update specs on startup**: Enable to pull latest specs (default: true)
- **Specs branch to track**: Branch of ethereum/consensus-specs (default: dev)

## Manual Installation

1. Build the server:
```bash
cd tools/mcp-servers/ethereum-specs
make build
```

2. Add to your Claude configuration (`~/.claude.json`):
```json
{
  "mcpServers": {
    "ethereum-specs": {
      "command": "/path/to/ethereum-specs-mcp",
      "args": [],
      "env": {
        "AUTO_UPDATE": "true",
        "SPECS_BRANCH": "dev"
      }
    }
  }
}
```

## Configuration

The server accepts the following environment variables:

- `AUTO_UPDATE`: Set to "false" to disable automatic repository updates on startup (default: "true")
- `SPECS_BRANCH`: Branch of ethereum/consensus-specs to use (default: "dev")

## Repository Management

The server clones the ethereum/consensus-specs repository to `~/.ethereum-specs` on first run. 

When auto-update is enabled, the server will:
1. Clone the repository if it doesn't exist
2. Fetch and pull the latest changes from the configured branch
3. Cache frequently accessed specifications in memory

Updates run in the background to avoid blocking server startup.

## Architecture

- **main.go**: MCP server implementation using the official Go SDK
- **specs_manager.go**: Repository management and tool implementations
- **go.mod**: Go module dependencies
- **Makefile**: Build automation

The server uses the official MCP Go SDK and communicates over stdio, making it compatible with Claude Code and other MCP clients.

## Development

### Prerequisites

```bash
# Install Go 1.23+
brew install go  # macOS
```

### Adding New Tools

1. Define parameter struct with proper jsonschema tags in main.go
2. Implement the tool handler function in main.go
3. Add the tool logic in specs_manager.go
4. Register the tool using `mcp.AddTool()` in main.go

### Performance Considerations

- Specifications are cached in memory after first access
- Git operations run in background on startup (when auto-update is enabled)
- Search results are limited to prevent excessive memory usage
- Diff comparisons are truncated after 100 changes for readability

## Logging

The server logs to stderr to avoid interfering with the MCP protocol on stdout. Logs include:
- Server initialization status
- Repository update progress
- Tool execution errors

## Troubleshooting

### Server not responding in Claude Code
- Ensure the binary is built: `make build`
- Check that the binary path in Claude configuration is correct
- Verify environment variables are set properly

### Repository not updating
- Check internet connectivity
- Verify Git is installed: `which git`
- Check write permissions to `~/.ethereum-specs`
- Review logs for Git errors

### Tool errors
- Ensure the repository is cloned: `ls ~/.ethereum-specs`
- Check that the requested fork/topic exists
- Verify the branch contains the expected specifications

## License

Part of the ethpandaops/ai-cookbook project.