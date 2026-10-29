#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise cross compiler-rt symbol generation with selected host tools."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('bmake', 'pkgsrc', 'makeconf', 'host-prefix', 'archive', 'generator'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--make-arg', action='append', default=[])
a = p.parse_args()
host = a.host_prefix
base = [str(a.bmake), '-C', str(a.pkgsrc / 'lang/compiler-rt'),
        'MAKECONF=' + str(a.makeconf), '_PKGSRC_BARRIER=yes', *a.make_arg]
values = subprocess.run(base + ['-V', '${PKGNAME}', '-V', '${PYTHON_FOR_BUILD_ONLY}',
                                '-V', '${MAKE_ENV}', '-V', '${CMAKE_CONFIGURE_ARGS}',
                                '-V', '${TOOL_PYTHONBIN}'],
                        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout.splitlines()
assert len(values) == 5, values
name, role, make_env, configure, python = values
assert name.startswith('compiler-rt-') and role == 'tool', (name, role)
assert Path(python).resolve().is_relative_to(host.resolve()), python
assert '-DCMAKE_NM:FILEPATH=' + str(host / 'bin/llvm-nm') in shlex.split(configure)
env = {k: os.environ[k] for k in ('HOME', 'TMPDIR', 'USER', 'LOGNAME') if k in os.environ}
env.update(PATH=str(host / 'bin') + ':' + str(host / 'sbin'), LC_ALL='C')
for assignment in shlex.split(make_env):
    if '=' in assignment:
        key, value = assignment.split('=', 1)
        env[key] = value
assert not env.get('PYTHONPATH'), env.get('PYTHONPATH')
with tempfile.TemporaryDirectory(prefix='compiler-rt-cross-host-') as td:
    output = Path(td) / 'exports.syms'
    subprocess.run([python, str(a.generator),
                    '--nm-executable', str(host / 'bin/llvm-nm'), '-o', str(output), str(a.archive)],
                   env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    assert output.stat().st_size > 0
print('PASS: actual target archive processed by selected host Python and llvm-nm')
