#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), manual-path checks for the package oracle.
"""Check man directories, gzip selection and real missing-file refusals."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('pkgsrc', type=Path)
    cli.add_argument('new_work', type=Path)
    cli.add_argument('--runner', type=Path, default=Path(__file__).with_name('gstreamer-plugins-cross.sh'))
    args = cli.parse_args()
    tree = args.pkgsrc.resolve(strict=True)
    runner = args.runner.resolve(strict=True)
    out = args.new_work
    require(out.is_absolute() and out.resolve() == out and not out.exists() and not out.is_symlink(),
            'Use a new canonical absolute work directory.')
    require(not out.is_relative_to(tree), 'Keep work outside the source tree.')
    require(not any(c in str(out) for c in '\r\n'), 'Invalid work path.')
    bmake = Path(os.environ['BMAKE']).resolve(strict=True)
    framework = tree / 'mk/plist'
    for name in ('plist-functions.awk', 'plist-man.awk'):
        require((framework / name).is_file(), 'Missing pkgsrc manual-list rule.')
    out.mkdir(mode=0o700, parents=True)
    host = out / 'host'
    (host / 'bin').mkdir(parents=True)
    tools = ('glib-mkenums', 'glib-genmarshal', 'g-ir-scanner', 'g-ir-compiler')
    for tool in tools:
        executable = host / 'bin' / tool
        executable.write_text('#!/bin/sh\nexit 0\n')
        executable.chmod(0o755)
    inputs = {str(runner): hashlib.sha256(runner.read_bytes()).hexdigest()}
    for name in ('plist-functions.awk', 'plist-man.awk'):
        p = framework / name
        inputs[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    records = []
    for mandir in ('man', 'share/man'):
        for compressed in (False, True):
            label = mandir.replace('/', '-') + ('-gzip' if compressed else '-plain')
            case = out / label
            fixture = case / 'pkgsrc'
            fixture.mkdir(parents=True)
            (fixture / 'mk').symlink_to(tree / 'mk', target_is_directory=True)
            dest = case / 'stage'
            prefix = dest / 'usr/pkg'
            manual = None
            for family in ('base', 'bad'):
                source = tree / ('multimedia/gst-plugins1-' + family) / 'PLIST'
                inputs[str(source)] = hashlib.sha256(source.read_bytes()).hexdigest()
                package = fixture / ('multimedia/gst-plugins1-' + family)
                package.mkdir(parents=True)
                shutil.copy2(source, package / 'PLIST')
                escape = lambda s: str(s).replace('$', '$$').replace('#', r'\#')
                makefile = ['PKGNAME=gst-plugins1-' + family + '-1.28.8nb1',
                            'DESTDIR=' + escape(dest), 'PREFIX=/usr/pkg',
                            'TOOLBASE=' + escape(host), 'PKGMANDIR=' + mandir,
                            '_MANZ=' + ('yes' if compressed else 'no'),
                            'CATMAN_SECTION_SUFFIX=no',
                            '_IMAKE_MANINSTALL=maninstall catinstall',
                            '_PLIST_MANINSTALL=maninstall catinstall',
                            '.if ${USE_CROSS_COMPILE:Uyes} == "no"', 'MESON_BINARIES=', '.else',
                            'MESON_BINARIES=' + ' '.join(tools), '.endif']
                makefile += ['MESON_BINARY.' + tool + '=${TOOLBASE}/bin/' + tool for tool in tools]
                (package / 'Makefile').write_text('\n'.join(makefile) + '\n')
                for name in source.read_text().splitlines():
                    if not name or not name[0].islower() or '$' in name:
                        continue
                    installed = name
                    if name.startswith('man/'):
                        installed = mandir + '/' + name.removeprefix('man/')
                        if compressed:
                            installed += '.gz'
                    file = prefix / installed
                    file.parent.mkdir(parents=True, exist_ok=True)
                    data = b'<repository><record name="Fixture"/></repository>\n' if name.endswith('.gir') else b'fixture\n'
                    if name.startswith('man/') and compressed:
                        data = gzip.compress(data, mtime=0)
                    file.write_bytes(data)
                    if family == 'base' and name.startswith('man/') and manual is None:
                        manual = file
            require(manual is not None, 'The real base PLIST has no manual-page fixture.')
            env = dict(os.environ, BMAKE=str(bmake), MAKECONF='/dev/null')
            def run(kind, expected):
                work = case / (kind + '-result')
                argv = ['sh', str(runner), str(fixture), str(work)]
                result = subprocess.run(argv, env=env, capture_output=True, text=True)
                (case / (kind + '.stdout')).write_text(result.stdout)
                (case / (kind + '.stderr')).write_text(result.stderr)
                require(result.returncode == expected, label + '/' + kind + ': unexpected status ' + str(result.returncode))
                if expected:
                    relative = str(manual.relative_to(prefix))
                    require('Missing package file: ' + relative in result.stderr,
                            'The refusal did not identify the removed manual page.')
                records.append(dict(case=label, kind=kind, argv=argv, exit=result.returncode,
                                    missing_file=str(manual.relative_to(prefix)) if expected else None))
            run('positive', 0)
            original = manual.read_bytes()
            manual.unlink()
            run('missing-file', 1)
            manual.write_bytes(original)
            run('restored', 0)
    result = dict(status='PASS', input_sha256=inputs, cases=records,
                  positive_cases=4, causal_missing_file_controls=4, restored_positive_cases=4,
                  scope='Metadata and file-oracle fixtures with real BSD make. The runner retains both '
                        'generator selections and all 20 source-list GIR/typelib paths. '
                        'No GStreamer compilation, media execution or real typelib loading is claimed.')
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: four manual-directory/gzip cases, four missing-file refusals and four restored cases.')


if __name__ == '__main__':
    main()
