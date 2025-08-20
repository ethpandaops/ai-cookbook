# ethPandaOps Data MCP Server

A minimal MCP (Model Context Protocol) server that provides access to ethPandaOps datasources through Grafana. The server automatically discovers available datasources on startup and currently supports Loki with plans to add more datasource types.

## Features

- **Automatic datasource discovery** - Connects to Grafana and discovers all available datasources
- **Flexible configuration** - Use environment variables to specify which datasources to enable
- **Token management** - Configure which environment variable contains your Grafana token
- **Multi-datasource support** - Query specific datasources by UID when multiple are available

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
        "DATASOURCE_UIDS": ""
      }
    }
  }
}
```

## Configuration

### Environment Variables

- `GRAFANA_SERVICE_TOKEN_ENV_VAR` (optional): The name of the environment variable containing your Grafana token (defaults to `GRAFANA_SERVICE_TOKEN`)
- `GRAFANA_URL` (optional): Grafana API URL (defaults to `https://grafana.primary.production.platform.ethpandaops.io`)
- `DATASOURCE_UIDS` (optional): Comma-separated list of datasource UIDs to enable. If not set, all discovered datasources are enabled.

The server reads the token from the environment variable specified in `GRAFANA_SERVICE_TOKEN_ENV_VAR`. This allows you to use different token environment variables for different environments.

### Automatic Datasource Discovery

On startup, the server:
1. Connects to Grafana using your service token
2. Discovers all available datasources
3. Filters by `DATASOURCE_UIDS` if specified
4. Logs which datasources are available

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
        "DATASOURCE_UIDS": "P8E80F9AEF21F6940,another-uid-here"
      }
    }
  }
}
```

## Available Tools

### Loki Tools

All Loki tools support an optional `datasource_uid` parameter to specify which datasource to query when multiple are available.

#### `loki_query`
Query logs from Loki datasource.

Parameters:
- `query` (required): LogQL query string
- `start`: Start time (default: "now-1h"). Accepts:
  - Relative time: "now-1h", "now-30m", "now-7d"
  - RFC3339 format: "2024-01-01T00:00:00Z"
- `end`: End time (default: "now")
- `limit`: Maximum number of log lines to return (default: 100)
- `datasource_uid` (optional): Specific datasource UID to use

Example:
```
Query: {job="ethereum"} |= "error"
Start: now-6h
End: now
```

#### `loki_labels`
Get available labels from Loki.

Parameters:
- `start`: Start time (default: "now-1h")
- `end`: End time (default: "now")
- `datasource_uid` (optional): Specific datasource UID to use

#### `loki_label_values`
Get values for a specific label.

Parameters:
- `label` (required): Label name to get values for
- `start`: Start time (default: "now-1h")
- `end`: End time (default: "now")
- `datasource_uid` (optional): Specific datasource UID to use

Example:
```
Label: job
```

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

## Troubleshooting

1. **Authentication errors**: Ensure your token environment variable is set and the token has the necessary permissions.

2. **No datasources discovered**: Check that your token has access to list datasources in Grafana.

3. **Datasource not found**: The server will log all discovered datasources on startup. Check that your desired datasource appears in the list.

4. **Connection issues**: Verify you can reach the Grafana instance and that your network allows the connection.

## License

MIT