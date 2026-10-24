#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check GI transfer deadline parsing and routing without target execution."""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--helper', type=Path, default=Path(__file__).resolve().parents[3]
                        / 'pkgsrc/devel/gobject-introspection/files/target-query.py')
    parser.add_argument('new_work', type=Path)
    options = parser.parse_args()
    source = options.helper.read_bytes()
    tree = ast.parse(source)
    names = ('QueryError', 'require', 'transfer_timeout', 'completed', 'run')
    nodes = [next(n for n in ast.walk(tree)
                  if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name == name)
             for name in names]
    work = options.new_work
    assert work.is_absolute() and work.resolve() == work and not work.exists()
    work.mkdir()
    cases, calls = [], []

    class SDKError(Exception):
        pass

    class OwnershipError(SDKError):
        pass

    class CommandError(SDKError):
        returncode, stdout, stderr = 7, b'out\n', b'err\n'
        stdout_truncated = stderr_truncated = False

    failure = None

    def capture(command, **options):
        calls.append((command, options))
        if failure is not None:
            raise failure
        return SimpleNamespace(value=b'out\n', stderr=b'err\n', stderr_truncated=False)

    scope = dict(stream=SimpleNamespace(capture_streamed=capture),
                 environment={'GI_TEST': 'host-only'}, subprocess=subprocess,
                 CommandError=CommandError, ProcessOwnershipError=OwnershipError,
                 SDKError=SDKError, work=work)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(options.helper), 'exec'), scope)
    deadline, run = scope['transfer_timeout'], scope['run']
    for value, expected in (({}, 180), ({'transfer_timeout_seconds': 1}, 1),
                            ({'transfer_timeout_seconds': 1800}, 1800),
                            ({'transfer_timeout_seconds': 3600}, 3600)):
        assert deadline(value) == expected
        cases.append('accepted ' + repr(value))
    for value in (0, -1, 3601, True, False, 180.0, '180', None):
        try:
            deadline({'transfer_timeout_seconds': value})
        except scope['QueryError']:
            cases.append('refused ' + repr(value))
        else:
            raise AssertionError('Invalid transfer deadline accepted: ' + repr(value))
    run('ordinary', ['ssh', 'allocation'])
    assert calls[-1][1]['timeout'] == 180
    cases.append('ordinary phase retains 180 seconds')
    run('transfer', ['ssh', 'tar'], b'payload', timeout=deadline({'transfer_timeout_seconds': 1800}))
    assert calls[-1][1]['timeout'] == 1800 and calls[-1][1]['input'] == b'payload'
    assert calls[-1][1]['stdout_limit'] == 16 * 1024 * 1024
    assert calls[-1][1]['empty_snapshot_timeout'] == 30
    cases.append('transfer routes the configured deadline and unchanged input/limits')
    failure = CommandError()
    try:
        run('status7', ['ssh', 'command'])
    except scope['QueryError']:
        assert (work / 'status7.log').read_bytes() == b'out\nerr\n'
        cases.append('completed nonzero command remains a status refusal')
    else:
        raise AssertionError('Nonzero command accepted')
    failure = SDKError('producer stream deadline expired')
    try:
        run('expired', ['ssh', 'tar'], b'payload', timeout=1800)
    except SDKError as error:
        assert error is failure
        assert (work / 'expired.log').read_text() == (
            'refused: producer stream deadline expired\ntimeout_seconds=1800\ninput_bytes=7\n')
        cases.append('SDK failure preserves its exception and phase receipt')
    else:
        raise AssertionError('SDK failure accepted')
    failure = OwnershipError('ownership unknown')
    try:
        run('unknown', ['ssh', 'tar'], b'payload', timeout=1800)
    except OwnershipError as error:
        assert error is failure and not (work / 'unknown.log').exists()
        cases.append('ownership uncertainty remains distinct and is rethrown')
    else:
        raise AssertionError('Ownership uncertainty accepted')
    routes = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Name) and n.func.id == 'run'
              and any(k.arg == 'timeout' for k in n.keywords)]
    assert len(routes) == 1 and ast.literal_eval(routes[0].args[0]) == 'transfer'
    routed = routes[0].keywords[0].value
    assert isinstance(routed, ast.Name) and routed.id == 'transfer_timeout_seconds'
    cases.append('only transfer overrides the host deadline')
    xml = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'xml_result' for t in n.targets))
    assert next(ast.literal_eval(k.value) for k in xml.value.keywords if k.arg == 'timeout') == 180
    assert b'timeout -k 5 60 ' in source
    cases.append('XML 180 and target execution 60 seconds remain unchanged')
    assert options.helper.read_bytes() == source
    result = dict(status='PASS', cases=cases, helper=str(options.helper.resolve()),
                  helper_sha256=hashlib.sha256(source).hexdigest(), argv=sys.argv,
                  limits='Pure parsing and injected SDK host-boundary outcomes only. '
                         'No SSH, compiler, target execution, session drain or throughput acceptance.')
    (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', cases=len(cases))))


if __name__ == '__main__':
    main()
