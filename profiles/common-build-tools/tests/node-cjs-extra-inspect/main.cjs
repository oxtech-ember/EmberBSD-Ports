'use strict';
const assert = require('node:assert/strict');
assert.equal(process, require('node:process'));
assert.equal(global, globalThis);
assert.equal(Buffer, require('node:buffer').Buffer);
assert.equal(arguments.length, 5);
console.log('inspect-brk CJS embedder args PASS');
