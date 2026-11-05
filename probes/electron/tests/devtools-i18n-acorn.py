#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Run the patched DevTools collector with the selected common Acorn."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'node', 'modules', 'patch'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
owner = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='devtools-i18n-') as temp:
    root = Path(temp)
    frontend = root / 'third_party/devtools-frontend/src'
    files = ('third_party/i18n/collect-strings.js', 'third_party/i18n/bake-ctc-to-lhl.js',
             'scripts/build/ninja/write-if-changed.js', 'package.json')
    source = a.source / 'third_party/devtools-frontend/src'
    for name in files:
        dest = frontend / name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, dest)
    (frontend / 'node_modules').symlink_to(a.modules.resolve(strict=True), target_is_directory=True)
    subprocess.run([str(a.patch), '-p1', '-F0', '-i', str(owner/'patches/devtools-i18n-common-acorn.patch')], cwd=root, check=True)
    script = frontend/'fixture.mjs'
    script.write_text('''import assert from 'node:assert/strict';
import fs from 'node:fs';
import {parseUIStrings, convertMessageToCtc} from './third_party/i18n/collect-strings.js';
const data = parseUIStrings(`const UIStrings = {
/** @description Find the value\n * @meaning Search label\n * @example {Joe} name\n */
label: 'Hello ' + '{name}',
/** Simple description */ second: 'two',
}`);
assert.deepEqual(data.label, {message:'Hello {name}', description:'Find the value', meaning:'Search label', examples:{name:'Joe'}});
assert.deepEqual(data.second, {message:'two', description:'Simple description', meaning:undefined, examples:{}});
const edge = parseUIStrings("const UIStrings = {/** Unicode, comma */ a: `Привет, мир`,\\n/** a comma, in comment */ // intervening comment\\n b: 'x,y' + '!'}");
assert.equal(edge.a.message, 'Привет, мир');
assert.equal(edge.b.message, 'x,y!');
assert.equal(edge.b.description, 'a comma, in comment');
assert.equal(convertMessageToCtc(data.label.message, data.label.examples).placeholders.ICU_0.example, 'Joe');
for (const bad of [
 `const UIStrings = {/** first */ a:'a', b:'b'}`,
 `const UIStrings = {/** x */ a:other}`,
 `const UIStrings = {/** x */ [name]:'a'}`,
 `const UIStrings = {/** @unknown x */ a:'a'}`,
 `const UIStrings = {/** x */ a: fn()}`,
 `const UIStrings = {/** x */ ...other}`,
 `const UIStrings = {/** x */ a:'a' - 'b'}`,
 `const UIStrings = {/** x */ a() {}}`,
 `const UIStrings = {/** first */ a:'a', /** trailing */\n b:'b'}`,
 `const UIStrings = {/** x */ a:` + "`" + 'hi ${name}' + "`" + `}`,
 `const UIStrings = {/** x */ a:'a'`,
]) assert.throws(() => parseUIStrings(bad));
const input = fs.readFileSync(process.argv[2], 'utf8');
const match = input.match(/(UIStrings = .*?\\}) as const;\\n/s);
assert.ok(match);
const real = parseUIStrings('const ' + match[1]);
assert.equal(real.findByStringSelectorOrXpath.message, 'Find by string, selector, or `XPath`');
assert.equal(real.findByStringSelectorOrXpath.description,
 'Placeholder text for the search box in the Elements panel. Selector refers to CSS selectors.');
let count = 0;
function walk(dir) {
  for (const entry of fs.readdirSync(dir, {withFileTypes:true})) {
    const file = dir + '/' + entry.name;
    if (entry.isDirectory()) {
      if (!['.git', 'node_modules', 'third_party'].includes(entry.name) && !entry.name.endsWith('_test_runner')) walk(file);
    }
    else if (/\\.(js|ts)$/.test(entry.name) && !/\\.(test|test\\.api|docs)\\.ts$/.test(entry.name)) {
      const content = fs.readFileSync(file, 'utf8');
      const match = content.match(/(UIStrings = .*?\\}) as const;\\n/s);
      if (match) {
        try { parseUIStrings('const ' + match[1] + ';'); }
        catch (error) { throw new Error(file + ': ' + error.message, {cause:error}); }
        count++;
      }
    }
  }
}
walk(process.argv[3]);
console.log(`PASS: fixtures and ${count} actual DevTools UIStrings declarations`);
''')
    panel = source/'front_end/panels/elements/ElementsPanel.ts'
    subprocess.run([str(a.node), str(script), str(panel), str(source/'front_end')], cwd=frontend, check=True)
