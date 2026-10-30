// SPDX-License-Identifier: BSD-2-Clause
// Run with the selected Node trial using --expose-gc.
'use strict';
const assert = require('node:assert/strict');
const vm = require('node:vm');
assert.equal(process.versions.node, '26.13.0');
let calls = [];
const ctx = vm.createContext({calls}, {microtaskMode: 'afterEvaluate'});
vm.runInContext('Promise.resolve().then(() => calls.push(42))', ctx);
assert.deepEqual(calls, [42]);
for (let i = 0; i < 10; ++i) { vm.runInNewContext('Promise.resolve().then(() => {})', {}, {microtaskMode:'afterEvaluate'}); global.gc(); }
const h = require('node:perf_hooks').createHistogram();
h.record(42); assert.equal(h.count, 1); assert.equal(h.min, 42);
assert.equal(Buffer.from('abc').toString(), 'abc');
console.log('Node common V8 vm, GC, histogram and buffer smoke PASS');

process.env.EMBER_NODE_SMOKE = 'ok'; assert.equal(process.env.EMBER_NODE_SMOKE,'ok'); delete process.env.EMBER_NODE_SMOKE; assert.equal(process.env.EMBER_NODE_SMOKE,undefined);
const {DatabaseSync} = require('node:sqlite'); const db = new DatabaseSync(':memory:'); db.exec('create table t(v integer); insert into t values (42)'); assert.equal(db.prepare('select v from t').get().v,42); db.close();
console.log('Node env and sqlite smoke PASS');

const inspector = require('node:inspector');
const post = (s,method,params) => new Promise(resolve => s.post(method,params,(error,result) => resolve({error,result})));
(async () => {
  const s = new inspector.Session(); s.connect();
  let r = await post(s,'Runtime.evaluate',{expression:'6 * 7'});
  assert.equal(r.error,null); assert.equal(r.result.result.value,42);
  r = await post(s,'UnknownDomain.unknownMethod',{});
  assert(r.error); assert.match(r.error.message,/wasn't found|not found/i);
  r = await post(s,'Runtime.evaluate',{expression: 42});
  assert(r.error); assert.match(r.error.message,/invalid|parameters/i);
  s.disconnect();
  const s2 = new inspector.Session(); s2.connect();
  r = await post(s2,'Runtime.evaluate',{expression:'21 * 2'});
  assert.equal(r.result.result.value,42); s2.disconnect();
  console.log('Inspector ordinary, unknown, invalid and teardown PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
