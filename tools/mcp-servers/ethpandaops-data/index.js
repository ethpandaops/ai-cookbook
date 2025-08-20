#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';

const GRAFANA_URL = process.env.GRAFANA_URL || 'https://grafana.primary.production.platform.ethpandaops.io';
// Read the token from the env var specified in GRAFANA_SERVICE_TOKEN_ENV_VAR
const TOKEN_ENV_VAR = process.env.GRAFANA_SERVICE_TOKEN_ENV_VAR || 'GRAFANA_SERVICE_TOKEN';
const GRAFANA_TOKEN = process.env[TOKEN_ENV_VAR];
const DATASOURCE_CONFIG = process.env.DATASOURCE_UIDS ? process.env.DATASOURCE_UIDS.split(',') : [];

// Datasources will be populated from Grafana API
let DATASOURCES = {};

if (!GRAFANA_TOKEN) {
  console.error(`Error: ${TOKEN_ENV_VAR} environment variable is required`);
  process.exit(1);
}

const server = new Server(
  {
    name: 'ethpandaops-data',
    version: '0.1.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Helper to make Grafana API requests
async function grafanaRequest(path, params = {}) {
  const response = await axios({
    method: 'GET',
    url: `${GRAFANA_URL}/api${path}`,
    headers: {
      'Authorization': `Bearer ${GRAFANA_TOKEN}`,
      'Content-Type': 'application/json',
    },
    params,
  });
  return response.data;
}

// Helper to query datasource proxy
async function queryDatasource(datasourceUid, path, params = {}) {
  const response = await axios({
    method: 'GET',
    url: `${GRAFANA_URL}/api/datasources/proxy/uid/${datasourceUid}${path}`,
    headers: {
      'Authorization': `Bearer ${GRAFANA_TOKEN}`,
      'Content-Type': 'application/json',
    },
    params,
  });
  return response.data;
}

// Parse time strings (now, now-1h, RFC3339, etc.)
function parseTime(timeStr) {
  if (!timeStr || timeStr === 'now') {
    return Date.now() * 1000000; // nanoseconds
  }
  
  if (timeStr.startsWith('now-')) {
    const duration = timeStr.substring(4);
    const match = duration.match(/^(\d+)([smhd])$/);
    if (match) {
      const value = parseInt(match[1]);
      const unit = match[2];
      const ms = {
        's': value * 1000,
        'm': value * 60 * 1000,
        'h': value * 60 * 60 * 1000,
        'd': value * 24 * 60 * 60 * 1000,
      }[unit];
      return (Date.now() - ms) * 1000000;
    }
  }
  
  // Try parsing as RFC3339
  const date = new Date(timeStr);
  if (!isNaN(date.getTime())) {
    return date.getTime() * 1000000;
  }
  
  throw new Error(`Invalid time format: ${timeStr}`);
}

// Discover datasources from Grafana
async function discoverDatasources() {
  try {
    console.error('Discovering datasources from Grafana...');
    const datasources = await grafanaRequest('/datasources');
    
    // Build datasource map
    for (const ds of datasources) {
      if (ds.type === 'loki') {
        DATASOURCES[ds.uid] = {
          uid: ds.uid,
          name: ds.name,
          type: 'loki',
          tools: ['loki_query', 'loki_labels', 'loki_label_values']
        };
      }
      // Add more datasource types here as needed
    }
    
    // Filter by config if specified
    if (DATASOURCE_CONFIG.length > 0) {
      const filtered = {};
      for (const uid of DATASOURCE_CONFIG) {
        if (DATASOURCES[uid]) {
          filtered[uid] = DATASOURCES[uid];
        }
      }
      DATASOURCES = filtered;
    }
    
    console.error(`Discovered ${Object.keys(DATASOURCES).length} datasource(s):`);
    for (const [uid, config] of Object.entries(DATASOURCES)) {
      console.error(`  - ${config.name} (${config.type}): ${uid}`);
    }
    
    return DATASOURCES;
  } catch (error) {
    console.error('Failed to discover datasources:', error.message);
    throw error;
  }
}

let enabledDatasources = {};

// Tool implementations
const toolHandlers = {
  async loki_query({ query, start = 'now-1h', end = 'now', limit = 100, datasource_uid }) {
    // Find Loki datasource - use provided UID or first available
    let datasourceUid = datasource_uid;
    if (!datasourceUid) {
      const lokiDs = Object.values(enabledDatasources).find(ds => ds.type === 'loki');
      if (!lokiDs) {
        throw new Error('No Loki datasource available');
      }
      datasourceUid = lokiDs.uid;
    }

    const startNs = parseTime(start);
    const endNs = parseTime(end);
    
    const result = await queryDatasource(datasourceUid, '/loki/api/v1/query_range', {
      query,
      start: startNs,
      end: endNs,
      limit,
    });
    
    return result;
  },

  async loki_labels({ start = 'now-1h', end = 'now', datasource_uid }) {
    // Find Loki datasource - use provided UID or first available
    let datasourceUid = datasource_uid;
    if (!datasourceUid) {
      const lokiDs = Object.values(enabledDatasources).find(ds => ds.type === 'loki');
      if (!lokiDs) {
        throw new Error('No Loki datasource available');
      }
      datasourceUid = lokiDs.uid;
    }

    const startNs = parseTime(start);
    const endNs = parseTime(end);
    
    const result = await queryDatasource(datasourceUid, '/loki/api/v1/labels', {
      start: startNs,
      end: endNs,
    });
    
    return result;
  },

  async loki_label_values({ label, start = 'now-1h', end = 'now', datasource_uid }) {
    // Find Loki datasource - use provided UID or first available
    let datasourceUid = datasource_uid;
    if (!datasourceUid) {
      const lokiDs = Object.values(enabledDatasources).find(ds => ds.type === 'loki');
      if (!lokiDs) {
        throw new Error('No Loki datasource available');
      }
      datasourceUid = lokiDs.uid;
    }

    const startNs = parseTime(start);
    const endNs = parseTime(end);
    
    const result = await queryDatasource(datasourceUid, `/loki/api/v1/label/${label}/values`, {
      start: startNs,
      end: endNs,
    });
    
    return result;
  },
};

// Define available tools based on enabled datasources
server.setRequestHandler(ListToolsRequestSchema, async () => {
  const tools = [];
  
  for (const [uid, config] of Object.entries(enabledDatasources)) {
    for (const toolName of config.tools) {
      if (toolName === 'loki_query') {
        tools.push({
          name: 'loki_query',
          description: 'Query logs from Loki datasource',
          inputSchema: {
            type: 'object',
            properties: {
              query: { type: 'string', description: 'LogQL query string' },
              start: { type: 'string', description: 'Start time (e.g., "now-1h", RFC3339)' },
              end: { type: 'string', description: 'End time (e.g., "now", RFC3339)' },
              limit: { type: 'integer', description: 'Max log lines to return (default: 100)' },
              datasource_uid: { type: 'string', description: 'Specific datasource UID to use (optional)' },
            },
            required: ['query'],
          },
        });
      } else if (toolName === 'loki_labels') {
        tools.push({
          name: 'loki_labels',
          description: 'Get available labels from Loki',
          inputSchema: {
            type: 'object',
            properties: {
              start: { type: 'string', description: 'Start time (e.g., "now-1h")' },
              end: { type: 'string', description: 'End time (e.g., "now")' },
              datasource_uid: { type: 'string', description: 'Specific datasource UID to use (optional)' },
            },
          },
        });
      } else if (toolName === 'loki_label_values') {
        tools.push({
          name: 'loki_label_values',
          description: 'Get values for a specific Loki label',
          inputSchema: {
            type: 'object',
            properties: {
              label: { type: 'string', description: 'Label name' },
              start: { type: 'string', description: 'Start time (e.g., "now-1h")' },
              end: { type: 'string', description: 'End time (e.g., "now")' },
              datasource_uid: { type: 'string', description: 'Specific datasource UID to use (optional)' },
            },
            required: ['label'],
          },
        });
      }
    }
  }
  
  return { tools };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  
  if (!(name in toolHandlers)) {
    throw new Error(`Unknown tool: ${name}`);
  }
  
  try {
    const result = await toolHandlers[name](args);
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error.message}`,
        },
      ],
    };
  }
});

async function main() {
  // Discover datasources on startup
  enabledDatasources = await discoverDatasources();
  
  const transport = new StdioServerTransport();
  await server.connect(transport);
  
  console.error(`MCP Server 'ethpandaops-data' is running`);
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});