// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
'use strict';

// Run with the selected Node: --expose-internals <this file>. The permission
// subprocess tests that denied paths never reach either JS override.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { Worker } = require('node:worker_threads');
const { pathToFileURL } = require('node:url');
const { internalBinding } = require('internal/test/binding');
const modules = internalBinding('modules');
const nativeFs = internalBinding('fs');

if (process.argv[2] === '--permission-child') {
  let calls = 0;
  modules.overrideReadFileSync(() => { calls++; return Buffer.from('{}'); });
  assert.throws(() => modules.readPackageJSON('/denied-hook/package.json', false),
                { code: 'ERR_ACCESS_DENIED' });
  assert.equal(calls, 0);
  assert.throws(() => nativeFs.legacyMainResolve('/denied-hook', 'index.js', undefined,
    () => { calls++; return true; }), { code: 'ERR_ACCESS_DENIED' });
  assert.equal(calls, 0);
  process.exit(0);
}

(async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'node-asar-hook-'));
  try {
    const names = (name) => path.join(root, name, 'package.json');
    fs.mkdirSync(path.join(root, 'fallback'));
    fs.writeFileSync(names('fallback'), '{"name":"native"}');
    modules.overrideReadFileSync(() => undefined);
    assert.equal(modules.readPackageJSON(names('fallback'), false)[0], 'native');

    modules.overrideReadFileSync(() => false);
    assert.equal(modules.readPackageJSON(names('missing'), false), undefined);
    modules.overrideReadFileSync(() => Buffer.from('{"name":"virtual"}'));
    // Existing negative entries remain cached across hook replacement.
    assert.equal(modules.readPackageJSON(names('missing'), false), undefined);
    assert.equal(modules.readPackageJSON(names('virtual'), false)[0], 'virtual');
    for (const [index, value] of [42, true, null, "{}", new Float32Array([1])].entries()) {
      modules.overrideReadFileSync(() => value);
      assert.throws(() => modules.readPackageJSON(names(`invalid-${index}`), false), TypeError);
    }
    modules.overrideReadFileSync(() => new Uint8Array(Buffer.from('{"name":"bytes"}')));
    assert.equal(modules.readPackageJSON(names('bytes'), false)[0], 'bytes');
    const vm = require('node:vm');
    const foreignBuffer = vm.runInNewContext(`const b = Buffer.from('{"name":"foreign"}'); Object.setPrototypeOf(b, Object.create(Buffer.prototype)); b`, { Buffer });
    modules.overrideReadFileSync(() => foreignBuffer);
    assert.equal(modules.readPackageJSON(names('foreign'), false)[0], 'foreign');
    const failure = new Error('virtual read failure');
    modules.overrideReadFileSync(() => { throw failure; });
    assert.throws(() => modules.readPackageJSON(names('failure'), false), e => e === failure);
    assert.throws(() => modules.getNearestParentPackageJSON(path.join(root, 'nearest', 'file.js')),
                  e => e === failure);
    assert.throws(() => modules.getPackageScopeConfig(pathToFileURL(path.join(root, 'scope', 'file.js')).href),
                  e => e === failure);
    modules.overrideReadFileSync(() => Buffer.from('{"name":"parent"}'));
    const shared = names('realm');
    assert.equal(modules.readPackageJSON(shared, false)[0], 'parent');
    const worker = new Worker(`
      const { parentPort, workerData } = require('node:worker_threads');
      const { internalBinding } = require('internal/test/binding');
      const modules = internalBinding('modules');
      modules.overrideReadFileSync(() => Buffer.from('{"name":"worker"}'));
      parentPort.postMessage(modules.readPackageJSON(workerData, false)[0]);
    `, { eval: true, workerData: shared });
    assert.equal(await new Promise((resolve, reject) => {
      worker.once('message', resolve); worker.once('error', reject);
      worker.once('exit', code => { if (code) reject(new Error(`worker exit ${code}`)); });
    }), 'worker');
    assert.equal(modules.readPackageJSON(shared, false)[0], 'parent');

    const packageDir = path.join(root, 'real');
    fs.mkdirSync(packageDir); fs.writeFileSync(path.join(packageDir, 'index.js'), '');
    assert.equal(nativeFs.legacyMainResolve(packageDir, 'index.js', undefined), 0);
    let called = 0;
    assert.equal(nativeFs.legacyMainResolve(packageDir, 'virtual', undefined,
      candidate => { called++; return candidate.endsWith('virtual.js'); }), 1);
    assert.equal(called, 2);
    const statFailure = new Error('stat callback failure');
    assert.throws(() => nativeFs.legacyMainResolve(packageDir, 'virtual', undefined,
      () => { throw statFailure; }), e => e === statFailure);
    assert.throws(() => nativeFs.legacyMainResolve(packageDir, 'virtual', undefined, 7), TypeError);

    const child = spawnSync(process.execPath, ['--expose-internals', '--permission',
      `--allow-fs-read=${__filename}`, __filename, '--permission-child'], { encoding: 'utf8' });
    assert.equal(child.status, 0, child.stderr || child.stdout);
    modules.overrideReadFileSync();
    console.log('ASAR package hooks, cache, exceptions, permissions and realms: PASS');
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
