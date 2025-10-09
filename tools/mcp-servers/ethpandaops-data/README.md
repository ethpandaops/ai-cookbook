# ethPandaOps Data MCP Server

A minimal MCP (Model Context Protocol) server that provides access to ethPandaOps datasources through Grafana. The server automatically discovers available datasources on startup and supports Loki, Prometheus, and ClickHouse. Datasources are cached in memory and exposed via a single tool per type, plus a datasource listing tool.

## Features

- **Automatic datasource discovery** - Connects to Grafana and discovers Loki, Prometheus, and ClickHouse datasources
- **Single tool per type** - Minimal, consistent tool surface for each datasource type
- **Datasource listing** - `list_datasources` to enumerate UIDs, names, and descriptions
- **Health check** - `health_check` to verify connection and authentication
- **Flexible configuration** - Use env vars to filter UIDs and provide descriptions
- **Token management** - Configure which environment variable contains your Grafana token
- **Multi-datasource support** - Pass `datasource_uid` when there are multiple of a type
- **ai-cookbook integration** - Automated installation and configuration via ai-cookbook
- **Result persistence** - Default to saving large query outputs under `/tmp/ai-cookbook-grafana` with catalog metadata and resource URIs
- **Visualization-ready workflow** - Built-in helper tools explain how to feed saved datasets into Vega-Lite or VChart MCP servers

## Installation

### Option 1: Using ai-cookbook installer (Recommended)

```bash
# Install ai-cookbook if not already installed
cd /path/to/ai-cookbook
python setup.py install

# Run the interactive installer
ai-cookbook

# Select "MCP Servers" -> "Install ethpandaops-data"
# Follow the prompts to configure Grafana URL and service token
```

The installer will:
- Install npm dependencies automatically
- Prompt for Grafana URL (with sensible defaults)
- Prompt for service token
- Test the connection
- Configure Claude Desktop automatically
- Load datasource descriptions from ai-cookbook/data/ethpandaops/

### Option 2: Manual Installation

1. Install dependencies:
```bash
cd tools/mcp-servers/ethpandaops-data
npm install
```

2. Set up your Grafana service token in your environment:
```bash
export ETHPANDAOPS_PLATFORM_PRODUCTION_GRAFANA_SERVICE_TOKEN="your-service-token-here"
```

3. Configure Claude Desktop to use this MCP server by adding to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ethpandaops-data": {
      "command": "node",
      "args": [
        "/path/to/ai-cookbook/tools/mcp-servers/ethpandaops-data/index.js"
      ],
      "env": {
        "GRAFANA_SERVICE_TOKEN_ENV_VAR": "ETHPANDAOPS_PLATFORM_PRODUCTION_GRAFANA_SERVICE_TOKEN",
        "GRAFANA_URL": "https://grafana.primary.production.platform.ethpandaops.io",
        "DATASOURCE_UIDS": "", // optional: comma-separated UIDs to include
        "DATASOURCE_DESCRIPTIONS": "{\"P8E80F9AEF21F6940\":\"Loki logs for Ethereum services\"}",
        "HTTP_TIMEOUT_MS": "30000"
      }
    }
  }
}
```

## Configuration

### Environment Variables

- `GRAFANA_SERVICE_TOKEN`: Your Grafana service token (required).
- `GRAFANA_SERVICE_TOKEN_ENV_VAR` (optional): Name of an environment variable that contains your token. Use this for indirect token configuration.
- `GRAFANA_URL` (optional): Grafana API URL (default: `https://grafana.primary.production.platform.ethpandaops.io`).
- `DATASOURCE_UIDS` (optional): Comma-separated datasource UIDs to enable. If absent, all discovered Loki/Prometheus/ClickHouse datasources are enabled.
- `DATASOURCE_DESCRIPTIONS` (optional): JSON map `{ "uid": "description" }` to help LLMs choose datasources.
- `DATASOURCE_REQUIRED_READING` (optional): JSON map `{ "uid": "url_or_path" }` to enforce knowledge loading before querying specific datasources. When configured, the LLM must call `load_knowledge` with the datasource UID before it can query that datasource.
- `HTTP_TIMEOUT_MS` (optional): Timeout for Grafana HTTP calls (default: 30000).
- `GRAFANA_RESULT_DIR` (optional): Directory for persisted query results (default: `/tmp/ai-cookbook-grafana`).
- `GRAFANA_MAX_RESOURCE_BYTES` (optional): Maximum bytes readable via `resources/read` (default: `5242880`).
- `GRAFANA_RESULT_TTL_HOURS` (optional): Automatically delete stored results older than this many hours (default: disabled).
- `GRAFANA_CATALOG_LOCK_TIMEOUT_MS` (optional): Milliseconds to wait when acquiring the catalog lock (default: `5000`).
- `GRAFANA_CATALOG_LOCK_POLL_MS` (optional): Backoff duration between lock attempts (default: `50`).
- `GRAFANA_CATALOG_LOCK_STALE_MS` (optional): Consider the lock stale and reclaim it after this many milliseconds (default: `60000`).

