// SPDX-License-Identifier: MIT
// Origin: EmberBSD (AI-assisted).
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const loader = path.resolve(process.argv[2]);
const target = path.join(path.dirname(loader), 'index-fetch.js');
const flag = '__UNDICI_IS_NODE__';
const clear = () => { delete require.cache[loader]; delete require.cache[target]; };
const descriptor = () => Object.getOwnPropertyDescriptor(globalThis, flag);
const original = descriptor();
try {
  delete globalThis[flag];
  clear(); assert.equal(require(loader), true); assert.equal(descriptor(), undefined);
  Object.defineProperty(globalThis, flag, {value: 'prior', writable: true, enumerable: false, configurable: true});
  let before = descriptor();
  clear(); assert.equal(require(loader), true); assert.deepEqual(descriptor(), before);
  globalThis.__UNDICI_TEST_THROW__ = true;
  clear(); assert.throws(() => require(loader), /intentional test failure/);
  assert.deepEqual(descriptor(), before);
  delete globalThis[flag];
  clear(); assert.throws(() => require(loader), /intentional test failure/);
  assert.equal(descriptor(), undefined);
  console.log('Undici loader global restoration on success and failure PASS');
} finally {
  delete globalThis.__UNDICI_TEST_THROW__;
  if (original) Object.defineProperty(globalThis, flag, original);
  else delete globalThis[flag];
}
