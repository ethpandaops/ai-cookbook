#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
  McpError,
  ErrorCode,
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';
import fs from 'fs/promises';
import os from 'os';
import path from 'path';
import crypto from 'crypto';
import toJsonSchema from 'to-json-schema';
import jq from 'node-jq';
import { parseTime, parseDurationToSeconds, normalizeType, requireUidForType as baseRequireUidForType } from './utils.js';

const GRAFANA_URL = process.env.GRAFANA_URL || 'https://grafana.primary.production.platform.ethpandaops.io';
// Simple token resolution: either direct or via named env var
const TOKEN_ENV_VAR = process.env.GRAFANA_SERVICE_TOKEN_ENV_VAR;
const GRAFANA_TOKEN = process.env.GRAFANA_SERVICE_TOKEN || (TOKEN_ENV_VAR ? process.env[TOKEN_ENV_VAR] : null);
const DATASOURCE_CONFIG = process.env.DATASOURCE_UIDS
  ? process.env.DATASOURCE_UIDS.split(',').map((s) => s.trim()).filter(Boolean)
  : [];
const DESCRIPTIONS_JSON = process.env.DATASOURCE_DESCRIPTIONS || '';
const REQUIRED_READING_JSON = process.env.DATASOURCE_REQUIRED_READING || '';
const HTTP_TIMEOUT_MS = process.env.HTTP_TIMEOUT_MS ? parseInt(process.env.HTTP_TIMEOUT_MS) : 30000;

const STORAGE_ROOT = process.env.GRAFANA_RESULT_DIR || path.join(os.tmpdir(), 'ai-cookbook-grafana');
const RESULTS_DIR = path.join(STORAGE_ROOT, 'results');
const CATALOG_PATH = path.join(STORAGE_ROOT, 'catalog.json');

