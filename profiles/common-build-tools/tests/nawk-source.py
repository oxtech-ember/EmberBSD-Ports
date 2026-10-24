#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), shared bundled nawk source regression.
"""Check pinned source, BSD ctype adaptation and bundled parser provenance."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
TAG = '20260426'
ARCHIVE_SHA256 = '7ae5b9fc6a8149bc45ea0ba3ba434a69a16d1460d19f6d01b6f04cc885b8e02b'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(recipe, archive, source_only):
    makefile = (recipe / 'Makefile').read_text()
    require(re.search(r'^DISTNAME=\s*nawk-' + TAG + r'$', makefile, re.M), 'old bundled nawk snapshot')
    manifest = json.loads((recipe / 'SOURCE.json').read_text())
    require(manifest['upstream']['tag'] == TAG and
            manifest['upstream']['commit'] == '5739fd79bcfc75ba7526773d0cf634521f8aca3c', 'changed upstream pin')
    data = archive.read_bytes()
    require(sha(data) == ARCHIVE_SHA256 == manifest['upstream']['archive']['sha256'], 'archive checksum differs')
    require(len(data) == manifest['upstream']['archive']['size'], 'archive size differs')
    require(manifest['upstream']['archive']['url'] ==
            'https://codeload.github.com/onetrueawk/awk/tar.gz/refs/tags/' + TAG, 'foreign source URL')
    require(manifest['bsd_ctype_commit'].endswith('7099c72bfddcbf9671d3a3478636cf05e73bbfaa'), 'lost BSD fix provenance')
    with tarfile.open(fileobj=io.BytesIO(data)) as upstream:
        prefix = 'awk-' + TAG + '/'
        upstream_makefile = upstream.extractfile(prefix + 'makefile').read()
        notice = upstream_makefile.split(b'\nCFLAGS =', 1)[0]
        require((recipe / 'files/Makefile').read_bytes().startswith(notice),
                'upstream Makefile copyright/permission notice changed or was removed')
        require(manifest['test_directories'] == ['testdir', 'bugs-fixed'], 'missing upstream test tree')
        core = {Path(member.name).name for member in upstream.getmembers()
                if member.isfile() and member.name.count('/') == 1 and
                Path(member.name).suffix in ('.c', '.h', '.y')}
        require(all(manifest['files'].get(name) == name for name in core), 'missing or remapped upstream C input')
        for original, target in manifest['files'].items():
            selected = (recipe / 'files' / target).read_bytes()
            raw = upstream.extractfile(prefix + original).read()
            if target in ('lib.c', 'run.c'):
                # The only C adaptations are byte-valued ctype casts. Strip
                # these casts to compare all remaining source bytes exactly.
                normalized = lambda content: re.sub(rb'\((?:uschar|int)\)\s*', b'', content)
                require(normalized(raw) == normalized(selected), 'unexpected C change: ' + target)
                require(selected.count(b'(uschar)') > raw.count(b'(uschar)'), 'missing BSD byte casts: ' + target)
            elif target == 'nawk.1':
                require(b'.TH NAWK 1' in selected and re.search(rb'^nawk ', selected, re.M) and
                        b'The AWK Programming Language' in selected,
                        'manual command or original book title changed')
            else:
                require(selected == raw, 'upstream source differs: ' + target)
        for member in upstream.getmembers():
            if member.isfile() and any(member.name.startswith(prefix + directory + '/')
                                       for directory in manifest['test_directories']):
                raw = upstream.extractfile(member).read()
                relative = member.name[len(prefix):]
                if relative == 'testdir/REGRESS':
                    raw = raw.replace(b'cc echo.c -o echo && echo echo compiled',
                        b': "${CC:?Select the SDK C compiler}"\n"$CC" ${CPPFLAGS:-} ${CFLAGS:-} echo.c ${LDFLAGS:-} -o echo && echo echo compiled')
                    raw = raw.replace(b'oldawk=${oldawk-awk}\nawk=${awk-../a.out}',
                        b': "${oldawk:?Select the comparison awk}"\n: "${awk:?Select the awk under test}"')
                require(raw == (recipe / 'files' / relative).read_bytes(), 'upstream test differs: ' + relative)
    lib = (recipe / 'files/lib.c').read_text()
    for expression in ('isalpha((uschar) *s)', 'isalnum((uschar) *s)', 'isspace((uschar) *s)',
                       'tolower((uschar) s[1])', 'isxdigit((uschar) s[2])', 'isspace((uschar) s[4])',
                       'isdigit((uschar) s[1])', 'isdigit((uschar) s[0])', 'isspace((uschar) *ep)'):
        require(expression in lib, 'lost byte classification barrier: ' + expression)
    require((recipe / 'files/run.c').read_text().count('isdigit((uschar) f[0])') == 2,
            'format-width byte checks lost the unsigned-char barrier')
    build = (recipe / 'files/Makefile').read_text()
    require('YACC' not in build and 'HOSTCC' not in build and '\nmaketab:' not in build,
            'bootstrap attempted parser regeneration')
    require('$(LDFLAGS)' in build, 'selected linker flags omitted')
    require('${CP} -R ${FILESDIR} ${WRKSRC}' in makefile, 'ordinary source path differs')
    bootstrap = (ROOT / 'upstream/pkgsrc/bootstrap/bootstrap').read_text()
    require('copy_src $pkgsrcdir/lang/nawk/files awk' in bootstrap, 'bootstrap source path differs')
    require('lang/nawk' in (ROOT / 'pkgsrc/replaces').read_text().splitlines(), 'missing shared replacement')
    require(TAG in (recipe / 'files/main.c').read_text(), 'runtime source version differs')
    if source_only:
        return
    require((recipe / 'files/GENERATED.json').is_file(), 'New generated parser payload is required')
    generated = json.loads((recipe / 'files/GENERATED.json').read_text())
    for name, digest in generated['inputs'].items():
        require(sha((recipe / 'files' / name).read_bytes()) == digest, 'stale generator input: ' + name)
    for name in manifest['generated']:
        require(sha((recipe / 'files' / name).read_bytes()) == generated['outputs'][name],
                'stale generated output: ' + name)
    require(set(generated['inputs']) == {'awkgram.y', 'awk.h', 'proto.h', 'maketab.c'}, 'missing generator inputs')
    require(set(generated['outputs']) == set(manifest['generated']), 'missing parser outputs')
    require('#define YYBYACC 1' in (recipe / 'files/awkgram.tab.c').read_text(), 'foreign parser producer')
    header = (recipe / 'files/awkgram.tab.h').read_text()
    tokens = [(name, int(number)) for name, number in re.findall(r'^#define ([A-Z][A-Z_0-9]*) ([0-9]+)$', header, re.M)]
    low = next(number for name, number in tokens if name == 'FIRSTTOKEN')
    high = next(number for name, number in tokens if name == 'LASTTOKEN')
    names = [name for name, number in tokens if low <= number <= high]
    table = (recipe / 'files/proctab.c').read_text().split('printname[', 1)[1].split('};', 1)[0]
    require(re.findall(r'"([A-Z][A-Z_0-9]*)"', table) == names, 'procedure table/token order differs')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('archive', type=Path)
    cli.add_argument('recipe', type=Path)
    cli.add_argument('work', type=Path)
    cli.add_argument('--source-only', action='store_true', help='Do not accept a generated payload or build plan')
    cli.add_argument('--bmake', type=Path, help='Explicit BSD make for the generated-payload build-plan check')
    args = cli.parse_args()
    args.work.mkdir()
    verify(args.recipe, args.archive, args.source_only)
    fixture = args.work / 'negative-recipe'
    shutil.copytree(args.recipe, fixture)
    for relative, before, after in (
        ('files/lib.c', b'isspace((uschar) *s)', b'isspace((int) *s)'),
        ('files/LICENSE', b'Lucent Technologies', b'Changed copyright'),
        ('files/Makefile', b'Lucent Technologies', b'Changed copyright'),
        ('SOURCE.json', b'5739fd79bcfc75ba7526773d0cf634521f8aca3c', b'0' * 40),
        ('Makefile', b'${CP} -R ${FILESDIR} ${WRKSRC}', b'${CP} -R /foreign/source ${WRKSRC}')):
        path = fixture / relative
        original = path.read_bytes()
        require(before in original, 'invalid negative fixture: ' + relative)
        path.write_bytes(original.replace(before, after, 1))
        try:
            verify(fixture, args.archive, True)
        except ValueError:
            pass
        else:
            raise ValueError('accepted changed source contract: ' + relative)
        path.write_bytes(original)
    changed = args.work / 'changed.tar.gz'
    changed.write_bytes(args.archive.read_bytes() + b'changed')
    try:
        verify(fixture, changed, True)
    except ValueError:
        pass
    else:
        raise ValueError('accepted changed archive bytes')
    changed.unlink()
    print('PASS: pinned tagged source, original licenses/tests, BSD ctype casts and one bundled owner')
    print('PASS: changed archive, lost BSD cast/license/pin and foreign-source controls rejected')
    if args.source_only:
        print('SOURCE ONLY: generated payload, compiler and runtime remain unverified')
        return
    require(args.bmake is not None and args.bmake.is_absolute(), 'Select BSD make for the build-plan check')
    work = args.work / 'build'
    shutil.copytree(args.recipe / 'files', work)
    command = [str(args.bmake), '-r', '-n', 'CC=/selected/gcc16', 'CFLAGS=-O2', 'LDFLAGS=-Wl,selected', 'a.out']
    process = subprocess.run(command, cwd=work, capture_output=True,
        env=dict(os.environ, MAKEFLAGS='', MAKECONF='/dev/null'))
    (args.work / 'plan.out').write_bytes(process.stdout)
    (args.work / 'plan.err').write_bytes(process.stderr)
    require(process.returncode == 0, 'bundled build plan failed')
    plan = process.stdout.decode()
    require(' -Wl,selected ' in plan and all(line.startswith('/selected/gcc16 ') for line in plan.splitlines()),
            'build plan changed the selected compiler/linker')
    require('maketab.c' not in plan and 'yacc' not in plan and 'bison' not in plan, 'generator entered bootstrap build')
    print('PASS: generated input/output hashes, token tables and selected bootstrap/ordinary build plan')
    print('No package compilation or runtime acceptance')


if __name__ == '__main__':
    main()
