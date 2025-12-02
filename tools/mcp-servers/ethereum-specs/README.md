# Ethereum Specs MCP Server

An MCP (Model Context Protocol) server that provides access to Ethereum specifications for both consensus layer and execution layer.

## Features

- **Consensus Layer**: Access specifications for all Ethereum consensus forks (phase0, altair, bellatrix, capella, deneb, electra, fulu)
- **Execution Layer**: Access Engine API specs and JSON-RPC method definitions (paris, shanghai, cancun, prague, osaka)
- Search across all specifications
- Compare specifications between different forks
- Retrieve configuration constants
- Get detailed JSON-RPC method information
- Fork/upgrade name mapping between consensus and execution layers
- Automatic repository updates on startup (configurable)

## Available Tools

### `get_spec`
Retrieve the content of a specific specification document.

**Parameters:**
- `fork` (required): Fork name for consensus (phase0-fulu) or upgrade name for engine (paris-osaka)
- `topic` (required): Topic name (beacon-chain, fork-choice, p2p-interface, validator, etc.)
- `layer` (optional): `consensus` (default), `engine`, or `eth`

**Examples:**
```json
{
  "name": "get_spec",
  "arguments": {
    "fork": "fulu",
    "topic": "p2p-interface"
  }
}
```

```json
{
  "name": "get_spec",
  "arguments": {
    "fork": "cancun",
    "topic": "common",
    "layer": "engine"
  }
}
```

### `search_specs`
Search for content across specifications. Searches all layers by default.

**Parameters:**
- `query` (required): Search query string
- `fork` (optional): Limit search to a specific fork/upgrade
- `layer` (optional): `consensus`, `engine`, `eth`, or `all` (default)

**Example:**
```json
{
  "name": "search_specs",
  "arguments": {
    "query": "blob",
    "layer": "all"
  }
}
```

### `list_forks`
List all available forks/upgrades in the specifications.

**Parameters:**
- `layer` (optional): `consensus` (default), `engine`, or `all`

**Example:**
```json
{
  "name": "list_forks",
  "arguments": {
    "layer": "all"
  }
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

### `get_rpc_method`
Get detailed information about a JSON-RPC method including parameters, return type, and examples.

**Parameters:**
- `method` (required): JSON-RPC method name (e.g., `eth_call`, `engine_newPayloadV4`)

**Example:**
```json
{
  "name": "get_rpc_method",
  "arguments": {
    "method": "eth_call"
  }
}
```

### `list_rpc_methods`
List available JSON-RPC methods with optional namespace filter.

**Parameters:**
- `namespace` (optional): Filter by namespace (`eth`, `engine`, `debug`)

**Example:**
```json
{
  "name": "list_rpc_methods",
  "arguments": {
    "namespace": "eth"
  }
}
```

### `get_fork_mapping`
Get the mapping between consensus layer fork names and execution layer upgrade names.

**Example:**
```json
{
  "name": "get_fork_mapping",
  "arguments": {}
}
```

Returns mappings like:
- bellatrix <-> paris (The Merge)
- capella <-> shanghai (Withdrawals)
- deneb <-> cancun (EIP-4844 Blobs)
- electra <-> prague (Pectra upgrade)

## Requirements

- Go 1.23+
- Git (for cloning and updating the specs repositories)

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
- **Specs branch to track**: Branch of ethereum/consensus-specs (default: master)
- **Execution APIs branch to track**: Branch of ethereum/execution-apis (default: main)

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
        "SPECS_BRANCH": "master",
        "EXECUTION_APIS_BRANCH": "main"
      }
    }
  }
}
```

## Configuration

The server accepts the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_UPDATE` | `true` | Update both repos on startup |
| `SPECS_BRANCH` | `master` | Branch for ethereum/consensus-specs |
| `EXECUTION_APIS_BRANCH` | `main` | Branch for ethereum/execution-apis |

## Repository Management

The server clones two repositories locally:
- `.consensus-specs/` - ethereum/consensus-specs
- `.execution-apis/` - ethereum/execution-apis

These are stored in the server's directory to keep everything self-contained.

When auto-update is enabled, the server will:
1. Clone repositories if they don't exist
2. Fetch and pull the latest changes from the configured branches
3. Cache frequently accessed specifications in memory

Updates run in the background to avoid blocking server startup.

## Architecture

- **main.go**: MCP server implementation and tool handlers
- **specs_manager.go**: Consensus specs repository management
- **execution_specs_manager.go**: Execution APIs repository management
- **yaml_parser.go**: OpenRPC YAML parsing utilities
- **fork_mapping.go**: CL/EL fork name mapping

The server uses the official MCP Go SDK and communicates over stdio, making it compatible with Claude Code and other MCP clients.

## Layer Structure

| Layer | Repository | Format | Organization |
|-------|------------|--------|--------------|
| `consensus` | ethereum/consensus-specs | Markdown | `specs/{fork}/{topic}.md` |
| `engine` | ethereum/execution-apis | Markdown | `src/engine/{upgrade}.md` |
| `eth` | ethereum/execution-apis | YAML | `src/eth/{category}.yaml` |

## Development

### Prerequisites

```bash
# Install Go 1.23+
brew install go  # macOS
```

### Adding New Tools

1. Define parameter struct with proper jsonschema tags in main.go
2. Implement the tool handler function in main.go
3. Add the tool logic in the appropriate manager file
4. Register the tool using `mcp.AddTool()` in main.go

## Troubleshooting

### Server not responding in Claude Code
- Ensure the binary is built: `make build`
- Check that the binary path in Claude configuration is correct
- Verify environment variables are set properly

### Repository not updating
- Check internet connectivity
- Verify Git is installed: `which git`
- Check write permissions to the server directory
- Review logs for Git errors

### Tool errors
- Ensure repositories are cloned: `ls .consensus-specs/ .execution-apis/`
- Check that the requested fork/topic exists
- Verify the branch contains the expected specifications
- Run `make clean && make build` to force a fresh clone

## License

Part of the ethpandaops/ai-cookbook project.