function parseEnvInt(name, fallback) {
  const raw = process.env[name];
  if (!raw) {
    return fallback;
  }
  const parsed = parseInt(raw, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

const MAX_RESOURCE_BYTES = parseEnvInt('GRAFANA_MAX_RESOURCE_BYTES', 5 * 1024 * 1024);
const MAX_INLINE_BYTES = parseEnvInt('GRAFANA_MAX_INLINE_BYTES', 64 * 1024); // 64KB default
const RESULT_TTL_HOURS = parseEnvInt('GRAFANA_RESULT_TTL_HOURS', 0); // 0 disables TTL pruning

const CATALOG_LOCK_PATH = path.join(STORAGE_ROOT, 'catalog.lock');
const CATALOG_LOCK_TIMEOUT_MS = parseEnvInt('GRAFANA_CATALOG_LOCK_TIMEOUT_MS', 5000);
const CATALOG_LOCK_POLL_MS = parseEnvInt('GRAFANA_CATALOG_LOCK_POLL_MS', 50);
const CATALOG_LOCK_STALE_MS = parseEnvInt('GRAFANA_CATALOG_LOCK_STALE_MS', 60000);

const WORKFLOW_INSTRUCTIONS = `Use this server to run Grafana-backed queries with support for Grafana template macros.

Query Tools:
- *_query tools (clickhouse_query, prometheus_query, loki_query): Return data inline up to 64KB for quick iteration
- *_query_to_resource tools: Persist large results to disk and return file_path/resource_uri

Grafana Macros (automatically expanded):
- ClickHouse: $__timeFilter(column), $__fromTime, $__toTime, $__interval_s, $__timeInterval(column)
- Prometheus: $__interval, $__rate_interval, $__range, $__range_s, $__range_ms
- Loki: Time filtering via start/end params (no macros needed)

Workflow:
1. Call *_query for small results or *_query_to_resource for large datasets
2. Use Grafana macros in your queries for dynamic time filtering and intervals
3. For persisted results, use resources/read with ?limit, ?offset, or ?jq filters
4. Clean up with delete_result or trim_results when finished`;

const RESULT_FILE_EXTENSION = 'json';
const MAX_SCHEMA_SAMPLE_SIZE = 3; // Number of items to sample when generating schema

let catalog = new Map();
let storageInitialized = false;

// Datasources will be populated from Grafana API
// In-memory cache of discovered datasources: { uid: { uid, name, type, typeNormalized, description } }
let DATASOURCES = {};
let enabledDatasources = {};

// Optional manual descriptions map { uid: description }
let DATASOURCE_DESCRIPTIONS = {};

// Optional required reading map { uid: url_or_path }
let DATASOURCE_REQUIRED_READING = {};

// Session state: track which datasources have had their knowledge loaded
let loadedKnowledge = new Set();

const RESOURCE_URI_PREFIX = 'mcp://ethpandaops-data/result/';

function resultIdToUri(id) {
  return `${RESOURCE_URI_PREFIX}${id}`;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function uriToResultId(uri) {
  if (typeof uri !== 'string') {
    return null;
  }
  return uri.startsWith(RESOURCE_URI_PREFIX) ? uri.slice(RESOURCE_URI_PREFIX.length) : null;
}

async function acquireCatalogLock() {
  const start = Date.now();
  while (true) {
    try {
      const handle = await fs.open(CATALOG_LOCK_PATH, 'wx');
      try {
        await handle.write(`${process.pid}:${Date.now()}\n`);
      } catch (writeError) {
        console.error('Failed to write catalog lock metadata:', writeError.message);
      }
      return handle;
    } catch (error) {
      if (error.code !== 'EEXIST') {
        throw error;
      }
      let stale = false;
      try {
        const stats = await fs.stat(CATALOG_LOCK_PATH);
        if (Date.now() - stats.mtimeMs > CATALOG_LOCK_STALE_MS) {
          await fs.unlink(CATALOG_LOCK_PATH);
          stale = true;
        }
      } catch (statError) {
        if (statError.code === 'ENOENT') {
          continue;
        }
        console.error('Catalog lock stat error:', statError.message);
      }
      if (stale) {
        continue;
      }
      if (Date.now() - start > CATALOG_LOCK_TIMEOUT_MS) {
        throw new Error(`Timed out acquiring catalog lock at ${CATALOG_LOCK_PATH}`);
      }
      await sleep(CATALOG_LOCK_POLL_MS);
    }
  }
}

async function releaseCatalogLock(handle) {
  try {
    if (handle) {
      await handle.close();
    }
  } catch (error) {
    console.error('Failed to close catalog lock handle:', error.message);
  }
  try {
    await fs.unlink(CATALOG_LOCK_PATH);
  } catch (error) {
    if (error.code !== 'ENOENT') {
      console.error('Failed to release catalog lock file:', error.message);
    }
  }
}

async function withCatalogWriteLock(mutator) {
  const handle = await acquireCatalogLock();
  try {
    await loadCatalogFromDisk();
    const { result, changed } = await mutator();
    if (changed) {
      await saveCatalogToDisk();
    }
    return { result, changed };
  } finally {
    await releaseCatalogLock(handle);
  }
}

async function ensureStorage() {
  if (storageInitialized) {
    return;
  }
  await fs.mkdir(RESULTS_DIR, { recursive: true });
  await loadCatalogFromDisk();
  await pruneCatalog({ skipNotification: true });
  storageInitialized = true;
}

async function loadCatalogFromDisk() {
  try {
    const raw = await fs.readFile(CATALOG_PATH, 'utf8');
    const parsed = JSON.parse(raw);
    const entries = new Map();
    if (Array.isArray(parsed.results)) {
      for (const entry of parsed.results) {
        if (entry && entry.id && entry.file_path) {
          entries.set(entry.id, entry);
        }
      }
    }
    catalog = entries;
  } catch (error) {
    if (error && error.code !== 'ENOENT') {
      console.error('Failed to load catalog:', error.message);
    }
    catalog = new Map();
  }
}

async function saveCatalogToDisk() {
  const payload = {
    version: 1,
    generated_at: new Date().toISOString(),
    results: Array.from(catalog.values()),
  };
  await fs.writeFile(CATALOG_PATH, JSON.stringify(payload, null, 2), 'utf8');
}

function sanitizeArgsForCatalog(args = {}) {
  const clone = { ...args };
  return clone;
}

function computeArgsHash(args = {}) {
  const hasher = crypto.createHash('sha256');
  hasher.update(JSON.stringify(args));
  return hasher.digest('hex');
}

/**
 * Generates a JSON schema from data with optimizations to reduce token usage
 */
function generateDataSchema(data, options = {}) {
  const sampleSize = options.sampleSize || MAX_SCHEMA_SAMPLE_SIZE;

  // Create a representative sample for schema generation
  const sample = createSchemaSample(data, sampleSize);

  // Generate schema with optimizations
  const schema = toJsonSchema(sample, {
    required: false,
    postProcessFnc: (type, schema, obj, defaultFunc) => {
      const result = defaultFunc(type, schema, obj);

      // Remove examples to save tokens
      delete result.examples;
      delete result.default;

      // For arrays, just note the count instead of full schema duplication
      if (type === 'array' && Array.isArray(obj)) {
        result.minItems = obj.length;
        result.maxItems = obj.length;
      }

      return result;
    }
  });

  return schema;
}

/**
 * Creates a representative sample from data for schema generation
 */
function createSchemaSample(data, sampleSize) {
  if (!data || typeof data !== 'object') {
    return data;
  }

  if (Array.isArray(data)) {
    // For arrays, take first few items
    return data.slice(0, sampleSize);
  }

  // For objects, recursively sample nested arrays
  const sample = {};
  for (const [key, value] of Object.entries(data)) {
    if (Array.isArray(value) && value.length > sampleSize) {
      sample[key] = value.slice(0, sampleSize);
    } else if (value && typeof value === 'object' && !Array.isArray(value)) {
      sample[key] = createSchemaSample(value, sampleSize);
    } else {
      sample[key] = value;
    }
  }

  return sample;
}

/**
 * Collects metadata about the result (row counts, sizes, etc.)
 */
function collectResultMetadata(raw, toolName) {
  if (toolName === 'clickhouse_tool') {
    const resultBlocks = raw?.results || {};
    let totalRows = 0;
    let totalColumns = 0;

    for (const block of Object.values(resultBlocks)) {
      const frames = Array.isArray(block?.frames) ? block.frames : [];
      for (const frame of frames) {
        const values = Array.isArray(frame?.data?.values) ? frame.data.values : [];
        if (values.length > 0) {
          totalRows += values[0].length || 0;
          totalColumns = Math.max(totalColumns, values.length);
        }
      }
    }

    return {
      data_type: 'tabular',
      row_count: totalRows,
      column_count: totalColumns,
      frame_count: Object.keys(resultBlocks).length
    };
  }

  if (toolName === 'prometheus_tool') {
    const series = Array.isArray(raw?.data?.result) ? raw.data.result : [];
    let sampleCount = 0;

    for (const seriesItem of series) {
      const values = Array.isArray(seriesItem?.values) ? seriesItem.values : [];
      sampleCount += values.length || (Array.isArray(seriesItem?.value) ? 1 : 0);
    }

    return {
      data_type: 'time_series',
      series_count: series.length,
      sample_count: sampleCount,
      result_type: raw?.data?.resultType || 'unknown'
    };
  }

  if (toolName === 'loki_tool') {
    const streams = Array.isArray(raw?.data?.result) ? raw.data.result : [];
    let entryCount = 0;

    for (const stream of streams) {
      const values = Array.isArray(stream?.values) ? stream.values : [];
      entryCount += values.length;
    }

    return {
      data_type: 'log_streams',
      stream_count: streams.length,
      entry_count: entryCount,
      result_type: raw?.data?.resultType || 'unknown'
    };
  }

  // Unknown tool - use generic metadata
  return {
    data_type: 'unknown',
    is_array: Array.isArray(raw),
    is_object: raw && typeof raw === 'object'
  };
}

async function notifyResourceListChanged() {
  try {
    if (server.transport) {
      await server.sendResourceListChanged();
    }
  } catch (error) {
    console.error('Failed to send resource list notification:', error.message);
  }
}

/**
 * Generates a short random ID (10 chars, base36)
 */
function generateShortId() {
  // Generate 8 random bytes and convert to base36
  const randomBytes = crypto.randomBytes(8);
  const randomNum = randomBytes.readBigUInt64BE(0);
  return randomNum.toString(36).slice(0, 10).padStart(10, '0');
}

async function persistResultEntry({
  toolName,
  datasourceUid,
  args,
  rawResult,
  summary = {},
  deliveryMeta = {},
}) {
  await ensureStorage();

  const id = generateShortId();
  const fileName = `${id}.${RESULT_FILE_EXTENSION}`;
  const filePath = path.join(RESULTS_DIR, fileName);

  await fs.writeFile(filePath, typeof rawResult === 'string' ? rawResult : JSON.stringify(rawResult), 'utf8');
  const stats = await fs.stat(filePath);

  const entry = {
    id,
    tool: toolName,
    datasource_uid: datasourceUid,
    format: RESULT_FILE_EXTENSION,
    file_path: filePath,
    file_name: fileName,
    size_bytes: stats.size,
    created_at: new Date().toISOString(),
    input: sanitizeArgsForCatalog(args),
    input_hash: computeArgsHash(args),
    summary,
    delivery_meta: deliveryMeta,
  };

  await withCatalogWriteLock(async () => {
    catalog.set(id, entry);
    return { result: entry, changed: true };
  });
  await notifyResourceListChanged();
  return entry;
}

/**
 * Formats bytes to human-readable string
 */
function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} bytes`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/**
 * Responds with inline data if size is under threshold, otherwise throws error
 */
async function respondWithInline({ toolName, args, datasourceUid, rawResult }) {
  const serialized = JSON.stringify(rawResult);
  const sizeBytes = Buffer.byteLength(serialized, 'utf8');

  if (sizeBytes > MAX_INLINE_BYTES) {
    const toolNameResource = toolName.replace('_query', '_query_to_resource');
    throw new Error(
      `Query result too large for inline response (${formatBytes(sizeBytes)}, max: ${formatBytes(MAX_INLINE_BYTES)}).\n\n` +
      `Use ${toolNameResource} instead to persist the result and access via resource URI.\n` +
      `This allows filtering with ?limit, ?offset, and ?jq parameters.`
    );
  }

  return rawResult;
}

/**
 * Responds with result structure and schema only.
 * Never returns actual data - forces LLM to use resources/read with filters.
 */
async function respondWithResult({ toolName, args, datasourceUid, rawResult }) {
  const serialized = JSON.stringify(rawResult);
  const sizeBytes = Buffer.byteLength(serialized, 'utf8');

  // Generate schema and metadata
  const schema = generateDataSchema(rawResult);
  const metadata = collectResultMetadata(rawResult, toolName);

  // Always persist the result
  const entry = await persistResultEntry({
    toolName,
    datasourceUid,
    args,
    rawResult: serialized,
    summary: { ...metadata, schema },
    deliveryMeta: { size_bytes: sizeBytes },
  });

  const baseUri = resultIdToUri(entry.id);

  // Generate quick access examples
  const quickAccess = [];
  quickAccess.push(`Full data: ${baseUri}`);
  quickAccess.push(`Paginated: ${baseUri}?limit=100`);

  if (metadata.data_type === 'time_series') {
    quickAccess.push(`Filtered: ${baseUri}?jq=.data.result[]|select(.metric.job=="prometheus")`);
  } else if (metadata.data_type === 'log_streams') {
    quickAccess.push(`Filtered: ${baseUri}?jq=.data.result[].values[]|select(.[1]|contains("ERROR"))`);
  } else if (metadata.data_type === 'tabular') {
    quickAccess.push(`Filtered: ${baseUri}?jq=.results.A.frames[0].data.values`);
  }

  // Always return structure-only
  return {
    result_id: entry.id,
    resource_uri: baseUri,
    file_path: entry.file_path,

    size: formatBytes(sizeBytes),
    size_bytes: sizeBytes,

    metadata: {
      data_type: metadata.data_type,
      row_count: metadata.row_count,
      column_count: metadata.column_count,
      series_count: metadata.series_count,
      sample_count: metadata.sample_count,
      stream_count: metadata.stream_count,
      entry_count: metadata.entry_count,
      result_type: metadata.result_type,
      frame_count: metadata.frame_count,
    },

    schema,

    access: {
      describe: `Call describe_result with result_id="${entry.id}" for detailed schema and examples`,
      read: `Call resources/read with URI from quick_access below`,
      quick_access: quickAccess,
    },
  };
}

function getCatalogEntryOrThrow(resultId) {
  const entry = catalog.get(resultId);
  if (!entry) {
    throw new McpError(ErrorCode.InvalidParams, `Unknown result_id: ${resultId}`);
  }
  return entry;
}

async function pruneCatalog({ skipNotification = false } = {}) {
  const { result: plan, changed } = await withCatalogWriteLock(async () => {
    const removalPlan = [];
    const now = Date.now();
    let mutated = false;

    for (const entry of Array.from(catalog.values())) {
      let remove = false;
      try {
        const stats = await fs.stat(entry.file_path);
        entry.size_bytes = stats.size;
      } catch (error) {
        if (error.code === 'ENOENT') {
          remove = true;
        } else {
          console.error(`Failed to stat ${entry.file_path}:`, error.message);
        }
      }

      if (!remove && RESULT_TTL_HOURS > 0) {
        const createdAt = Date.parse(entry.created_at || '');
        if (!Number.isNaN(createdAt)) {
          const ageHours = (now - createdAt) / (1000 * 60 * 60);
          if (ageHours > RESULT_TTL_HOURS) {
            remove = true;
            removalPlan.push({ entry, deleteFile: true });
          }
        }
      }

      if (remove) {
        if (!removalPlan.find((item) => item.entry.id === entry.id)) {
          removalPlan.push({ entry, deleteFile: false });
        }
        catalog.delete(entry.id);
        mutated = true;
      }
    }

    return { result: removalPlan, changed: mutated };
  });

  const removalPlan = plan || [];

  if (removalPlan.length > 0) {
    for (const { entry, deleteFile } of removalPlan) {
      if (deleteFile) {
        try {
          await fs.unlink(entry.file_path);
        } catch (error) {
          if (error.code !== 'ENOENT') {
            console.error(`Failed to remove expired result file ${entry.file_path}:`, error.message);
          }
        }
      }
    }
  }

  if (changed && !skipNotification) {
    await notifyResourceListChanged();
  }
}

function catalogEntriesSorted() {
  return Array.from(catalog.values()).sort((a, b) => {
    const timeA = Date.parse(a.created_at || '') || 0;
    const timeB = Date.parse(b.created_at || '') || 0;
    return timeB - timeA;
  });
}

const server = new Server(
  {
    name: 'ethpandaops-data',
    version: '0.4.0',
  },
  {
    capabilities: {
      tools: { listChanged: true },
      resources: { listChanged: true },
    },
    instructions: WORKFLOW_INSTRUCTIONS,
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

// parseTime and parseDurationToSeconds imported from utils.js

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

function loadRequiredReading() {
  const map = {};
  try {
    if (REQUIRED_READING_JSON) {
      Object.assign(map, JSON.parse(REQUIRED_READING_JSON));
    }
  } catch (e) {
    console.error('Failed to parse DATASOURCE_REQUIRED_READING JSON:', e.message);
  }
  return map;
}

/**
 * Check if a datasource requires knowledge to be loaded before querying
 * @param {string} datasourceUid - The datasource UID to check
 * @throws {Error} if knowledge is required but not loaded
 */
function validateKnowledgeLoaded(datasourceUid) {
  if (DATASOURCE_REQUIRED_READING[datasourceUid]) {
    if (!loadedKnowledge.has(datasourceUid)) {
      const readingSource = DATASOURCE_REQUIRED_READING[datasourceUid];
      throw new Error(
        `Knowledge loading required for datasource ${datasourceUid}.\n\n` +
        `You must call the load_knowledge tool with datasource_uid="${datasourceUid}" before querying this datasource.\n` +
        `This datasource requires you to read: ${readingSource}\n\n` +
        `Example: load_knowledge({ datasource_uid: "${datasourceUid}" })`
      );
    }
  }
}

/**
 * Load required knowledge for a datasource (from URL or file path)
 * @param {string} source - URL or file path to load knowledge from
 * @returns {Promise<string>} The knowledge content
 */
async function loadKnowledgeContent(source) {
  // Check if it's a URL
  if (source.startsWith('http://') || source.startsWith('https://')) {
    try {
      const response = await axios.get(source, {
        timeout: HTTP_TIMEOUT_MS,
        headers: {
          'User-Agent': 'ethpandaops-data-mcp/0.4.0'
        }
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch knowledge from URL ${source}: ${error.message}`);
    }
  } else {
    // It's a file path
    try {
      const content = await fs.readFile(source, 'utf8');
      return content;
    } catch (error) {
      throw new Error(`Failed to read knowledge from file ${source}: ${error.message}`);
    }
  }
}

