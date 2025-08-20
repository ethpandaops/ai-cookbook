#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';
import { parseTime, parseDurationToSeconds, normalizeType, requireUidForType as baseRequireUidForType } from './utils.js';

const GRAFANA_URL = process.env.GRAFANA_URL || 'https://grafana.primary.production.platform.ethpandaops.io';
// Read the token from the env var specified in GRAFANA_SERVICE_TOKEN_ENV_VAR
const TOKEN_ENV_VAR = process.env.GRAFANA_SERVICE_TOKEN_ENV_VAR || 'GRAFANA_SERVICE_TOKEN';
const GRAFANA_TOKEN = process.env[TOKEN_ENV_VAR];
const DATASOURCE_CONFIG = process.env.DATASOURCE_UIDS
  ? process.env.DATASOURCE_UIDS.split(',').map((s) => s.trim()).filter(Boolean)
  : [];
const DESCRIPTIONS_JSON = process.env.DATASOURCE_DESCRIPTIONS || '';
const HTTP_TIMEOUT_MS = process.env.HTTP_TIMEOUT_MS ? parseInt(process.env.HTTP_TIMEOUT_MS) : 15000;

// Datasources will be populated from Grafana API
// In-memory cache of discovered datasources: { uid: { uid, name, type, typeNormalized, description } }
let DATASOURCES = {};
let enabledDatasources = {};

// Optional manual descriptions map { uid: description }
let DATASOURCE_DESCRIPTIONS = {};

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

// HTTP client helpers
const http = axios.create({
  baseURL: `${GRAFANA_URL}`,
  headers: {
    Authorization: `Bearer ${GRAFANA_TOKEN}`,
    'Content-Type': 'application/json',
  },
  timeout: HTTP_TIMEOUT_MS,
});

async function grafanaGet(path, params = {}) {
  const res = await http.get(`/api${path}`, { params });
  return res.data;
}

// Helper to query datasource proxy
async function datasourceGet(datasourceUid, path, params = {}) {
  const res = await http.get(`/api/datasources/proxy/uid/${datasourceUid}${path}`, { params });
  return res.data;
}

async function grafanaDsQueryPost(body) {
  // Unified Grafana data query API (works across many datasources)
  const res = await http.post('/api/ds/query', body);
  return res.data;
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

function parseDurationToSeconds(input) {
  if (!input) return 30; // default 30s
  if (typeof input === 'number') return input;
  const m = String(input).match(/^(\d+)([smhd])$/);
  if (!m) {
    const n = Number(input);
    if (!isNaN(n)) return n;
    throw new Error(`Invalid duration: ${input}`);
  }
  const val = parseInt(m[1]);
  const unit = m[2];
  const mult = unit === 's' ? 1 : unit === 'm' ? 60 : unit === 'h' ? 3600 : 86400;
  return val * mult;
}

function loadDescriptions() {
  const map = {};
  try {
    if (DESCRIPTIONS_JSON) {
      Object.assign(map, JSON.parse(DESCRIPTIONS_JSON));
    }
  } catch (e) {
    console.error('Failed to parse DATASOURCE_DESCRIPTIONS JSON:', e.message);
  }
  return map;
}

// Discover datasources from Grafana
async function discoverDatasources() {
  try {
    console.error('Discovering datasources from Grafana...');
    const datasources = await grafanaGet('/datasources');
    DATASOURCE_DESCRIPTIONS = loadDescriptions();
    
    // Build datasource map
    const found = {};
    for (const ds of datasources) {
      const typeNormalized = normalizeType(ds.type);
      if (["loki","prometheus","clickhouse"].includes(typeNormalized)) {
        found[ds.uid] = {
          uid: ds.uid,
          name: ds.name,
          type: ds.type,
          typeNormalized,
          description: DATASOURCE_DESCRIPTIONS[ds.uid] || '',
        };
      }
    }
    DATASOURCES = found;
    
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
      console.error(`  - ${config.name} (${config.typeNormalized}): ${uid}${config.description ? ' - '+config.description : ''}`);
    }
    
    return DATASOURCES;
  } catch (error) {
    console.error('Failed to discover datasources:', error.message);
    throw error;
  }
}

// Tool implementations
function firstUidOfType(typeNorm) {
  return Object.values(enabledDatasources).find((ds) => ds.typeNormalized === typeNorm)?.uid;
}

const requireUidForType = (typeNorm, provided, dsMap = enabledDatasources) => baseRequireUidForType(typeNorm, provided, dsMap);

