// SPDX-License-Identifier: BSD-2-Clause
// EmberBSD Ports regression, developed with AI assistance.
const assert = require('node:assert/strict');
const path = require('node:path');
const {appFilePath, isAllowedExternalURL} = require(process.argv[2] || path.join(__dirname, '../files/app-paths.cjs'));
const root = '/tmp/dist';
for (const [url,expected] of [
  ['bfapp://./', '/tmp/dist/index.html'],
  ['bfapp://./assets/main.js', '/tmp/dist/assets/main.js'],
  ['bfapp://./..%2fdist-evil/secret', null],
  ['bfapp://./%zz', null], ['bfapp://./%00', null],
  ['bfapp://evil/index.html', null],
]) assert.equal(appFilePath(root,url),expected,url);
for (const url of ['javascript:alert(1)','file:///tmp/x','mailto:test@example.com']) assert.equal(isAllowedExternalURL(url),false,url);
for (const url of ['https://example.com/','http://example.com/']) assert.equal(isAllowedExternalURL(url),true,url);
console.log('PASS app path and external URL policy');
