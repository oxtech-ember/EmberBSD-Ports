"""Dry-run the real GYP archive commands with an explicit GNU make and shell."""
import argparse
import ast
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


def command_templates(source):
    values = {}
    for item in ast.parse(source).body:
        if not isinstance(item, ast.Assign) or len(item.targets) != 1:
            continue
        name = getattr(item.targets[0], 'id', '')
        if name not in ('LINK_COMMANDS_MAC', 'LINK_COMMANDS_LINUX'):
            continue
        value = item.value
        if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Mod):
            values[name] = ast.literal_eval(value.left) % {'python': sys.executable}
        else:
            values[name] = ast.literal_eval(value)
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--make', type=Path, required=True)
    parser.add_argument('--shell', type=Path, required=True)
    args = parser.parse_args()
    if not args.make.is_absolute() or not args.shell.is_absolute():
        parser.error('Select absolute build-host make and shell paths')
    templates = command_templates(args.source.read_text())
    with tempfile.TemporaryDirectory(prefix='node-darwin-libtool-') as tmp:
        work = Path(tmp)
        fixture = work / 'Makefile'
        env = {k: v for k, v in os.environ.items()
               if k not in ('GYP_LIBTOOL', 'MAKEFLAGS', 'MFLAGS', 'MAKELEVEL')}
        env['PATH'] = str(args.make.parent) + os.pathsep + str(args.shell.parent)

        def observe(template, selected=None, darwin=True):
            fixture.write_text(template + '\nTOOLSET=target\nAR.target=selected-ar\n'
                               'all:\n\t$(cmd_alink)\n')
            current = dict(env)
            if selected is not None:
                current['GYP_LIBTOOL'] = selected
            result = subprocess.run([str(args.make), '-n', '-f', str(fixture),
                                     'SHELL=' + str(args.shell), 'all'], cwd=work,
                                    env=current, text=True, capture_output=True,
                                    timeout=20, check=True)
            words = shlex.split(result.stdout.strip())
            if darwin:
                start = words.index('filter-libtool') + 1
                assert words[start + 1:] == ['-static', '-o', 'all'], words
                return words[start]
            return words

        mac = templates['LINK_COMMANDS_MAC']
        assert observe(mac) == '/usr/bin/libtool'
        for selected in ('/selected prefix/bin/llvm-libtool-darwin',
                         '/missing-selected/libtool', ''):
            assert observe(mac, selected) == selected
        linux = templates['LINK_COMMANDS_LINUX']
        ordinary = observe(linux, darwin=False)
        assert observe(linux, '/selected/libtool', darwin=False) == ordinary
        assert ordinary[-3:] == ['selected-ar', 'crs', 'all'], ordinary
    print('PASS: Darwin default, selected path, missing path, empty path, and GNU archive route')


if __name__ == '__main__':
    main()
