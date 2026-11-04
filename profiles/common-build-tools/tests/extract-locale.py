#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that the real recipe extract command writes UTF-8 member names.

The Ports make environment runs with LC_ALL=C. The common defaults give the
extract step alone a UTF-8 C locale. Without that setting the same command
must fail, so the fixture reproduces the bsdtar conversion error.
"""
import os
import shlex
import io
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
NAME = 'parseqrc/caf\u00e9.js'
RECIPES = ('audio/flac', 'devel/qt6-qttools')


def extract(make, tree, makeconf, recipe, archive, out, extra=()):
    query = subprocess.run([make, '-C', str(tree / recipe), 'MAKECONF=' + makeconf, *extra,
                            '-v', 'EXTRACT_CMD_DEFAULT'], capture_output=True, text=True)
    if query.returncode != 0 or not query.stdout.strip():
        sys.exit('FAIL: cannot evaluate the extract command of ' + recipe + ': ' + query.stderr.strip()[:300])
    out.mkdir()
    environment = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'TMPDIR': str(out.parent),
                   'extract_file': str(archive)}
    return subprocess.run(['/bin/sh', '-c', query.stdout.strip()], cwd=out,
                          capture_output=True, text=True, env=environment)


def check_crate(make, tree, makeconf, work, tool_tree=None):
    """Exercise real pkgsrc extraction and isolate crate tool discovery."""
    variables = tree / 'mk/extract/bsd.extract-vars.mk'
    current = variables.read_text()
    pattern = '    !empty(EXTRACT_ONLY:M*.crate) || \\\n'
    if current.count(pattern) != 2:
        sys.exit('FAIL: crate tool discovery is not present in both lists')
    baseline = current.replace(pattern, '')
    for label, content, expected in [('old', baseline, False), ('new', current, True)]:
        fragment = work / (label + '.mk')
        fragment.write_text(content)
        fixture = work / (label + '-fixture.mk')
        fixture.write_text('EXTRACT_ONLY= fixture.crate\nEXTRACT_USING= nbtar\n.include "' + str(fragment) + '"\n')
        result = subprocess.run([make, '-f', str(fixture), '-v', 'USE_TOOLS'],
                                capture_output=True, text=True, check=True)
        tools = result.stdout.split()
        if any((name in tools) != expected for name in ('tar', 'gzcat')):
            sys.exit('FAIL: crate archive tool discovery for ' + label + ': ' + result.stdout)
    tool_tree = tree if tool_tree is None else tool_tree
    query = subprocess.run([make, '-C', str(tool_tree / 'devel/cxxbridge'), 'MAKECONF=' + makeconf,
                            '-v', 'TOOLS_PLATFORM.tar', '-v', 'TOOLS_PLATFORM.gzcat',
                            '-v', 'TOOLS_PLATFORM.rm', '-v', 'TOOLS_PLATFORM.mkdir',
                            '-v', 'TOOLS_PLATFORM.cat', '-v', 'SH'],
                           capture_output=True, text=True, check=True)
    paths = query.stdout.splitlines()
    if len(paths) != 6 or not all(shlex.split(p) and Path(shlex.split(p)[0]).is_absolute()
                                  and Path(shlex.split(p)[0]).is_file() for p in paths):
        sys.exit('FAIL: selected tar/gzcat unavailable: ' + repr(paths))
    archive = work / 'sample.crate'
    with tarfile.open(archive, 'w:gz') as tar:
        payload = b'crate fixture\n'
        entry = tarfile.TarInfo('fixture/lib.rs')
        entry.size = len(payload)
        tar.addfile(entry, io.BytesIO(payload))
    target = work / 'crate-out'
    target.mkdir()
    bindir = Path(paths[0]).parent
    env = {'PATH': str(bindir), 'TAR': paths[0], 'GZCAT': paths[1],
           'RM': paths[2], 'MKDIR': paths[3], 'CAT': paths[4], 'TMPDIR': str(work)}
    result = subprocess.run([paths[5], str(tree / 'mk/extract/extract'), str(archive)],
                            cwd=target, env=env, capture_output=True, text=True)
    if result.returncode or (target / 'fixture/lib.rs').read_bytes() != b'crate fixture\n':
        sys.exit('FAIL: selected native tools could not extract crate: ' + result.stderr)


def main():
    if len(sys.argv) != 3:
        sys.exit('Usage: BMAKE=bmake extract-locale.py EXPORTED_PKGSRC MAKECONF')
    make = os.environ.get('BMAKE', 'bmake')
    tree, makeconf = Path(os.path.realpath(sys.argv[1])), os.path.realpath(sys.argv[2])
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        archive = work / 'fixture.tar'
        payload = work / 'payload.js'
        payload.write_text('// fixture\n')
        with tarfile.open(archive, 'w', format=tarfile.PAX_FORMAT) as tar:
            tar.add(payload, arcname=NAME)
        for index, recipe in enumerate(RECIPES):
            out = work / ('out-%d' % index)
            result = extract(make, tree, makeconf, recipe, archive, out)
            if result.returncode != 0 or not (out / NAME).is_file():
                print('FAIL: ' + recipe + ' cannot extract ' + NAME + ': ' + result.stderr.strip())
                return 1
        check_crate(make, tree, makeconf, work)
        old = extract(make, tree, makeconf, RECIPES[0], archive, work / 'out-c', ['EXTRACT_ENV='])
        if old.returncode == 0 or 'converted' not in old.stderr:
            print('FAIL: the C locale fixture does not reproduce the conversion error')
            return 1
    print('PASS: recipe extraction writes UTF-8 member names; the C locale alone fails')
    return 0


if __name__ == '__main__':
    sys.exit(main())
