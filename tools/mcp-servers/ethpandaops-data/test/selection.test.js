import test from 'node:test';
import assert from 'node:assert/strict';
import { requireUidForType } from '../utils.js';

test('requireUidForType with none available throws', () => {
  assert.throws(() => requireUidForType('loki', undefined, {}), /No loki datasource available/);
});

test('requireUidForType with multiple available throws', () => {
  const dsMap = {
    a: { uid: 'a', typeNormalized: 'loki' },
    b: { uid: 'b', typeNormalized: 'loki' },
  };
  assert.throws(() => requireUidForType('loki', undefined, dsMap), /Multiple loki datasources available/);
});

test('requireUidForType returns provided uid when given', () => {
  const dsMap = {};
  assert.equal(requireUidForType('prometheus', 'x', dsMap), 'x');
});

test('requireUidForType selects only available uid', () => {
  const dsMap = {
    prom: { uid: 'prom', typeNormalized: 'prometheus' },
  };
  assert.equal(requireUidForType('prometheus', undefined, dsMap), 'prom');
});