Token configuration: Either set `GRAFANA_SERVICE_TOKEN` directly, or use `GRAFANA_SERVICE_TOKEN_ENV_VAR` to specify which environment variable contains your token.

### Automatic Datasource Discovery

On startup, the server:
1. Connects to Grafana using your service token
2. Discovers all available datasources
3. Normalizes types to `loki`, `prometheus`, or `clickhouse`
4. Applies descriptions from env/file
5. Filters by `DATASOURCE_UIDS` if specified
6. Logs which datasources are available

### Enabling Specific Datasources

To enable only specific datasources by their UID:

```json
{
  "mcpServers": {
    "ethpandaops-data": {
      "command": "node",
      "args": [
        "/path/to/ai-cookbook/tools/mcp-servers/ethpandaops-data/index.js"
      ],
      "env": {
        "GRAFANA_SERVICE_TOKEN_ENV_VAR": "ETHPANDAOPS_PLATFORM_PRODUCTION_GRAFANA_SERVICE_TOKEN",
        "DATASOURCE_UIDS": "P8E80F9AEF21F6940, another-uid-here"
      }
    }
  }
}
```

## Knowledge Loading

For datasources that require specific schema or documentation knowledge, you can configure required reading via the `DATASOURCE_REQUIRED_READING` environment variable. When configured, the LLM **must** call the `load_knowledge` tool before it can query that datasource.

### Configuration

Add required reading URLs or file paths to your MCP server configuration:

```json
{
  "mcpServers": {
    "ethpandaops-production-data": {
      "env": {
        "DATASOURCE_REQUIRED_READING": "{\"PDE22E36FB877C574\": \"https://raw.githubusercontent.com/ethpandaops/xatu-data/refs/heads/master/llms/clickhouse/llms.txt\"}"
      }
    }
  }
}
```

Or use a local file in `claude-code/mcp-servers/<server-name>/datasource-required-reading.json`:

```json
{
  "PDE22E36FB877C574": "https://raw.githubusercontent.com/ethpandaops/xatu-data/refs/heads/master/llms/clickhouse/llms.txt"
}
```

The installer will automatically load this file if present.

### Workflow

1. Call `health_check` to see which datasources require knowledge loading
2. For datasources with `requires_knowledge: true`, call `load_knowledge({ datasource_uid: "..." })`
3. The tool fetches the documentation and returns it to the LLM
4. Now you can query that datasource using the normal query tools

### Error Handling

If you try to query a datasource that requires knowledge loading without calling `load_knowledge` first, you'll get an error like:

```
Knowledge loading required for datasource PDE22E36FB877C574.

You must call the load_knowledge tool with datasource_uid="PDE22E36FB877C574" before querying this datasource.
This datasource requires you to read: https://raw.githubusercontent.com/ethpandaops/xatu-data/refs/heads/master/llms/clickhouse/llms.txt

Example: load_knowledge({ datasource_uid: "PDE22E36FB877C574" })
```

## Result Storage & Visualization Workflow

All data tools persist their output under `/tmp/ai-cookbook-grafana/results` and return schema + metadata (never inline data):

1. Run `clickhouse_tool`, `prometheus_tool`, or `loki_tool` to get `result_id`, `resource_uri`, and JSON schema.
2. Access data via `resources/read` with the `resource_uri`:
   - Add `?limit=N&offset=M` for pagination
   - Add `?jq=EXPRESSION` for filtering (e.g., `?jq=.data.result[]|select(.metric.job=="prometheus")`)
3. Optional: Call `describe_result` with `result_id` to get detailed schema and usage examples.
4. For visualization tools, use `file_path` from `describe_result` to load data directly.
5. Clean up with `delete_result` or `trim_results`, or enable `GRAFANA_RESULT_TTL_HOURS` for automatic pruning.

