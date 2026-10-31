# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
"""Run Clang's analyzer using the selected build's actual FIT C flags."""
import sys
sys.dont_write_bytecode = True
import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from common import arguments


def options(parser):
    parser.add_argument('--build-dir', type=Path, required=True,
                        help='configured U-Boot output directory with .cmd files')


args = arguments('Analyze FIT modules using recorded target compile flags', options)
build = args.build_dir.resolve(strict=True)
env = dict(os.environ)
env['PATH'] = os.pathsep.join((str(args.host_prefix / 'bin'), str(args.host_prefix / 'gnu/bin')))
objects = ('spl/boot/image-fit.o', 'spl/common/spl/spl_fit.o')
with tempfile.TemporaryDirectory(prefix='uboot-analyze-') as directory:
    for obj in objects:
        objpath = Path(obj)
        command_file = build / objpath.parent / ('.' + objpath.name + '.cmd')
        command = shlex.split(command_file.read_text().splitlines()[0].split(':=', 1)[1])
        if Path(command[0]).resolve(strict=True) != args.clang:
            raise SystemExit('recorded compiler differs from selected native clang')
        inputs = [Path(item) for item in command[1:]
                  if item.endswith('.c') and not item.startswith('-')]
        expected = args.source / ('boot/image-fit.c' if objpath.name == 'image-fit.o'
                                  else 'common/spl/spl_fit.c')
        if len(inputs) != 1 or (build / inputs[0]).resolve(strict=True) != expected.resolve(strict=True):
            raise SystemExit('recorded C input differs from --source')
        filtered = []
        skip = False
        for item in command:
            if skip:
                skip = False
                continue
            if item == '-o':
                skip = True
                continue
            if item == '-c' or item.startswith('-Wp,-MMD'):
                continue
            filtered.append(item)
        report = Path(directory) / (objpath.name + '.plist')
        subprocess.run(filtered[:1] + ['--analyze', '-o', str(report)] + filtered[1:],
                       cwd=build, env=env, check=True)
        print('analyzed', obj, flush=True)
