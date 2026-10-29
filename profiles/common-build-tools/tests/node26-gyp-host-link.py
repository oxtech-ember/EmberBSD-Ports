#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check generated GYP link commands: source, selected host Python arguments."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    source = Path(sys.argv[1]).resolve()
    python = str(Path(sys.argv[2]).resolve())
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source / 'tools/gyp/pylib'))
    from gyp.generator.make import LINK_COMMANDS_LINUX, LINK_COMMANDS_MAC
    original_linux, original_mac = LINK_COMMANDS_LINUX, LINK_COMMANDS_MAC
    for host, flavor in (('darwin', 'mac'), ('darwin', 'netbsd'), ('linux', 'netbsd')):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'a.gyp').write_text(
                "{'targets':[{'target_name':'hello','type':'executable',"
                "'toolsets':['host','target'],'sources':['main.cc']}]}\n")
            (root / 'main.cc').write_text('int main() { return 0; }\n')
            env = dict(os.environ, PYTHONPATH=str(source / 'tools/gyp/pylib'))
            for name in ('GYP_CROSSCOMPILE', 'AR_host', 'AR_target', 'CC_host',
                         'CC_target', 'CXX_host', 'CXX_target'):
                env.pop(name, None)
            env['PYTHONDONTWRITEBYTECODE'] = '1'
            if flavor != 'mac':
                env['GYP_CROSSCOMPILE'] = '1'
            code = 'import sys;sys.platform=' + repr(host) + ';import gyp;sys.exit(gyp.script_main())'
            subprocess.run([python, '-B', '-c', code, '--no-parallel', '-f', 'make-' + flavor,
                            '--depth=.', 'a.gyp'], cwd=root, env=env, check=True)
            lines = (root / 'Makefile').read_text().splitlines()
            commands = dict(line.split(' = ', 1) for line in lines
                            if line.startswith(('cmd_link', 'cmd_solink')) and ' = ' in line)
            for name in ('link', 'solink', 'solink_module'):
                command = 'cmd_' + name
                if (host, flavor) == ('darwin', 'netbsd'):
                    assert commands[command] == '$(cmd_' + name + '_$(TOOLSET))'
                    assert commands[command + '_host'] == next(
                        line.split(' = ', 1)[1] for line in original_mac.splitlines()
                        if line.startswith(command + ' = '))
                    assert commands[command + '_target'] == next(
                        line.split(' = ', 1)[1] for line in original_linux.splitlines()
                        if line.startswith(command + ' = '))
                else:
                    assert command + '_host' not in commands and command + '_target' not in commands
                    template = original_mac if host == 'darwin' else original_linux
                    assert commands[command] == next(
                        line.split(' = ', 1)[1] for line in template.splitlines()
                        if line.startswith(command + ' = '))
    print('GYP link commands: Darwin native/cross and Linux cross PASS')


if __name__ == '__main__':
    main()
