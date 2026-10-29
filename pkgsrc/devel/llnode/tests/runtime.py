#!/usr/bin/env python3
"""Exercise schema 2 on a debug-capable Node and an installed LLDB plugin.

Usage: runtime.py /path/to/lldb /path/to/node /path/to/llnode-plugin
The caller supplies the runtime library environment appropriate for Node.
"""
import os
import pathlib
import subprocess
import sys

here = pathlib.Path(__file__).resolve().parent
if len(sys.argv) != 4:
    raise SystemExit(__doc__)
lldb, node, plugin = sys.argv[1:]

def run(fixture, arguments, commands):
    setup = [f'plugin load {plugin}', 'settings set target.disable-aslr false',
             f'target create {node}',
             'settings set -- target.run-args ' + arguments + ' ' + str(here / fixture),
             'breakpoint set --name uv_kill', 'run']
    library_path = os.environ.get('LLNODE_TARGET_LIBRARY_PATH')
    if library_path:
        setup.insert(3, 'settings set target.env-vars DYLD_LIBRARY_PATH=' + library_path)
    argv = [lldb, '-b']
    for command in setup + commands + ['process kill', 'quit']:
        argv.extend(['-o', command])
    proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, timeout=180)
    if proc.returncode:
        raise RuntimeError(proc.stdout)
    return proc.stdout

frames = run('frames.js', '', ['v8 bt'])
for expected in ['stop(', 'inferredArrow(', 'namedFrame(', '(anonymous)']:
    assert expected in frames, expected
spill = run('spill.js', '--allow-natives-syntax',
            [f'command script import {here / "spill_inspect.py"}', 'ember-spill-check'])
for expected in ['PropertyArray[', '#outNumber: 9876', '#outString:',
                 'field 4, ooo', 'field 5, ooo', '.outNumber=<Smi: 9876>',
                 '<String: "actual-spill">', '<JSDate: 1700000000123.000000>',
                 '<Array: length=3', '<String: "array-value">', '[1]=<Smi: 77>',
                 '<String: "third">']:
    assert expected in spill, expected
for field, value, reason in [
    ('FirstJSFunctionType', '-1', 'V8 schema 2 layout metadata is incomplete'),
    ('sandbox_enabled', '1', 'V8 sandbox or pointer compression is not supported'),
    ('pointer_compression_enabled', '1', 'V8 sandbox or pointer compression is not supported'),
]:
    # An expected LLDB error makes its batch exit nonzero, so inspect its output.
    try:
        run('frames.js', '', [f'command script import {here / "metadata_fault.py"}',
                              f'ember-metadata-fault {field} {value}', 'v8 bt'])
    except RuntimeError as failure:
        assert reason in str(failure), (field, failure)
    else:
        raise AssertionError('metadata fault was accepted: ' + field)
print('schema 2 frames, properties, Date, FixedArray and metadata refusal: PASS')
