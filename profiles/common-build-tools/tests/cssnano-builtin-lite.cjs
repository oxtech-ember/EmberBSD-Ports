// Verify that an explicit consumer selects cssnano's own lite preset even
// when a conflicting package is visible from the provider's module path.
// Run: node cssnano-builtin-lite.cjs <installed-node_modules> <css-file>...
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawnSync } = require('node:child_process');
const [modules, ...inputs] = process.argv.slice(2);
if (!modules || !inputs.length) throw new Error('expected module directory and CSS inputs');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'cssnano-lite-'));
try {
  const nodeModules = path.join(temp, 'node_modules');
  fs.mkdirSync(nodeModules);
  for (const entry of fs.readdirSync(modules)) {
    if (entry !== 'cssnano' && entry !== 'cssnano-preset-lite')
      fs.symlinkSync(path.resolve(modules, entry), path.join(nodeModules, entry));
  }
  // Copy only the provider under test so the hostile package is its neighbour;
  // installed dependencies stay selected by the supplied module directory.
  fs.cpSync(path.join(modules, 'cssnano'), path.join(nodeModules, 'cssnano'), { recursive: true });
  const hostile = path.join(nodeModules, 'cssnano-preset-lite');
  fs.mkdirSync(hostile);
  fs.writeFileSync(path.join(hostile, 'package.json'), '{"name":"cssnano-preset-lite","main":"index.js"}');
  fs.writeFileSync(path.join(hostile, 'index.js'), 'throw new Error("unexpected external preset");');
  const runner = path.join(temp, 'verify.mjs');
  fs.writeFileSync(runner, `import cssnano from 'cssnano';
import lite from 'cssnano/preset-lite';
import postcss from 'postcss';
import fs from 'node:fs';
let rejected = false;
try { cssnano({preset: 'lite'}); } catch (e) { rejected = /unexpected external preset/.test(String(e)); }
if (!rejected) throw Error('fixture did not resolve hostile preset');
for (const file of process.argv.slice(2)) {
 const css = fs.readFileSync(file, 'utf8');
 const explicit = (await postcss([cssnano({preset: lite})]).process(css, {from: file})).css;
 const builtin = (await postcss([cssnano({preset: lite()})]).process(css, {from: file})).css;
 if (explicit !== builtin) throw Error('different preset output: ' + file);
}
`);
  const result = spawnSync(process.execPath, [runner, ...inputs], { encoding: 'utf8' });
  if (result.status !== 0) throw Error(result.stderr || result.stdout);
  console.log(`CSSNano explicit builtin lite: ${inputs.length} inputs passed with hostile external preset`);
} finally { fs.rmSync(temp, { recursive: true, force: true }); }
