#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check actual Bash generator commands from the selected host prefix."""
import json
import os
from pathlib import Path
import shlex
import sys

sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
from sdk_source import install_signal_handlers

install_signal_handlers()
sdk, args = load_sdk()
from emberbsd_sdk.errors import CommandError, SDKError
from emberbsd_sdk.stream import PRODUCER_STREAM_API, capture_streamed

if type(PRODUCER_STREAM_API) is not int or PRODUCER_STREAM_API != 1:
    raise SDKError('SDK producer stream API 1 is required')
if len(args) != 3:
    raise SystemExit('Use EXPORTED_PKGSRC MAKECONF NEW_WORK; set absolute BMAKE')
tree, conf = (Path(p).resolve(strict=True) for p in args[:2])
work = Path(args[2])
if not work.is_absolute():
    raise SystemExit('Use an absolute new work directory')
make = Path(os.environ['BMAKE'])
if not make.is_absolute():
    raise SystemExit('BMAKE must name the selected absolute SDK bmake')
work.mkdir()


def run(argv):
    try:
        result = capture_streamed(argv, timeout=180, stdout_limit=8 * 1024 * 1024)
        if result.stderr_truncated:
            raise SDKError('Metadata stderr exceeded the capture limit')
        return 0, result.value.decode(), result.stderr.decode()
    except CommandError as error:
        if error.stderr_truncated or error.stdout_truncated:
            raise SDKError('Refusal output exceeded the capture limit') from error
        return error.returncode, error.stdout.decode(), error.stderr.decode()


names = ['PKG_FAIL_REASON', 'EMBERBSD_CROSS_BUILD_CC', 'NATIVE_CC',
         'EMBERBSD_CROSS_BUILD_CXX', 'NATIVE_CXX', 'CONFIGURE_ENV',
         'NATIVE_CPPFLAGS', 'NATIVE_CFLAGS', 'NATIVE_CXXFLAGS', 'NATIVE_LDFLAGS',
         'EMBERBSD_NATIVE_BMAKE', 'EMBERBSD_CROSS_BUILD_PYTHON']
command = [str(make), '-C', str(tree / 'shells/bash'), 'MAKECONF=' + str(conf),
           'show-vars', 'VARNAMES=' + ' '.join(names)]
code, output, errors = run(command)
(work / 'bash.txt').write_text(output)
(work / 'bash.stderr').write_text(errors)
if code:
    raise SystemExit('Bash metadata failed: ' + errors)
values = output.splitlines()
assert len(values) == len(names), values
data = dict(zip(names, values))
assert not data['PKG_FAIL_REASON'], data['PKG_FAIL_REASON']
assert Path(data['EMBERBSD_NATIVE_BMAKE']).resolve(strict=True) == make.resolve(strict=True)
assert Path(data['EMBERBSD_CROSS_BUILD_PYTHON']).resolve(strict=True) == Path(sys.executable).resolve(strict=True)
for language, flags in (('CC', 'CFLAGS'), ('CXX', 'CXXFLAGS')):
    expected = [data['EMBERBSD_CROSS_BUILD_' + language]]
    expected += shlex.split(data['NATIVE_CPPFLAGS'])
    expected += shlex.split(data['NATIVE_' + flags])
    expected += shlex.split(data['NATIVE_LDFLAGS'])
    assert shlex.split(data['NATIVE_' + language]) == expected
# Bash appends another assignment. Check every assignment, including the last.
assignments = [value for value in shlex.split(data['CONFIGURE_ENV'])
               if value.startswith('CC_FOR_BUILD=')]
assert len(assignments) >= 2, assignments
assert all(value == 'CC_FOR_BUILD=' + data['NATIVE_CC'] for value in assignments)
for role in ('CC', 'CXX', 'CPP', 'AS', 'LD', 'AR', 'RANLIB', 'NM', 'STRIP'):
    variable = 'NATIVE_' + role
    code, output, errors = run([str(make), '-C', str(tree / 'shells/bash'),
                              'MAKECONF=' + str(conf), variable + '=/bin/false',
                              '-v', 'PKG_FAIL_REASON'])
    (work / (variable + '.txt')).write_text(output)
    (work / (variable + '.stderr')).write_text(errors)
    assert code == 0, errors
    expected = ('Cross generators require the selected native build compilers'
                if role in ('CC', 'CXX', 'CPP') else
                variable + ' differs from the selected Ports tool')
    assert expected in output, (variable, output)
overrides = [('_EMBER_SDK_AR', '/usr/bin/ar'),
             ('_EMBER_NATIVE_CC_COMMAND', '/usr/bin/cc'),
             ('_EMBER_NATIVE_TOOLSET_CHECK', 'VERIFIED')]
overrides += [(prefix + name, '-I/target-only')
              for prefix in ('NATIVE_', 'HOST_')
              for name in ('CPPFLAGS', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS')]
for variable, value in overrides:
    code, output, errors = run([str(make), '-C', str(tree / 'shells/bash'),
                              'MAKECONF=' + str(conf), variable + '=' + value,
                              '-v', 'PKG_FAIL_REASON'])
    (work / (variable + '.stderr')).write_text(errors)
    assert code != 0, (variable, output)
    expected = ('Do not override reserved SDK native selection variables'
                if variable.startswith('_EMBER_') else
                variable + ' differs from the selected native ABI flags')
    assert expected in errors, (variable, errors)
(work / 'selection.json').write_text(json.dumps(data, indent=2) + '\n')
print('PASS: actual Bash generator ABI commands and overridden-compiler refusal; no compiler run')
