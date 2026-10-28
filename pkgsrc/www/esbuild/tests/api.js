// SPDX-License-Identifier: MIT
// Origin: EmberBSD (AI-assisted), shared esbuild consumer regression.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync, spawnSync } = require('node:child_process');
const os = require('node:os');
const root = process.argv[2];
const esbuild = require(path.join(root, 'lib/node_modules/esbuild'));
assert.equal(esbuild.version, '0.28.2');
const metadata = require(path.join(root, 'lib/node_modules/esbuild/package.json'));
assert.equal(metadata.scripts, undefined);
assert.equal(metadata.optionalDependencies, undefined);
assert.equal(execFileSync(path.join(root, 'bin/esbuild'), ['--version'], { encoding: 'utf8' }).trim(), esbuild.version);
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'esbuild-shared-'));
try {
  const modulePath = path.join(temp, 'lib/node_modules/esbuild');
  fs.cpSync(path.join(root, 'lib/node_modules/esbuild'), modulePath, { recursive: true });
  const cmd = ['-e', 'require(process.argv[1]).transformSync("1")', modulePath];
  const explicit = spawnSync(process.execPath, cmd, { encoding: 'utf8', env: { ...process.env, ESBUILD_BINARY_PATH: path.join(root, 'bin/esbuild') } });
  assert.equal(explicit.status, 0, explicit.stderr);
  const probe = spawnSync(process.execPath, cmd, { encoding: 'utf8', env: { ...process.env, ESBUILD_BINARY_PATH: '' } });
  assert.notEqual(probe.status, 0);
  assert.match(probe.stderr, /Shared esbuild executable is missing/);
} finally { fs.rmSync(temp, { recursive: true, force: true }); }
const result = esbuild.transformSync('const n: number = 5; console.log(n)', { loader: 'ts', minify: true });
assert.match(result.code, /console\.log\(5\)/);
(async () => {
  const build = await esbuild.build({ stdin: { contents: 'export const n: number = 5', loader: 'ts' }, write: false, bundle: true, format: 'esm' });
  assert.match(build.outputFiles[0].text, /n = 5/);
  assert.equal(fs.realpathSync(path.join(root, 'lib/node_modules/esbuild/bin/esbuild')), fs.realpathSync(path.join(root, 'bin/esbuild')));
  console.log('shared esbuild executable, JS sync/async APIs PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