const toolHandlers = {
  // List discovered datasources with optional type filter
  async list_datasources({ type } = {}) {
    const list = Object.values(enabledDatasources)
      .filter((d) => !type || d.typeNormalized === type)
      .map(({ uid, name, type, typeNormalized, description }) => ({ uid, name, type, typeNormalized, description }));
    return { datasources: list };
  },

  // Loki: support actions: query, labels, label_values
  async loki_tool({ action = 'query', query, start = 'now-1h', end = 'now', limit = 100, label, datasource_uid }) {
    const datasourceUid = requireUidForType('loki', datasource_uid);
    const startNs = parseTime(start);
    const endNs = parseTime(end);
    if (action === 'query') {
      if (!query) throw new Error('query is required for action=query');
      return await datasourceGet(datasourceUid, '/loki/api/v1/query_range', {
        query,
        start: startNs,
        end: endNs,
        limit,
      });
    } else if (action === 'labels') {
      return await datasourceGet(datasourceUid, '/loki/api/v1/labels', { start: startNs, end: endNs });
    } else if (action === 'label_values') {
      if (!label) throw new Error('label is required for action=label_values');
      return await datasourceGet(datasourceUid, `/loki/api/v1/label/${label}/values`, { start: startNs, end: endNs });
    }
    throw new Error(`Unknown action for loki_tool: ${action}`);
  },

  // Prometheus: instant or range query
  async prometheus_tool({ mode = 'instant', query, time = 'now', start = 'now-1h', end = 'now', step = '30s', datasource_uid }) {
    const datasourceUid = requireUidForType('prometheus', datasource_uid);
    if (!query) throw new Error('query is required');
    if (mode === 'instant') {
      const t = time === 'now' ? Math.floor(Date.now() / 1000) : Math.floor(new Date(time).getTime() / 1000);
      return await datasourceGet(datasourceUid, '/api/v1/query', { query, time: t });
    } else if (mode === 'range') {
      const startSec = Math.floor((parseTime(start) / 1e9));
      const endSec = Math.floor((parseTime(end) / 1e9));
      const stepSec = parseDurationToSeconds(step);
      return await datasourceGet(datasourceUid, '/api/v1/query_range', { query, start: startSec, end: endSec, step: stepSec });
    }
    throw new Error(`Unknown mode for prometheus_tool: ${mode}`);
  },

  // ClickHouse: SQL via Grafana unified query API
  // Note: Requires a ClickHouse datasource that supports raw SQL queries via Grafana query model.
  async clickhouse_tool({ sql, from = 'now-1h', to = 'now', datasource_uid }) {
    const datasourceUid = requireUidForType('clickhouse', datasource_uid);
    if (!sql) throw new Error('sql is required');
    const fromMs = Math.floor(parseTime(from) / 1e6);
    const toMs = Math.floor(parseTime(to) / 1e6);
    const ds = enabledDatasources[datasourceUid];
    const body = {
      from: String(fromMs),
      to: String(toMs),
      queries: [
        {
          refId: 'A',
          datasource: { uid: datasourceUid, type: ds.type },
          queryType: 'sql',
          editorMode: 'code',
          format: 'table',
          rawSql: sql,
        },
      ],
    };
    return await grafanaDsQueryPost(body);
  },
};

// Define available tools based on enabled datasources
server.setRequestHandler(ListToolsRequestSchema, async () => {
  // Consolidated tools: one per type + listing tool
  const tools = [
    {
      name: 'list_datasources',
      description: 'List discovered datasources with optional type filter',
      inputSchema: {
        type: 'object',
        properties: {
          type: { type: 'string', enum: ['loki', 'prometheus', 'clickhouse'], description: 'Optional type filter' },
        },
      },
    },
    {
      name: 'loki_tool',
      description: 'Interact with Loki: actions=query|labels|label_values',
      inputSchema: {
        type: 'object',
        properties: {
          action: { type: 'string', enum: ['query', 'labels', 'label_values'], description: 'Loki action' },
          query: { type: 'string', description: 'LogQL query string (for action=query)' },
          start: { type: 'string', description: 'Start time (e.g., "now-1h", RFC3339)' },
          end: { type: 'string', description: 'End time (e.g., "now", RFC3339)' },
          limit: { type: 'integer', description: 'Max log lines to return (default: 100)' },
          label: { type: 'string', description: 'Label name (for action=label_values)' },
          datasource_uid: { type: 'string', description: 'Datasource UID (required if multiple Loki datasources)' },
        },
      },
    },
    {
      name: 'prometheus_tool',
      description: 'Query Prometheus: mode=instant|range',
      inputSchema: {
        type: 'object',
        properties: {
          mode: { type: 'string', enum: ['instant', 'range'], description: 'Query mode' },
          query: { type: 'string', description: 'PromQL query string' },
          time: { type: 'string', description: 'Instant timestamp (RFC3339 or "now")' },
          start: { type: 'string', description: 'Range start (e.g., "now-1h")' },
          end: { type: 'string', description: 'Range end (e.g., "now")' },
          step: { type: 'string', description: 'Range step (e.g., "30s")' },
          datasource_uid: { type: 'string', description: 'Datasource UID (required if multiple Prometheus datasources)' },
        },
        required: ['query'],
      },
    },
    {
      name: 'clickhouse_tool',
      description: 'Run SQL against ClickHouse datasource via Grafana',
      inputSchema: {
        type: 'object',
        properties: {
          sql: { type: 'string', description: 'SQL query to execute' },
          from: { type: 'string', description: 'Time range start (e.g., "now-1h")' },
          to: { type: 'string', description: 'Time range end (e.g., "now")' },
          datasource_uid: { type: 'string', description: 'Datasource UID (required if multiple ClickHouse datasources)' },
        },
        required: ['sql'],
      },
    },
  ];
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
    console.error(`Tool '${name}' error:`, error?.response?.data || error.message);
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
  if (!GRAFANA_TOKEN) {
    console.error(`Error: ${TOKEN_ENV_VAR} environment variable is required`);
    process.exit(1);
  }
  // Discover datasources on startup
  enabledDatasources = await discoverDatasources();
  
  const transport = new StdioServerTransport();
  await server.connect(transport);
  
  console.error(`MCP Server 'ethpandaops-data' is running`);
}

// Only run main() when executed directly, not when imported for tests
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error('Server error:', error);
    process.exit(1);
  });
}

// Exports for tests
export { parseTime, parseDurationToSeconds, normalizeType, requireUidForType };
