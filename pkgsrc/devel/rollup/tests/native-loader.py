#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Run the actual npm native loader with observed platform/addon fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

SCRIPT=r'''
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const sources = JSON.parse(fs.readFileSync(0, 'utf8'));
let count = 0;
function load(source, platform, arch, {local=true, failure, musl=false}={}) {
  const requested = [];
  const parse = () => {};
  const failureObject = Object.assign(new Error('fixture addon failure'), {code: failure});
  const module = {exports: {}};
  const context = {module, __dirname: '/fixture/dist', Error,
    require(id) {
      if (id === 'node:fs') return {existsSync: () => local};
      if (id === 'node:path') return path;
      if (id === 'node:process') return {platform, arch, report: {
        getReport: () => ({header: {osName:'fixture', glibcVersionRuntime: musl ? undefined : '2.40'}})
      }};
      if (id === 'node:child_process') return {spawnSync: () => { throw new Error('fixture must not spawn'); }};
      requested.push(id);
      if (failure) throw failureObject;
      return {parse};
    }
  };
  let error;
  try {vm.runInNewContext(source,context,{timeout:1000});} catch (value) {error=value;}
  return {requested, error, failureObject, exports:module.exports, parse};
}
for (const arch of ['arm64','x64']) {
  const base='netbsd-'+arch;
  const original=load(sources.baseline,'netbsd',arch);
  assert.match(original.error.message,/not yet supported/);
  assert.deepEqual(original.requested,[]); ++count;
  const selected=load(sources.patched,'netbsd',arch);
  assert.equal(selected.error,undefined);
  assert.deepEqual(selected.requested,['./rollup.'+base+'.node']);
  assert.equal(selected.exports.parse,selected.parse); ++count;
  const corrupt=load(sources.patched,'netbsd',arch,{failure:'ERR_DLOPEN_FAILED'});
  assert.equal(corrupt.error,corrupt.failureObject);
  assert.deepEqual(corrupt.requested,['./rollup.'+base+'.node']); ++count;
  const absent=load(sources.patched,'netbsd',arch,{local:false,failure:'MODULE_NOT_FOUND'});
  assert.match(absent.error.message,/Cannot find module/);
  assert.equal(absent.error.cause,absent.failureObject);
  assert.deepEqual(absent.requested,['@rollup/rollup-'+base]); ++count;
}
for (const [platform,arch,base,musl] of [
  ['darwin','arm64','darwin-arm64'],['darwin','x64','darwin-x64'],
  ['freebsd','arm64','freebsd-arm64'],['freebsd','x64','freebsd-x64'],
  ['openbsd','x64','openbsd-x64'],['linux','x64','linux-x64-gnu'],
  ['linux','x64','linux-x64-musl',true]
]) {
  for (const source of Object.values(sources)) {
    const result=load(source,platform,arch,{musl});
    assert.equal(result.error,undefined);
    assert.deepEqual(result.requested,['./rollup.'+base+'.node']);
  }
  ++count;
}
console.log(JSON.stringify({cases:count, scope:'actual loader with platform/addon fixtures; no target native execution'}));
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('node','source','archive'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if not all(path.is_absolute() for path in vars(args).values()):parser.error('select absolute paths')
    if not os.access(args.node,os.X_OK):parser.error('select executable native Node')
    recipe=Path(__file__).resolve().parents[1]
    pattern=r'^SHA512 \('+re.escape(args.archive.name)+r'\) = ([0-9a-f]+)$'
    matches=re.findall(pattern,(recipe/'distinfo').read_text(),re.M)
    assert len(matches)==1 and hashlib.sha512(args.archive.read_bytes()).hexdigest()==matches[0]
    with tarfile.open(args.archive) as archive:baseline=archive.extractfile('package/dist/native.js').read().decode()
    result=subprocess.run([str(args.node),'-e',SCRIPT],input=json.dumps(dict(baseline=baseline,patched=args.source.read_text())),capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    print(result.stdout.strip())


if __name__=='__main__':main()
