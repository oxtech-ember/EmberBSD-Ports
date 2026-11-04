#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the selected BSDinstall after moving it into another prefix."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('binary', 'shell', 'printf', 'shell-name', 'strip-name'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()
for name in (a.shell_name, a.strip_name):
    if Path(name).name != name or name in ('', '.', '..'):
        p.error('selected tool names must be single basenames')
binary, shell, printf = (Path(value).resolve(strict=True) for value in (a.binary, a.shell, a.printf))
with tempfile.TemporaryDirectory(prefix="bsdinstall test '") as temp:
    root = Path(temp)
    bindir = root / 'prefix space' / 'bin'
    bindir.mkdir(parents=True)
    install = bindir / 'bsdinstall'
    shutil.copy2(binary, install)
    selected_shell = bindir / a.shell_name
    selected_shell.symlink_to(shell)
    strip = bindir / a.strip_name
    strip.write_text('#!' + str(shell) + '\n' + shlex.quote(str(printf)) + ' "%s\\n" "$@" > "$RECORD"\n')
    strip.chmod(0o755)
    source = root / 'input'
    source.write_text('payload')
    external = root / 'external-link'
    external.symlink_to(install)
    internal = bindir / 'alias'
    internal.symlink_to('bsdinstall')
    cases = [('absolute', [str(install)], root, str(bindir)),
             ('relative', [os.path.relpath(install, root)], root, str(bindir)),
             ('PATH', ['bsdinstall'], root, str(bindir)),
             ('empty PATH', ['bsdinstall'], bindir, ':/missing'),
             ('internal symlink', [str(internal)], root, str(bindir)),
             ('external symlink', [str(external)], root, str(bindir))]
    for label, command, cwd, path in cases:
        output, record = root / (label + ' file'), root / (label + '.record')
        env = dict(os.environ, PATH=path, RECORD=str(record))
        env.pop('STRIP', None)
        result = subprocess.run(command + ['-s', str(source), str(output)], cwd=cwd,
                                env=env, capture_output=True, text=True)
        assert result.returncode == 0, (label, result.stderr)
        assert record.read_text().strip() == str(output)
    output, record = root / "quoted destination ' and spaces", root / 'quoted.record'
    env = dict(os.environ, PATH=str(bindir), RECORD=str(record))
    env.pop('STRIP', None)
    result = subprocess.run([str(install), '-s', '-S', '--demo', str(source), str(output)],
                            cwd=root, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert record.read_text().splitlines() == ['--demo', str(output)]
    custom = root / 'custom'
    custom.write_text('#!' + str(shell) + '\n' + shlex.quote(str(printf)) + ' "%s\\n" "$@" > "$RECORD"\n')
    custom.chmod(0o755)
    env['STRIP'] = str(custom)
    output = root / 'explicit'
    result = subprocess.run([str(install), '-s', str(source), str(output)], env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert record.read_text().strip() == str(output)
    env['STRIP'] = shlex.quote(str(custom))
    result = subprocess.run([str(install), '-s', '-S', '--explicit', str(source), 'explicit-shell'],
                            cwd=root, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert record.read_text().splitlines()[0] == '--explicit'
    env.pop('STRIP')
    result = subprocess.run([str(install), '-a', ':', str(source), 'after'], cwd=root,
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    selected_shell.unlink()
    result = subprocess.run([str(install), '-s', '-S', '--demo', str(source), str(root / 'missing-shell')],
                            env=env, capture_output=True, text=True)
    assert result.returncode != 0
    selected_shell.symlink_to(shell)
    strip.unlink()
    output = root / 'missing'
    result = subprocess.run([str(install), '-s', str(source), str(output)], env=env,
                            capture_output=True, text=True)
    assert result.returncode != 0 and not output.exists()
    result = subprocess.run([str(install), str(source), str(root / 'plain')], env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    for flag in ('-s', '-a'):
        output = root / ('resolve-failure' + flag)
        badenv = dict(env)
        badenv.pop('PATH', None)
        args = ['missing-self', flag] + ([':'] if flag == '-a' else []) + [str(source), str(output)]
        result = subprocess.run(args, executable=str(install), env=badenv, capture_output=True, text=True)
        assert result.returncode != 0 and not output.exists(), (flag, result.stderr)
print('BSDinstall relocation, overrides and failure handling PASS')
