// Pure utilities, no external deps

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
        s: value * 1000,
        m: value * 60 * 1000,
        h: value * 60 * 60 * 1000,
        d: value * 24 * 60 * 60 * 1000,
      }[unit];
      return (Date.now() - ms) * 1000000;
    }
  }
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

function normalizeType(dsType) {
  if (!dsType) return 'unknown';
  if (dsType === 'loki') return 'loki';
  if (dsType === 'prometheus') return 'prometheus';
  if (dsType === 'clickhouse' || dsType === 'grafana-clickhouse-datasource' || dsType === 'vertamedia-clickhouse-datasource') return 'clickhouse';
  return dsType;
}

function requireUidForType(typeNorm, provided, dsMap = {}) {
  if (provided) return provided;
  const candidates = Object.values(dsMap).filter((ds) => ds.typeNormalized === typeNorm);
  if (candidates.length === 0) throw new Error(`No ${typeNorm} datasource available`);
  if (candidates.length > 1) throw new Error(`Multiple ${typeNorm} datasources available; specify datasource_uid`);
  return candidates[0].uid;
}

export { parseTime, parseDurationToSeconds, normalizeType, requireUidForType };