> Note: catalog mutations are guarded by a simple filesystem lock (`catalog.lock`) so multiple Grafana MCP instances can share the same result directory safely.

## Available Tools

### Tools

- `health_check`
  - Verify connectivity, authentication, storage configuration, and catalog size.
  - Returns Grafana user info, discovered datasources, result storage defaults, required reading status, and preview limits.

- `list_datasources`
  - List discovered datasources (UID, name, type, description) with optional type filter.
  - Params: `type` (`loki` | `prometheus` | `clickhouse`).

- `load_knowledge`
  - Load required documentation/schema information for a datasource before querying.
  - Some datasources (configured via `DATASOURCE_REQUIRED_READING`) require knowledge to be loaded before they can be queried.
  - This tool fetches the documentation from a URL or file path and marks the datasource as ready for querying.
  - Params: `datasource_uid` (required)
  - Returns: The knowledge content and confirmation that the datasource can now be queried.

- `loki_tool`
  - Interact with Loki (`query`, `labels`, `label_values`).
  - Stores results to disk and returns metadata (`result_id`, `file_path`, `resource_uri`).

- `prometheus_tool`
  - Run instant or range PromQL queries.
  - Stores results to disk and returns metadata (`result_id`, `file_path`, `resource_uri`).

- `clickhouse_tool`
  - Execute raw SQL through Grafana’s unified data query API.
  - Stores results to disk and returns metadata (`result_id`, `file_path`, `resource_uri`).

- `describe_result`
  - Return metadata for a specific `result_id` (resource URI, summary, sizes).

- `delete_result`
  - Remove a stored result and optionally delete its cached artifact.

- `trim_results`
  - Bulk-prune saved results by age (`max_age_hours`) or by keeping only the most recent (`max_results`).

## Adding New Datasource Types

The server automatically discovers datasources from Grafana. To add support for new datasource types:

1. Update the discovery logic in `discoverDatasources()`:
```javascript
if (ds.type === 'prometheus') {
  DATASOURCES[ds.uid] = {
    uid: ds.uid,
    name: ds.name,
    type: 'prometheus',
    tools: ['prometheus_query', 'prometheus_series']
  };
}
```

2. Implement the tool handlers in `toolHandlers`:
```javascript
const toolHandlers = {
  // existing handlers...
  async prometheus_query({ query, time, datasource_uid }) {
    // Implementation
  }
};
```

3. Add tool definitions in the `ListToolsRequestSchema` handler.

## Development

Run the server locally for testing:
```bash
# Option A: Direct token
GRAFANA_SERVICE_TOKEN=your-token node index.js

# Option B: Indirect via environment variable
export MY_GRAFANA_TOKEN=your-token
GRAFANA_SERVICE_TOKEN_ENV_VAR=MY_GRAFANA_TOKEN node index.js
```

### Testing

Slim unit tests use Node’s built-in test runner (no extra deps):

```bash
cd tools/mcp-servers/ethpandaops-data
npm test
```

Tests cover pure helpers (time parsing, duration parsing, type normalization) and UID selection logic; they do not make network calls.

## Troubleshooting

### Using the health check

The `health_check` tool can help diagnose connection issues:

```javascript
// In Claude Desktop, after installing the MCP server
await health_check()
```

This will return:
- Connection status to Grafana
- Authentication status
- Number of discovered datasources
- Helpful error messages if something is wrong

### Common Issues

1. **Authentication errors**: Ensure your token environment variable is set and the token has the necessary permissions.
   - Create a service token at: `<GRAFANA_URL>/org/serviceaccounts`
   - Ensure the token has at least 'Viewer' role

2. **No datasources discovered**: Check that your token has access to list datasources in Grafana.
   - Verify types are among `loki`, `prometheus`, or `clickhouse` (normalized).

3. **Datasource not found**: The server will log all discovered datasources on startup. Check that your desired datasource appears in the list.

4. **Connection issues**: Verify you can reach the Grafana instance and that your network allows the connection.
5. **ClickHouse errors**: The query model may differ by plugin; errors from Grafana will be surfaced. You may need to adjust the SQL or plugin-specific model in the server if your ClickHouse plugin doesn’t support raw SQL via the unified API.

## License

MIT
