#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Run Node's actual GC/timeout test with a real peer reset and error controls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

PORTS = Path(__file__).resolve().parents[3]
PROFILE = PORTS / 'profiles/common-build-tools'
PATCH = PROFILE / 'patches/node-gc-net-timeout.patch'
TEST = Path('test/parallel/test-gc-net-timeout.js')
p = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'host-prefix', 'archive', 'work'):
    p.add_argument('--' + name, required=True, type=Path)
a = p.parse_args()
assert all(path.is_absolute() for path in (a.sdk_source, a.host_prefix, a.archive, a.work))
sys.path.insert(0, str(a.sdk_source / 'src'))
from emberbsd_sdk import sourceprep
from emberbsd_sdk.host_prefix import load_host_prefix
native = load_host_prefix(a.host_prefix, required_roles=('node', 'python', 'patch'))
assert Path(native.tool('python')).resolve() == Path(sys.executable).resolve()
assert not a.work.exists(), 'use a new work directory'
a.work.mkdir(parents=True)
env = dict(os.environ, PATH=native.path, LC_ALL='C', TMPDIR=str(a.work))
# Do not inherit optional Node preload/test instrumentation from the caller.
for key in tuple(env):
    if key.startswith(('NODE_', 'TEST_')):
        del env[key]
commands = []

def run(label, argv, *, cwd=a.work, success=True, timeout=30):
    command = list(map(str, argv))
    try:
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                                timeout=timeout)
        status, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as error:
        status, stdout, stderr = 'timeout', error.stdout or b'', error.stderr or b''
    (a.work / (label + '.stdout')).write_bytes(stdout)
    (a.work / (label + '.stderr')).write_bytes(stderr)
    commands.append(dict(label=label, argv=command, status=status))
    (a.work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    assert (status == 0) == success, (label, status, stderr.decode(errors='replace'))
    return status, stdout, stderr

version = run('version', [native.tool('node'), '--version'])[1].strip()
assert version == b'v26.12.1', version
sources = [line.split('\t') for line in (PROFILE / 'sources.tsv').read_text().splitlines()
           if line.startswith(a.archive.name + '\t')]
assert len(sources) == 1 and a.archive.name == 'node-v26.12.1.tar.xz'
assert hashlib.sha256(a.archive.read_bytes()).hexdigest() == sources[0][1]
entry = ('recipe-patch\t' + PATCH.relative_to(PORTS).as_posix() +
         '\tlang/nodejs\tpatch-test_parallel_test-gc-net-timeout.js\n')
assert (PORTS / 'pkgsrc/export.conf').read_text().count(entry) == 1
source = a.work / 'source'; source.mkdir()
sourceprep.extract_archive(a.archive, source, 'node-v26.12.1', 'Node GC test',
                          components=('test/common', TEST.as_posix()))
baseline = source / 'node-v26.12.1'
candidate = a.work / 'candidate'
shutil.copytree(baseline, candidate)
run('patch', [native.tool('patch'), '-f', '-F0', '-p0', '-V', 'none', '-i', PATCH],
    cwd=candidate)
# The carried patch only inserts the client error listener: all upstream GC,
# timeout, counters and termination conditions must remain byte-identical.
original = (baseline / TEST).read_text()
patched = (candidate / TEST).read_text()
start = patched.index("  req.on('error',")
end = patched.index('  req.resume();', start)
assert patched[:start] + patched[end:] == original

preload = a.work / 'inject.cjs'
preload.write_text(r"""'use strict';
const assert = require('node:assert');
const net = require('node:net');
const mode = process.env.EMBER_GC_ERROR;
const clients = new WeakSet();
const connect = net.connect;
const emit = net.Socket.prototype.emit;
let injected = false;
let observed = 0;
net.Socket.prototype.emit = function(event, error, ...rest) {
  if (event === 'error' && clients.has(this)) {
    if (error.code === 'ECONNRESET') {
      observed++;
      process.stderr.write('probe: client ECONNRESET\n');
    }
  }
  return emit.call(this, event, error, ...rest);
};
function error(code) { return Object.assign(new Error(code), { code }); }
net.connect = function(...args) {
  const socket = connect.apply(this, args);
  clients.add(socket);
  if (mode !== 'reset' && !injected) {
    injected = true;
    setImmediate(() => {
      let failure;
      if (mode === 'other') {
        failure = error('ECONNREFUSED');
      } else {
        const children = mode === 'empty' ? [] : [error('ECONNRESET'),
          error(mode === 'mixed' ? 'ECONNREFUSED' : 'ECONNRESET')];
        failure = new AggregateError(children);
        failure.code = mode === 'outer' ? 'ECONNREFUSED' : 'ECONNRESET';
      }
      socket.emit('error', failure);
    });
  }
  return socket;
};
if (mode === 'reset') {
  const serverEmit = net.Server.prototype.emit;
  net.Server.prototype.emit = function(event, socket, ...rest) {
    const result = serverEmit.call(this, event, socket, ...rest);
    if (event === 'connection' && !injected) {
      injected = true;
      socket.resetAndDestroy();
    }
    return result;
  };
}
process.on('exit', (code) => {
  if (code === 0) {
    assert(injected);
    assert(observed > 0);
  }
});
""")

def exercise(label, tree, mode=None, *, success=True, timeout=30):
    env.pop('EMBER_GC_ERROR', None)
    argv = [native.tool('node'), '--expose-gc']
    if mode:
        env['EMBER_GC_ERROR'] = mode
        argv += ['--require', preload]
    result = run(label, [*argv, tree / TEST], success=success, timeout=timeout)
    if success:
        progress = re.findall(rb'done/collected/total: (\d+)/(\d+)/(\d+)', result[1])
        assert progress, (label, 'missing original GC progress')
        done, collected, total = map(int, progress[-1])
        assert done > 0 and collected == total and total > 0, (label, progress[-1])
    return result

_, _, failure = exercise('baseline-reset', baseline, 'reset', success=False)
assert b"Unhandled 'error' event" in failure and b'ECONNRESET' in failure
assert b'probe: client ECONNRESET' in failure
exercise('candidate-reset', candidate, 'reset')
exercise('candidate-normal', candidate)
exercise('candidate-aggregate', candidate, 'aggregate')
for mode in ('other', 'mixed', 'outer', 'empty'):
    status, _, failure = exercise('reject-' + mode, candidate, mode, success=False)
    assert status != 'timeout' and b'AssertionError' in failure, (mode, failure)
# Ensure that swallowing socket errors did not make a missing collection pass.
lost_gc = a.work / 'lost-gc'
shutil.copytree(candidate, lost_gc)
assert patched.count('countGC++;') == 1
(lost_gc / TEST).write_text(patched.replace('countGC++;', '/* deliberately lose GC notification */'))
status, progress, _ = exercise('reject-lost-gc', lost_gc, 'reset', success=False, timeout=2)
assert status == 'timeout' and b'done/collected/total:' in progress
print('PASS: real peer reset fails upstream and passes candidate; normal/aggregate GC complete; '
      'unrelated/mixed/outer/empty errors and lost GC are rejected')
