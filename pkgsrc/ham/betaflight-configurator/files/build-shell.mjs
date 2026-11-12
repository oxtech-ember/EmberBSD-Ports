// SPDX-License-Identifier: BSD-2-Clause
// EmberBSD Ports build helper, developed with AI assistance.
import { mkdir, mkdtemp, rm, rename, copyFile, readdir, readFile, lstat } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';

const names = ['main.cjs', 'serial.cjs', 'app-paths.cjs'];
const args = process.argv.slice(2);
if (args.length !== 8 || args[0] !== '--asar-module' || args[2] !== '--input' ||
    args[4] !== '--files' || args[6] !== '--work') {
  throw new Error('usage: build-shell.mjs --asar-module /absolute/asar.js --input /absolute/source.asar --files /absolute/files --work /absolute/work');
}
const [, modulePath, , input, , files, , workArg] = args;
for (const p of [modulePath, input, files, workArg]) {
  if (!p.startsWith('/')) throw new Error('all paths must be absolute');
}
const work = resolve(workArg), output = join(work, 'app.asar');
const asar = await import(pathToFileURL(modulePath).href);
await mkdir(work, { recursive: true });
const stage = await mkdtemp(join(work, '.asar-stage-'));
const app = join(stage, 'app'), original = join(stage, 'original'),
  verified = join(stage, 'verified'), candidate = join(stage, 'app.asar');
try {
await mkdir(app); await mkdir(original); await mkdir(verified);
asar.extractAll(input, original);
asar.extractAll(input, app);
for (const name of names) await copyFile(join(files, name), join(app, name));
await asar.createPackage(app, candidate);
asar.extractAll(candidate, verified);
async function compare(a, b, relative = '', excluded = new Set()) {
  const left = (await readdir(a)).filter(n => !(relative === '' && excluded.has(n))).sort();
  const right = (await readdir(b)).filter(n => !(relative === '' && excluded.has(n))).sort();
  assert.deepEqual(right, left, `entry mismatch: ${relative}`);
  for (const n of left) {
    const x = join(a,n), y = join(b,n), rel = join(relative,n);
    const xs = await lstat(x), ys = await lstat(y);
    assert.equal(xs.isDirectory(), ys.isDirectory(), `type mismatch: ${rel}`);
    assert.equal(xs.isFile(), ys.isFile(), `type mismatch: ${rel}`);
    if (xs.isDirectory()) await compare(x,y,rel);
    else { assert(xs.isFile(), `unsupported entry: ${rel}`); assert.deepEqual(await readFile(y),await readFile(x), `content mismatch: ${rel}`); }
  }
}
await compare(original, verified, '', new Set(names));
for (const name of names) assert.deepEqual(await readFile(join(verified,name)), await readFile(join(files,name)), `shell mismatch: ${name}`);
await rename(candidate, output);
console.log(output);
} finally {
  await rm(stage, { recursive: true, force: true });
}
