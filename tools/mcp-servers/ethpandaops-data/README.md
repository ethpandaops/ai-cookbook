# ethPandaOps Data MCP Server

A minimal MCP (Model Context Protocol) server that provides access to ethPandaOps datasources through Grafana. The server automatically discovers available datasources on startup and supports Loki, Prometheus, and ClickHouse. Datasources are cached in memory and exposed via a single tool per type, plus a datasource listing tool.

## Features

- **Automatic datasource discovery** - Connects to Grafana and discovers Loki, Prometheus, and ClickHouse datasources
- **Single tool per type** - Minimal, consistent tool surface for each datasource type
- **Datasource listing** - `list_datasources` to enumerate UIDs, names, and descriptions
- **Flexible configuration** - Use env vars to filter UIDs and provide descriptions
- **Token management** - Configure which environment variable contains your Grafana token
- **Multi-datasource support** - Pass `datasource_uid` when there are multiple of a type

## Installation

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
        "HTTP_TIMEOUT_MS": "15000"
      }
    }
  }
}
```

## Configuration

### Environment Variables

- `GRAFANA_SERVICE_TOKEN_ENV_VAR` (optional): The name of the env var containing your Grafana token (default: `GRAFANA_SERVICE_TOKEN`).
- `GRAFANA_URL` (optional): Grafana API URL (default: `https://grafana.primary.production.platform.ethpandaops.io`).
- `DATASOURCE_UIDS` (optional): Comma-separated datasource UIDs to enable. If absent, all discovered Loki/Prometheus/ClickHouse datasources are enabled.
- `DATASOURCE_DESCRIPTIONS` (optional): JSON map `{ "uid": "description" }` to help LLMs choose datasources.
- `HTTP_TIMEOUT_MS` (optional): Timeout for Grafana HTTP calls (default: 15000).

The server reads the token from the environment variable specified in `GRAFANA_SERVICE_TOKEN_ENV_VAR`. This allows you to use different token environment variables for different environments.

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

## Available Tools

### Tools

- `list_datasources`
  - List all discovered datasources (UID, name, type, description).
  - Params: `type` (optional: `loki` | `prometheus` | `clickhouse`).

- `loki_tool`
  - Actions: `query`, `labels`, `label_values`.
  - Common params: `start` (default: `now-1h`), `end` (default: `now`), `datasource_uid` (required if multiple Loki datasources).
  - For `query`: `query` (LogQL), `limit` (default: 100).
  - For `label_values`: `label`.

- `prometheus_tool`
  - Modes: `instant` or `range`.
  - Params: `query` (PromQL), `mode`, `time` (instant), `start`, `end`, `step` (range), `datasource_uid`.

- `clickhouse_tool`
  - Params: `sql` (required), `from` (default: `now-1h`), `to` (default: `now`), `datasource_uid`.
  - Uses Grafana’s unified data query API; requires a ClickHouse datasource that supports raw SQL in Grafana.

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
export ETHPANDAOPS_PLATFORM_PRODUCTION_GRAFANA_SERVICE_TOKEN=your-token
GRAFANA_SERVICE_TOKEN_ENV_VAR=ETHPANDAOPS_PLATFORM_PRODUCTION_GRAFANA_SERVICE_TOKEN node index.js
```

### Testing

Slim unit tests use Node’s built-in test runner (no extra deps):

```bash
cd tools/mcp-servers/ethpandaops-data
npm test
```

Tests cover pure helpers (time parsing, duration parsing, type normalization) and UID selection logic; they do not make network calls.

## Troubleshooting

1. **Authentication errors**: Ensure your token environment variable is set and the token has the necessary permissions.

2. **No datasources discovered**: Check that your token has access to list datasources in Grafana.
   - Verify types are among `loki`, `prometheus`, or `clickhouse` (normalized).

3. **Datasource not found**: The server will log all discovered datasources on startup. Check that your desired datasource appears in the list.

4. **Connection issues**: Verify you can reach the Grafana instance and that your network allows the connection.
5. **ClickHouse errors**: The query model may differ by plugin; errors from Grafana will be surfaced. You may need to adjust the SQL or plugin-specific model in the server if your ClickHouse plugin doesn’t support raw SQL via the unified API.

## License

MIT
