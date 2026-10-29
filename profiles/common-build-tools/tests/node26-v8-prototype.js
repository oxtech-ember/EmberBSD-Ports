// SPDX-License-Identifier: BSD-2-Clause
'use strict';
const assert = require('node:assert/strict');
const set = require(process.argv[2]);
const obj = {}, proto = {}; assert.equal(set(obj, proto), 0); assert.equal(Object.getPrototypeOf(obj), proto);
assert.equal(set(obj, null), 0); assert.equal(Object.getPrototypeOf(obj), null);
const invalid = {}; const prior = Object.getPrototypeOf(invalid); assert.equal(set(invalid, 1), 0); assert.equal(Object.getPrototypeOf(invalid), prior);
let called = 0; const proxy = new Proxy({}, { setPrototypeOf(t, p) { ++called; return Reflect.setPrototypeOf(t,p); } });
assert.notEqual(set(proxy, 1), 0); assert.equal(called, 0);
assert.equal(set(proxy, proto), 0); assert.equal(called,1); assert.equal(Object.getPrototypeOf(proxy),proto);
console.log('N-API prototype object/null/invalid/proxy PASS');
