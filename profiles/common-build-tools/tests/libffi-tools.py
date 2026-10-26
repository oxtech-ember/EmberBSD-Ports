#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Parse the actual libffi recipe for Darwin and ELF tool requirements."""

import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bmake', 'makefiles', 'shell'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--recipe', type=Path,
        default=Path(__file__).resolve().parents[3] / 'pkgsrc/devel/libffi/Makefile')
    options = parser.parse_args()
    for path in (options.bmake, options.makefiles, options.shell, options.recipe):
        if not path.is_absolute() or not path.exists():
            parser.error('Select existing absolute input paths.')
    source = options.recipe.read_text()
    with tempfile.TemporaryDirectory(prefix='libffi-tools-') as temporary:
        root = Path(temporary)
        recipe = root / 'devel/libffi'
        recipe.mkdir(parents=True)
        (root / 'mk').mkdir()
        # Parse the complete production recipe. Empty framework includes avoid
        # running package checks or selecting host tools in this finite fixture.
        for name in ('compiler.mk', 'bsd.prefs.mk', 'pthread.buildlink3.mk', 'bsd.pkg.mk'):
            (root / 'mk' / name).write_text('# Metadata fixture only.\n')
        config = root / 'mk.conf'
        config.write_text('# No user make configuration.\n')
        environment = dict(PATH=os.pathsep.join((str(options.bmake.parent), str(options.shell.parent))),
                           LC_ALL='C', MAKECONF=str(config), TMPDIR=str(root))

        def query(text, system):
            (recipe / 'Makefile').write_text(text)
            command = [str(options.bmake), '-r', '-m', str(options.makefiles),
                'SHELL=' + str(options.shell), 'MAKECONF=' + str(config),
                'OPSYS=' + system, 'PKGSRC_COMPILER=clang',
                'MACHINE_PLATFORM=' + system + '-test-aarch64',
                '-C', str(recipe), '-V', '${USE_TOOLS}']
            result = subprocess.run(command, env=environment, capture_output=True, text=True,
                                    check=True, timeout=30)
            return set(result.stdout.split())

        def correct(tools, system):
            return {'gmake', 'pkg-config'} <= tools and (('readelf' in tools) == (system != 'Darwin'))

        for system in ('Darwin', 'NetBSD', 'Linux'):
            tools = query(source, system)
            assert correct(tools, system), (system, sorted(tools))
        # Controls prove these expectations detect the original unconditional
        # Darwin dependency and an accidental loss of the ELF requirement.
        assert not correct(query(source + '\nUSE_TOOLS+= readelf\n', 'Darwin'), 'Darwin')
        assert not correct(query(source + '\nUSE_TOOLS:= ${USE_TOOLS:Nreadelf}\n', 'NetBSD'), 'NetBSD')
    print('PASS: Darwin, NetBSD and Linux recipe metadata; both deliberate tool-selection faults detected')


if __name__ == '__main__':
    main()
