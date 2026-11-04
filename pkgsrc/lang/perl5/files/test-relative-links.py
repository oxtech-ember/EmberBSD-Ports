#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the actual Perl package post-install links at a relocated prefix."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--recipe', type=Path, required=True)
    parser.add_argument('--dirs', type=Path, required=True)
    parser.add_argument('--bmake', required=True)
    parser.add_argument('--mk', required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    args = parser.parse_args()

    recipe = args.recipe.read_text()
    start = recipe.index('.PHONY: perl5-post-install')
    end = recipe.index('.if ${OPSYS} == "Haiku"', start)
    definitions = [line for line in recipe.splitlines()
                   if line.startswith(('_PERL5_RELBASE=', '_PERL5_MANUP='))]
    with tempfile.TemporaryDirectory(prefix='perl-relative-') as temporary:
        root = Path(temporary)
        fixture = root / 'Makefile'
        # Preserve dirs.mk verbatim; its pkgsrc preferences include is stubbed.
        dirs = root / 'lang/perl5/dirs.mk'
        dirs.parent.mkdir(parents=True)
        shutil.copyfile(args.dirs, dirs)
        prefs = root / 'mk/bsd.prefs.mk'
        prefs.parent.mkdir()
        prefs.write_text('# fixture preferences\n')
        fixture.write_text('.include "' + str(dirs) + '"\n' +
                           '\n'.join(definitions) + '\n' + recipe[start:end])
        files = root / 'files'
        files.mkdir()
        (files / 'perllink.1').write_text('manual')
        work = root / 'work'
        work.mkdir()
        (work / 'perllink.sh').write_text('# selected script\n')
        for mandir in ('man', 'share/man'):
            stage = root / ('stage-' + mandir.replace('/', '-'))
            destination = stage / 'usr/pkg'
            base = destination / 'lib/perl5'
            for directory in (destination / 'bin', destination / mandir / 'man1',
                              base / 'bin', base / mandir / 'man1'):
                directory.mkdir(parents=True, exist_ok=True)
            binary = args.prefix / 'bin'
            gnu = args.prefix / 'gnu/bin'
            command = [args.bmake, '-m', args.mk, '-f', str(fixture),
                       'PREFIX=/usr/pkg', 'DESTDIR=' + str(stage), 'PKGMANDIR=' + mandir,
                       'WRKDIR=' + str(work), 'FILESDIR=' + str(files), 'RUN=',
                       'TEST=' + str(gnu / 'test'),
                       'INSTALL_SCRIPT=' + str(binary / 'bsdinstall') + ' -m 755',
                       'INSTALL_MAN=' + str(binary / 'bsdinstall') + ' -m 644',
                       'RM=' + str(gnu / 'rm'), 'LN=' + str(gnu / 'ln'),
                       'perl5-post-install']
            environment = dict(os.environ, PATH=str(binary) + ':' + str(gnu))
            subprocess.run(command, cwd=root, env=environment, check=True,
                           capture_output=True, text=True)
            moved = root / ('moved-' + mandir.replace('/', '-'))
            shutil.move(destination, moved)
            pairs = ((moved / 'bin/perllink', moved / 'lib/perl5/bin/perllink'),
                     (moved / mandir / 'man1/perllink.1',
                      moved / 'lib/perl5' / mandir / 'man1/perllink.1'))
            for link, target in pairs:
                assert link.is_symlink(), f'missing link: {link}'
                assert not os.path.isabs(os.readlink(link)), (
                    f'absolute link in relocated package: {link}')
                assert link.resolve(strict=True) == target.resolve(strict=True)
            print(f'{mandir}: relative links survive relocation')


if __name__ == '__main__':
    main()
