const test = require('node:test');
const assert = require('node:assert');
const { byDay } = require('../src/filter.js');
test('keeps earlier rows', () => assert.equal(byDay([{ date: '2026-01-01' }], '2026-01-02').length, 1));
