import test from 'node:test';
import assert from 'node:assert/strict';
import { parseTime, parseDurationToSeconds, normalizeType } from '../utils.js';

test('parseTime handles now', () => {
  const ns = parseTime('now');
  const nowNs = Date.now() * 1e6;
  assert.ok(Math.abs(ns - nowNs) < 5e9, 'now within ~5s');
});

test('parseTime handles now-1h', () => {
  const ns = parseTime('now-1h');
  const expected = (Date.now() - 3600 * 1000) * 1e6;
  assert.ok(Math.abs(ns - expected) < 5e9, 'now-1h within ~5s');
});

test('parseTime handles RFC3339', () => {
  const ns = parseTime('2024-01-01T00:00:00Z');
  const expected = new Date('2024-01-01T00:00:00Z').getTime() * 1e6;
  assert.equal(ns, expected);
});

test('parseDurationToSeconds parses common units', () => {
  assert.equal(parseDurationToSeconds('30s'), 30);
  assert.equal(parseDurationToSeconds('5m'), 300);
  assert.equal(parseDurationToSeconds('2h'), 7200);
  assert.equal(parseDurationToSeconds('1d'), 86400);
  assert.equal(parseDurationToSeconds(60), 60);
  assert.equal(parseDurationToSeconds('60'), 60);
});

test('normalizeType maps clickhouse variants', () => {
  assert.equal(normalizeType('grafana-clickhouse-datasource'), 'clickhouse');
  assert.equal(normalizeType('vertamedia-clickhouse-datasource'), 'clickhouse');
  assert.equal(normalizeType('clickhouse'), 'clickhouse');
  assert.equal(normalizeType('prometheus'), 'prometheus');
  assert.equal(normalizeType('loki'), 'loki');
});
