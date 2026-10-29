const assert = require('node:assert/strict');
const { code } = require('ts-poet');
const output = code`export const answer={value:42}`.toString();
assert.match(output, /answer = \{ value: 42 \};/);
console.log('ts-poet default formatting PASS');