// Discover datasources from Grafana
async function discoverDatasources() {
  try {
    console.error('Discovering datasources from Grafana...');
    const datasources = await grafanaGet('/datasources');
    DATASOURCE_DESCRIPTIONS = loadDescriptions();
    DATASOURCE_REQUIRED_READING = loadRequiredReading();
    
    // Build datasource map
    const found = {};
    for (const ds of datasources) {
      const typeNormalized = normalizeType(ds.type);
      if (["loki","prometheus","clickhouse"].includes(typeNormalized)) {
        // Only include datasources that have a description
        const description = DATASOURCE_DESCRIPTIONS[ds.uid];
        if (description) {
          found[ds.uid] = {
            uid: ds.uid,
            name: ds.name,
            type: ds.type,
            typeNormalized,
            description: description,
          };
        } else {
          console.error(`  Skipping ${ds.name} (${ds.type}) - no description provided`);
        }
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
  // Load required knowledge for a datasource before querying
  async load_knowledge({ datasource_uid }) {
    if (!datasource_uid) {
      throw new McpError(ErrorCode.InvalidParams, 'datasource_uid is required');
    }

    // Check if datasource exists
    const datasource = enabledDatasources[datasource_uid];
    if (!datasource) {
      throw new McpError(
        ErrorCode.InvalidParams,
        `Unknown datasource_uid: ${datasource_uid}. Call list_datasources to see available datasources.`
      );
    }

    // Check if required reading is configured for this datasource
    const readingSource = DATASOURCE_REQUIRED_READING[datasource_uid];
    if (!readingSource) {
      return {
        datasource_uid,
        datasource_name: datasource.name,
        required_reading: false,
        message: 'No required reading configured for this datasource. You may query it directly.',
      };
    }

    // Load the knowledge content
    const content = await loadKnowledgeContent(readingSource);

    // Mark this datasource as having loaded knowledge
    loadedKnowledge.add(datasource_uid);

    return {
      datasource_uid,
      datasource_name: datasource.name,
      datasource_type: datasource.typeNormalized,
      required_reading: true,
      source: readingSource,
      knowledge_loaded: true,
      content,
      message: `Knowledge loaded successfully. You may now query this datasource.`,
    };
  },

  // Health check tool to verify connection to Grafana
  async health_check() {
    try {
      await ensureStorage();
      // Check if we have a token
      if (!GRAFANA_TOKEN) {
        return {
          healthy: false,
          error: 'No Grafana service token configured',
          help: 'Please set GRAFANA_SERVICE_TOKEN environment variable or use GRAFANA_SERVICE_TOKEN_ENV_VAR to specify which env var contains the token'
        };
      }

      // Try to fetch user info to verify authentication
      const userInfo = await grafanaGet('/user');
      
      // Check datasources
      const datasourceCount = Object.keys(enabledDatasources).length;
      
      // Determine health status
      const healthy = datasourceCount > 0;
      const status = datasourceCount === 0 ? 'warning' : 'healthy';
      
      // Check required reading status
      const datasourcesWithRequiredReading = Object.keys(DATASOURCE_REQUIRED_READING).filter(
        uid => enabledDatasources[uid]
      );
      const requiredReadingStatus = datasourcesWithRequiredReading.map(uid => ({
        uid,
        name: enabledDatasources[uid]?.name,
        source: DATASOURCE_REQUIRED_READING[uid],
        loaded: loadedKnowledge.has(uid)
      }));

      return {
        healthy: healthy,
        status: status,
        grafana_url: GRAFANA_URL,
        authenticated: true,
        user: userInfo.login || userInfo.name,
        datasources_discovered: datasourceCount,
        datasources: Object.values(enabledDatasources).map(ds => ({
          name: ds.name,
          type: ds.typeNormalized,
          uid: ds.uid,
          requires_knowledge: !!DATASOURCE_REQUIRED_READING[ds.uid],
          knowledge_loaded: loadedKnowledge.has(ds.uid)
        })),
        required_reading: {
          configured: datasourcesWithRequiredReading.length,
          status: requiredReadingStatus
        },
        catalog_entries: catalog.size,
        result_storage: {
          directory: RESULTS_DIR,
          max_inline_size: formatBytes(MAX_INLINE_BYTES),
          max_resource_size: formatBytes(MAX_RESOURCE_BYTES),
        },
        features: [
          'Inline query tools (*_query) return data directly up to 64KB',
          'Resource query tools (*_query_to_resource) save to disk and return file_path/resource_uri',
          'Automatic JSON schema generation for all query results',
          'Resource templates with filtering (?limit, ?offset, ?jq)',
          'JQ expression filtering for complex queries',
          'Error-driven workflow guides you to the right tool',
          'Knowledge loading enforcement for datasources with DATASOURCE_REQUIRED_READING',
        ],
        message: datasourceCount === 0
          ? 'Connected to Grafana but no datasources discovered. Check permissions or datasource configuration.'
          : `Successfully connected. ${datasourceCount} datasource(s) available.`
      };
    } catch (error) {
      return {
        healthy: false,
        error: error.message,
        grafana_url: GRAFANA_URL,
        help: error.response?.status === 401 
          ? 'Authentication failed. Please check your Grafana service token. You can create one at: ' + GRAFANA_URL + '/org/serviceaccounts'
          : 'Failed to connect to Grafana. Please check your GRAFANA_URL and network connection.'
      };
    }
  },

  // List discovered datasources with optional type filter
  async list_datasources({ type } = {}) {
    const list = Object.values(enabledDatasources)
      .filter((d) => !type || d.typeNormalized === type)
      .map(({ uid, name, type, typeNormalized, description }) => ({ uid, name, type, typeNormalized, description }));
    return { datasources: list };
  },

  // Loki query - inline response
  async loki_query(args = {}) {
    const {
      action = 'query',
      query,
      start = 'now-1h',
      end = 'now',
      limit = 100,
      label,
      datasource_uid,
    } = args;

    const datasourceUid = requireUidForType('loki', datasource_uid);
    validateKnowledgeLoaded(datasourceUid);
    const startNs = parseTime(start);
    const endNs = parseTime(end);

    let rawResult;
    if (action === 'query') {
      if (!query) throw new Error('query is required for action=query');
      rawResult = await datasourceGet(datasourceUid, '/loki/api/v1/query_range', {
        query,
        start: startNs,
        end: endNs,
        limit,
      });
    } else if (action === 'labels') {
      rawResult = await datasourceGet(datasourceUid, '/loki/api/v1/labels', { start: startNs, end: endNs });
    } else if (action === 'label_values') {
      if (!label) throw new Error('label is required for action=label_values');
      rawResult = await datasourceGet(datasourceUid, `/loki/api/v1/label/${label}/values`, { start: startNs, end: endNs });
    } else {
      throw new Error(`Unknown action for loki_query: ${action}`);
    }

    return respondWithInline({
      toolName: 'loki_query',
      args,
      datasourceUid,
      rawResult,
    });
  },

  // Loki query to resource - persists and returns resource URI
  async loki_query_to_resource(args = {}) {
    const {
      action = 'query',
      query,
      start = 'now-1h',
      end = 'now',
      limit = 100,
      label,
      datasource_uid,
    } = args;

    const datasourceUid = requireUidForType('loki', datasource_uid);
    validateKnowledgeLoaded(datasourceUid);
    const startNs = parseTime(start);
    const endNs = parseTime(end);

    let rawResult;
    if (action === 'query') {
      if (!query) throw new Error('query is required for action=query');
      rawResult = await datasourceGet(datasourceUid, '/loki/api/v1/query_range', {
        query,
        start: startNs,
        end: endNs,
        limit,
      });
    } else if (action === 'labels') {
      rawResult = await datasourceGet(datasourceUid, '/loki/api/v1/labels', { start: startNs, end: endNs });
    } else if (action === 'label_values') {
      if (!label) throw new Error('label is required for action=label_values');
      rawResult = await datasourceGet(datasourceUid, `/loki/api/v1/label/${label}/values`, { start: startNs, end: endNs });
    } else {
      throw new Error(`Unknown action for loki_query_to_resource: ${action}`);
    }

    return respondWithResult({
      toolName: 'loki_query_to_resource',
      args,
      datasourceUid,
      rawResult,
    });
  },

  // Prometheus query - inline response
  async prometheus_query(args = {}) {
    const {
      mode = 'instant',
      query,
      time = 'now',
      start = 'now-1h',
      end = 'now',
      step = '30s',
      datasource_uid,
    } = args;

    const datasourceUid = requireUidForType('prometheus', datasource_uid);
    validateKnowledgeLoaded(datasourceUid);
    if (!query) throw new Error('query is required');

    let rawResult;
    if (mode === 'instant') {
      const t = time === 'now' ? Math.floor(Date.now() / 1000) : Math.floor(new Date(time).getTime() / 1000);
      rawResult = await datasourceGet(datasourceUid, '/api/v1/query', { query, time: t });
    } else if (mode === 'range') {
      const startSec = Math.floor(parseTime(start) / 1e9);
      const endSec = Math.floor(parseTime(end) / 1e9);
      const stepSec = parseDurationToSeconds(step);
      rawResult = await datasourceGet(datasourceUid, '/api/v1/query_range', { query, start: startSec, end: endSec, step: stepSec });
    } else {
      throw new Error(`Unknown mode for prometheus_query: ${mode}`);
    }

    return respondWithInline({
      toolName: 'prometheus_query',
      args,
      datasourceUid,
      rawResult,
    });
  },

  // Prometheus query to resource - persists and returns resource URI
  async prometheus_query_to_resource(args = {}) {
    const {
      mode = 'instant',
      query,
      time = 'now',
      start = 'now-1h',
      end = 'now',
      step = '30s',
      datasource_uid,
    } = args;

    const datasourceUid = requireUidForType('prometheus', datasource_uid);
    validateKnowledgeLoaded(datasourceUid);
    if (!query) throw new Error('query is required');

    let rawResult;
    if (mode === 'instant') {
      const t = time === 'now' ? Math.floor(Date.now() / 1000) : Math.floor(new Date(time).getTime() / 1000);
      rawResult = await datasourceGet(datasourceUid, '/api/v1/query', { query, time: t });
    } else if (mode === 'range') {
      const startSec = Math.floor(parseTime(start) / 1e9);
      const endSec = Math.floor(parseTime(end) / 1e9);
      const stepSec = parseDurationToSeconds(step);
      rawResult = await datasourceGet(datasourceUid, '/api/v1/query_range', { query, start: startSec, end: endSec, step: stepSec });
    } else {
      throw new Error(`Unknown mode for prometheus_query_to_resource: ${mode}`);
    }

    return respondWithResult({
      toolName: 'prometheus_query_to_resource',
      args,
      datasourceUid,
      rawResult,
    });
  },

  // ClickHouse query - inline response
  async clickhouse_query(args = {}) {
    const { sql, from = 'now-1h', to = 'now', datasource_uid } = args;
    const datasourceUid = requireUidForType('clickhouse', datasource_uid);
    validateKnowledgeLoaded(datasourceUid);
    if (!sql) throw new Error('sql is required');

    const dangerousPatterns = [
      ';--', '/*', '*/', 'xp_', 'sp_',
      'exec(', 'execute(', 'eval(',
      'drop table', 'drop database', 'truncate',
      'insert into', 'update set', 'delete from'
    ];

    const sqlLower = sql.toLowerCase();
    for (const pattern of dangerousPatterns) {
      if (sqlLower.includes(pattern)) {
        throw new Error(`SQL query contains potentially dangerous pattern: ${pattern}.`);
      }
    }

    const fromMs = Math.floor(parseTime(from) / 1e6);
    const toMs = Math.floor(parseTime(to) / 1e6);
    const ds = enabledDatasources[datasourceUid];

    let body;
    if (ds.type === 'vertamedia-clickhouse-datasource') {
      body = {
        from: String(fromMs),
        to: String(toMs),
        queries: [
          {
            refId: 'A',
            datasource: { uid: datasourceUid, type: ds.type },
            query: sql,
            format: 'table',
            intervalMs: 1000,
            maxDataPoints: 1000,
          },
        ],
      };
    } else {
      body = {
        from: String(fromMs),
        to: String(toMs),
        queries: [
          {
            refId: 'A',
            datasource: { uid: datasourceUid, type: ds.type },
            queryType: 'sql',
            editorMode: 'code',
            format: 1,
            intervalMs: 1000,
            maxDataPoints: 1000,
            rawSql: sql,
          },
        ],
      };
    }

    const rawResult = await grafanaDsQueryPost(body);

    return respondWithInline({
      toolName: 'clickhouse_query',
      args,
      datasourceUid,
      rawResult,
    });
  },

  // ClickHouse query to resource - persists and returns resource URI
  async clickhouse_query_to_resource(args = {}) {
    const { sql, from = 'now-1h', to = 'now', datasource_uid } = args;
    const datasourceUid = requireUidForType('clickhouse', datasource_uid);
    validateKnowledgeLoaded(datasourceUid);
    if (!sql) throw new Error('sql is required');

    const dangerousPatterns = [
      ';--', '/*', '*/', 'xp_', 'sp_',
      'exec(', 'execute(', 'eval(',
      'drop table', 'drop database', 'truncate',
      'insert into', 'update set', 'delete from'
    ];

    const sqlLower = sql.toLowerCase();
    for (const pattern of dangerousPatterns) {
      if (sqlLower.includes(pattern)) {
        throw new Error(`SQL query contains potentially dangerous pattern: ${pattern}.`);
      }
    }

    const fromMs = Math.floor(parseTime(from) / 1e6);
    const toMs = Math.floor(parseTime(to) / 1e6);
    const ds = enabledDatasources[datasourceUid];

    let body;
    if (ds.type === 'vertamedia-clickhouse-datasource') {
      body = {
        from: String(fromMs),
        to: String(toMs),
        queries: [
          {
            refId: 'A',
            datasource: { uid: datasourceUid, type: ds.type },
            query: sql,
            format: 'table',
            intervalMs: 1000,
            maxDataPoints: 1000,
          },
        ],
      };
    } else {
      body = {
        from: String(fromMs),
        to: String(toMs),
        queries: [
          {
            refId: 'A',
            datasource: { uid: datasourceUid, type: ds.type },
            queryType: 'sql',
            editorMode: 'code',
            format: 1,
            intervalMs: 1000,
            maxDataPoints: 1000,
            rawSql: sql,
          },
        ],
      };
    }

    const rawResult = await grafanaDsQueryPost(body);

    return respondWithResult({
      toolName: 'clickhouse_query_to_resource',
      args,
      datasourceUid,
      rawResult,
    });
  },

  async describe_result({ result_id }) {
    if (!result_id) {
      throw new McpError(ErrorCode.InvalidParams, 'result_id is required');
    }
    await ensureStorage();
    await loadCatalogFromDisk();
    const entry = getCatalogEntryOrThrow(result_id);

    const baseUri = resultIdToUri(entry.id);
    const metadata = entry.summary || {};

    // Generate usage examples based on data type
    const examples = [];
    examples.push(`Basic access: ${baseUri}`);
    examples.push(`With pagination: ${baseUri}?limit=100&offset=0`);

    if (metadata.data_type === 'time_series') {
      examples.push(`Filter by metric: ${baseUri}?jq=.data.result[]|select(.metric.job=="prometheus")`);
      examples.push(`Get metric names: ${baseUri}?jq=.data.result[].metric.__name__|unique`);
    } else if (metadata.data_type === 'log_streams') {
      examples.push(`Filter logs: ${baseUri}?jq=.data.result[].values[]|select(.[1]|contains("ERROR"))`);
      examples.push(`Get stream labels: ${baseUri}?jq=.data.result[].stream|unique`);
    } else if (metadata.data_type === 'tabular') {
      examples.push(`First 10 rows: ${baseUri}?limit=10`);
      examples.push(`Custom selection: ${baseUri}?jq=.results.A.frames[0].data.values`);
    }

    return {
      result_id,
      tool: entry.tool,
      datasource_uid: entry.datasource_uid,
      created_at: entry.created_at,
      size: formatBytes(entry.size_bytes),
      size_bytes: entry.size_bytes,
      format: entry.format,
      resource_uri: baseUri,
      file_path: entry.file_path,

      metadata: {
        data_type: metadata.data_type,
        row_count: metadata.row_count,
        column_count: metadata.column_count,
        series_count: metadata.series_count,
        sample_count: metadata.sample_count,
        stream_count: metadata.stream_count,
        entry_count: metadata.entry_count,
        result_type: metadata.result_type,
      },

      schema: metadata.schema,

      query_input: entry.input,

      usage_examples: examples,

      filters_available: [
        'limit=N - Return max N items',
        'offset=N - Skip N items',
        'jq=EXPRESSION - Apply JQ expression for complex filtering',
      ],
    };
  },

  async delete_result({ result_id, delete_file = true }) {
    if (!result_id) {
      throw new McpError(ErrorCode.InvalidParams, 'result_id is required');
    }
    await ensureStorage();
    const { result: entry, changed } = await withCatalogWriteLock(async () => {
      const current = catalog.get(result_id);
      if (!current) {
        return { result: null, changed: false };
      }
      catalog.delete(result_id);
      return { result: current, changed: true };
    });

    if (!entry) {
      throw new McpError(ErrorCode.InvalidParams, `Unknown result_id: ${result_id}`);
    }

    let fileDeleted = false;
    if (delete_file) {
      try {
        await fs.unlink(entry.file_path);
        fileDeleted = true;
      } catch (error) {
        if (error.code === 'ENOENT') {
          fileDeleted = true;
        } else {
          console.error(`Failed to delete file ${entry.file_path}:`, error.message);
        }
      }
    }

    if (changed) {
      await notifyResourceListChanged();
    }

    return {
      result_id,
      removed: changed,
      file_deleted: fileDeleted,
    };
  },

  async trim_results({ max_age_hours, max_results } = {}) {
    await ensureStorage();

    const { result: removalPlan, changed } = await withCatalogWriteLock(async () => {
      const removed = [];

      if (typeof max_age_hours === 'number' && max_age_hours > 0) {
        const cutoff = Date.now() - max_age_hours * 60 * 60 * 1000;
        for (const entry of catalogEntriesSorted()) {
          const created = Date.parse(entry.created_at || '');
          if (!Number.isNaN(created) && created < cutoff) {
            catalog.delete(entry.id);
            removed.push({ entry, deleteFile: true });
          }
        }
      }

      if (typeof max_results === 'number' && max_results >= 0) {
        const entries = catalogEntriesSorted();
        const excess = entries.slice(max_results);
        for (const entry of excess) {
          if (!removed.find((item) => item.entry.id === entry.id)) {
            catalog.delete(entry.id);
            removed.push({ entry, deleteFile: true });
          }
        }
      }

      return { result: removed, changed: removed.length > 0 };
    });

    const removedIds = [];
    if (removalPlan && removalPlan.length > 0) {
      for (const { entry, deleteFile } of removalPlan) {
        removedIds.push(entry.id);
        if (deleteFile) {
          try {
            await fs.unlink(entry.file_path);
          } catch (error) {
            if (error.code !== 'ENOENT') {
              console.error(`Failed to remove file ${entry.file_path}:`, error.message);
            }
          }
        }
      }
    }

    if (removedIds.length > 0) {
      await notifyResourceListChanged();
    }

    return {
      removed_ids: removedIds,
      remaining: catalog.size,
    };
  },
};

// Define available tools based on enabled datasources
server.setRequestHandler(ListToolsRequestSchema, async () => {
  // Consolidated tools: one per type + listing tool
  const tools = [
    {
      name: 'health_check',
      description: 'Check connection to Grafana and verify authentication',
      inputSchema: {
        type: 'object',
        properties: {},
      },
    },
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
      name: 'load_knowledge',
      description: 'Load required knowledge/documentation for a datasource before querying. Some datasources require you to read documentation or schema information before they can be queried. This tool fetches that knowledge from a URL or file path. IMPORTANT: You must call this tool for any datasource that has required_reading configured before you can query it.',
      inputSchema: {
        type: 'object',
        properties: {
          datasource_uid: { type: 'string', description: 'Datasource UID to load knowledge for' },
        },
        required: ['datasource_uid'],
      },
    },
    {
      name: 'loki_query',
      description: 'Query Loki logs with inline response (max 64KB). Use this for quick iteration and small result sets. If result exceeds 64KB, error message directs you to use loki_query_to_resource instead. Actions: query|labels|label_values. Time filtering is handled via start/end parameters - Loki queries do not need Grafana time macros.',
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
      name: 'loki_query_to_resource',
      description: 'Query Loki logs and persist result to disk. Returns result_id, resource_uri, and file_path. Use this for large datasets (>64KB) or when you need to filter with ?limit, ?offset, or ?jq parameters via resources/read. Time filtering is handled via start/end parameters - Loki queries do not need Grafana time macros.',
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
      name: 'prometheus_query',
      description: 'Query Prometheus metrics with inline response (max 64KB). Use this for quick iteration and small result sets. If result exceeds 64KB, error message directs you to use prometheus_query_to_resource instead. Modes: instant|range. IMPORTANT: You can use Grafana macros in your PromQL queries - $__interval (e.g., rate(metric[$__interval])), $__rate_interval (recommended for rate/increase), $__range, $__range_s, $__range_ms. These are automatically expanded by Grafana.',
      inputSchema: {
        type: 'object',
        properties: {
          mode: { type: 'string', enum: ['instant', 'range'], description: 'Query mode' },
          query: { type: 'string', description: 'PromQL query string. Can use Grafana macros: $__interval, $__rate_interval, $__range' },
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
      name: 'prometheus_query_to_resource',
      description: 'Query Prometheus metrics and persist result to disk. Returns result_id, resource_uri, and file_path. Use this for large datasets (>64KB) or when you need to filter with ?limit, ?offset, or ?jq parameters via resources/read. IMPORTANT: You can use Grafana macros in your PromQL queries - $__interval (e.g., rate(metric[$__interval])), $__rate_interval (recommended for rate/increase), $__range, $__range_s, $__range_ms. These are automatically expanded by Grafana.',
      inputSchema: {
        type: 'object',
        properties: {
          mode: { type: 'string', enum: ['instant', 'range'], description: 'Query mode' },
          query: { type: 'string', description: 'PromQL query string. Can use Grafana macros: $__interval, $__rate_interval, $__range' },
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
      name: 'clickhouse_query',
      description: 'Run SQL query against ClickHouse with inline response (max 64KB). Use this for quick iteration and small result sets. If result exceeds 64KB, error message directs you to use clickhouse_query_to_resource instead. IMPORTANT: You can use Grafana macros in your SQL - $__timeFilter(column) for WHERE clauses, $__fromTime/$__toTime for time bounds, $__interval_s for grouping intervals, $__timeInterval(column) for GROUP BY. These are automatically expanded by Grafana.',
      inputSchema: {
        type: 'object',
        properties: {
          sql: { type: 'string', description: 'SQL query to execute. Can use Grafana macros: $__timeFilter(column), $__fromTime, $__toTime, $__interval_s, $__timeInterval(column)' },
          from: { type: 'string', description: 'Time range start (e.g., "now-1h")' },
          to: { type: 'string', description: 'Time range end (e.g., "now")' },
          datasource_uid: { type: 'string', description: 'Datasource UID (required if multiple ClickHouse datasources)' },
        },
        required: ['sql'],
      },
    },
    {
      name: 'clickhouse_query_to_resource',
      description: 'Run SQL query against ClickHouse and persist result to disk. Returns result_id, resource_uri, and file_path. Use this for large datasets (>64KB) or when you need to filter with ?limit, ?offset, or ?jq parameters via resources/read. IMPORTANT: You can use Grafana macros in your SQL - $__timeFilter(column) for WHERE clauses, $__fromTime/$__toTime for time bounds, $__interval_s for grouping intervals, $__timeInterval(column) for GROUP BY. These are automatically expanded by Grafana.',
      inputSchema: {
        type: 'object',
        properties: {
          sql: { type: 'string', description: 'SQL query to execute. Can use Grafana macros: $__timeFilter(column), $__fromTime, $__toTime, $__interval_s, $__timeInterval(column)' },
          from: { type: 'string', description: 'Time range start (e.g., "now-1h")' },
          to: { type: 'string', description: 'Time range end (e.g., "now")' },
          datasource_uid: { type: 'string', description: 'Datasource UID (required if multiple ClickHouse datasources)' },
        },
        required: ['sql'],
      },
    },
    {
      name: 'describe_result',
      description: 'Return metadata for a stored result_id (includes resource_uri, sizes, summaries).',
      inputSchema: {
        type: 'object',
        properties: {
          result_id: { type: 'string', description: 'Identifier returned from a data tool response' },
        },
        required: ['result_id'],
      },
    },
    {
      name: 'delete_result',
      description: 'Remove a stored result and optionally delete its cached artifact.',
      inputSchema: {
        type: 'object',
        properties: {
          result_id: { type: 'string', description: 'Identifier returned from a data tool response' },
          delete_file: { type: 'boolean', description: 'Whether to remove the stored file (default: true)' },
        },
        required: ['result_id'],
      },
    },
    {
      name: 'trim_results',
      description: 'Prune saved results by age or quantity.',
      inputSchema: {
        type: 'object',
        properties: {
          max_age_hours: { type: 'number', description: 'Delete entries older than this many hours' },
          max_results: { type: 'integer', description: 'Keep at most this many newest entries' },
        },
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
    const errDetails = {
      message: error.message,
      status: error?.response?.status,
      statusText: error?.response?.statusText,
      data: error?.response?.data,
    };
    console.error(`Tool '${name}' error:`, errDetails);
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ error: errDetails }, null, 2),
        },
      ],
    };
  }
});

server.setRequestHandler(ListResourcesRequestSchema, async () => {
  await ensureStorage();
  await loadCatalogFromDisk();

  const resources = catalogEntriesSorted().map((entry) => {
    const metadata = entry.summary || {};
    return {
      uri: resultIdToUri(entry.id),
      name: `${entry.tool} result (${formatBytes(entry.size_bytes)})`,
      description: `${metadata.data_type || 'data'} from ${entry.tool}${metadata.row_count ? `, ${metadata.row_count} rows` : ''}${metadata.series_count ? `, ${metadata.series_count} series` : ''}${metadata.stream_count ? `, ${metadata.stream_count} streams` : ''}`,
      mimeType: 'application/json',
      _meta: {
        result_id: entry.id,
        tool: entry.tool,
        datasource_uid: entry.datasource_uid,
        created_at: entry.created_at,
        size_bytes: entry.size_bytes,
        ...metadata,
      },
    };
  });

  const resourceTemplates = [
    {
      uriTemplate: `${RESOURCE_URI_PREFIX}{id}{?limit,offset,jq}`,
      name: 'Filtered Query Result',
      description: 'Access query results with optional filtering. Supports: limit (max items), offset (skip items), jq (JQ expression for filtering)',
      mimeType: 'application/json',
    },
  ];

  return { resources, resourceTemplates };
});

server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  await ensureStorage();

  // Parse URI and query parameters
  const uri = new URL(request.params.uri, 'http://dummy');
  const pathParts = uri.pathname.split('/');
  const resultId = pathParts[pathParts.length - 1];

  if (!resultId || !catalog.has(resultId)) {
    throw new McpError(ErrorCode.InvalidParams, `Invalid resource URI: ${request.params.uri}`);
  }

  const entry = getCatalogEntryOrThrow(resultId);

  // Read the data
  const rawData = await fs.readFile(entry.file_path, 'utf8');
  let data = JSON.parse(rawData);

  // Extract query parameters
  const limit = uri.searchParams.get('limit') ? parseInt(uri.searchParams.get('limit')) : null;
  const offset = uri.searchParams.get('offset') ? parseInt(uri.searchParams.get('offset')) : null;
  const jqExpression = uri.searchParams.get('jq');

  // Apply JQ filtering first if specified
  if (jqExpression) {
    try {
      const jqResult = await jq.run(jqExpression, data, { input: 'json', output: 'json' });
      data = jqResult;
    } catch (error) {
      throw new McpError(
        ErrorCode.InvalidParams,
        `Invalid JQ expression: ${error.message}\n\nExample: ?jq=.data.result[]|select(.metric.job=="prometheus")`
      );
    }
  }

  // Apply pagination (limit/offset) to arrays
  if ((limit !== null || offset !== null) && Array.isArray(data)) {
    const start = offset || 0;
    const end = limit ? start + limit : undefined;
    data = data.slice(start, end);
  } else if ((limit !== null || offset !== null) && data?.data?.result && Array.isArray(data.data.result)) {
    // Special handling for Prometheus/Loki structure
    const start = offset || 0;
    const end = limit ? start + limit : undefined;
    data.data.result = data.data.result.slice(start, end);
  }

  // Serialize filtered data (compact format - no pretty-printing)
  const filteredData = JSON.stringify(data);
  const filteredSize = Buffer.byteLength(filteredData, 'utf8');

  // Check if filtered result still exceeds limits
  if (filteredSize > MAX_RESOURCE_BYTES) {
    throw new McpError(
      ErrorCode.InvalidParams,
      `Filtered result still too large (${formatBytes(filteredSize)}, max: ${formatBytes(MAX_RESOURCE_BYTES)}).\n\n` +
      `Try:\n` +
      `- Smaller limit: ?limit=100\n` +
      `- More specific JQ filter: ?jq=.data.result[0:10]\n` +
      `- Combination: ?limit=50&jq=.data.result[]|select(.metric.instance=="localhost")`
    );
  }

  return {
    contents: [
      {
        uri: request.params.uri,
        mimeType: 'application/json',
        text: filteredData,
        _meta: {
          result_id: entry.id,
          tool: entry.tool,
          original_size_bytes: entry.size_bytes,
          filtered_size_bytes: filteredSize,
          filters_applied: {
            limit,
            offset,
            jq: jqExpression,
          },
        },
      },
    ],
  };
});

async function main() {
  await ensureStorage();
  if (!GRAFANA_TOKEN) {
    console.error('Error: Grafana token not configured.');
    console.error('Set either:');
    console.error(' - GRAFANA_SERVICE_TOKEN=<token>');
    console.error(' - GRAFANA_SERVICE_TOKEN_ENV_VAR=<ENV_VAR_NAME> (where ENV_VAR_NAME contains the token)');
    process.exit(1);
  }
  // Discover datasources on startup
  enabledDatasources = await discoverDatasources();
  
  const transport = new StdioServerTransport();
  await server.connect(transport);
  if (catalog.size > 0) {
    await notifyResourceListChanged();
  }
  
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
