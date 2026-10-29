// SPDX-License-Identifier: BSD-2-Clause
'use strict';
const assert = require('node:assert/strict');
const [matching, mismatching, napi] = process.argv.slice(2);
assert.ok(matching && mismatching && napi, 'expected matching, mismatching and Node-API addons');
assert.equal(process.versions.modules, '1162674177');
assert.doesNotThrow(() => require(matching));
assert.throws(() => require(mismatching), /NODE_MODULE_VERSION/);
assert.doesNotThrow(() => require(napi));
console.log('matching addon, mismatched addon rejection and Node-API: PASS');
