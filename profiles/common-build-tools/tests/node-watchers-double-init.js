// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
'use strict';

// Exercise the exact selected Node watcher guard twice and with an existing
// owner property, as happens when a second built-in fs namespace is loaded.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const sourcePath = process.argv[2];
assert(sourcePath && require('node:path').isAbsolute(sourcePath));
const source = fs.readFileSync(sourcePath, 'utf8');
const start = source.indexOf("if (!('owner' in FSEvent.prototype)) {");
const end = source.indexOf('\n\nlet kResistStopPropagation;', start);
assert(start >= 0 && end > start);
const guard = source.slice(start, end);
const owner_symbol = Symbol('owner');
class FSEvent {}
const context = { FSEvent, owner_symbol, ObjectDefineProperty: Object.defineProperty };
vm.runInNewContext(guard, context);
vm.runInNewContext(guard, context);
const event = new FSEvent();
event.owner = 42;
assert.equal(event.owner, 42);
class Existing {}
Object.defineProperty(Existing.prototype, 'owner', { value: 123 });
vm.runInNewContext(guard, { ...context, FSEvent: Existing });
assert.equal(new Existing().owner, 123);
console.log('Node watcher owner first, repeated and preexisting: PASS');

// Run with --expose-internals: load the real Node builtin once, then exercise
// the selected source guard against the actual shared FSEvent prototype.
const ActualFSEvent = process.binding('fs_event_wrap').FSEvent;
const actualOwner = require('internal/async_hooks').symbols.owner_symbol;
require('internal/fs/watchers');
const original = Object.getOwnPropertyDescriptor(ActualFSEvent.prototype, 'owner');
assert(original && original.get && original.set);
vm.runInNewContext(guard, {
  FSEvent: ActualFSEvent,
  owner_symbol: actualOwner,
  ObjectDefineProperty: Object.defineProperty,
});
assert.deepEqual(Object.getOwnPropertyDescriptor(ActualFSEvent.prototype, 'owner'), original);
console.log('Actual Node watcher loaded; second guard preserves FSEvent owner: PASS');
