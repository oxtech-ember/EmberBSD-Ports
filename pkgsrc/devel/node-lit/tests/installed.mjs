// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
// Run with the selected Node and an explicit installed lib/node_modules path.
import assert from 'node:assert/strict';
import {isAbsolute, join} from 'node:path';
import {pathToFileURL} from 'node:url';

const root = process.argv[2];
assert.ok(root && isAbsolute(root), 'select an absolute node_modules directory');
const load = path => import(pathToFileURL(join(root, path)).href);
const lit = await load('lit/index.js');
const repeat = await load('lit-html/node/directives/repeat.js');
const element = await load('lit-element/lit-element.js');
assert.equal(typeof lit.html, 'function');
assert.equal(typeof lit.LitElement, 'function');
assert.equal(typeof repeat.repeat, 'function');
assert.equal(element.LitElement, lit.LitElement);
assert.deepEqual(lit.html`Hello ${42}`.values, [42]);
console.log('PASS: common Lit ESM resolution and template API');
