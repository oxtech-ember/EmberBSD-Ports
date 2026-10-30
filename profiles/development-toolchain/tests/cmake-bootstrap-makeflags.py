#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise GNU make under bmake's inherited flags and CMake's configure environment."""
import argparse
from pathlib import Path
import shlex
import subprocess
import tempfile

p = argparse.ArgumentParser()
for name in ('pkgsrc', 'bmake', 'gmake', 'makeconf', 'shell', 'env', 'prefix', 'work'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
base = [str(a.bmake), '-m', str(a.prefix / 'share/mk'), 'SHELL=' + str(a.shell),
        'MAKECONF=' + str(a.makeconf), 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
        '-C', str(a.pkgsrc / 'devel/cmake')]
result = subprocess.run(base + ['-V', '${_CONFIGURE_SCRIPT_ENV}', '-V', '${CONFIGURE_ARGS}'],
                        capture_output=True, text=True, check=True)
lines = result.stdout.splitlines()
assert len(lines) == 2
config_env = shlex.split(lines[0])
assert 'MAKEFLAGS=' in config_env
assert any(word.startswith('--parallel=') for word in shlex.split(lines[1]))

with tempfile.TemporaryDirectory(dir=a.work) as tmp:
    work = Path(tmp)
    (work / 'probe.mk').write_text('all:\n\t@printf ok > result\n')
    command = [str(a.gmake), '-f', str(work / 'probe.mk')]
    driver = work / 'driver.mk'
    def run(env):
        (work / 'result').unlink(missing_ok=True)
        words = [str(a.env), *env, *command]
        driver.write_text('.SHELL: name=sh path=' + str(a.shell) + '\nall:\n\t@cd ' + shlex.quote(str(work)) + ' && ' +
                          ' '.join(map(shlex.quote, words)) + '\n')
        return subprocess.run([str(a.bmake), '-m', str(a.prefix / 'share/mk'),
            '-f', str(driver)], capture_output=True, text=True)
    bad = run([])
    assert bad.returncode == 0 and not (work / 'result').exists(), bad.stdout + bad.stderr
    good = run(config_env)
    assert good.returncode == 0, good.stdout + good.stderr
    assert (work / 'result').read_text() == 'ok'
print('CMake configure environment prevents bmake flags from breaking GNU make: PASS')
