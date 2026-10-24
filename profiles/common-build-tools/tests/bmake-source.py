#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the shared bmake vendor update without building or running bmake."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
MODE_OVERRIDES = {'make-bootstrap.sh.in': False}
sys.path.insert(0, str(ROOT / 'pkgsrc/lang/llvm/files'))
from sdk_source import load_sdk
sdk, arguments = load_sdk()
from emberbsd_sdk.stream import capture_streamed


def archive_files(path):
    result = {}
    with tarfile.open(path) as archive:
        for member in archive:
            name = Path(member.name)
            assert member.isfile() and name.parts[0] == 'bmake', member.name
            assert not name.is_absolute() and '..' not in name.parts, member.name
            relative = str(Path(*name.parts[1:]))
            assert relative and relative.casefold() not in {key.casefold() for key in result}, relative
            result[relative] = (archive.extractfile(member).read(), bool(member.mode & 0o111))
    return result


def tree_files(path):
    result = {}
    for file in path.rglob('*'):
        assert not file.is_symlink(), file
        if file.is_file():
            result[str(file.relative_to(path))] = (file.read_bytes(), bool(file.stat().st_mode & 0o111))
    return result


def keywords(data):
    return re.sub(rb'\$(?:Id|NetBSD|FreeBSD):[^$\r\n]*\$', b'$RCSID$', data)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'archive', 'old-archive', 'git', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    cli.add_argument('--version', required=True)
    args = cli.parse_args(arguments)
    assert re.fullmatch(r'\d{8}', args.version), 'Use a dated upstream release'
    work = args.work.absolute()
    work.mkdir()
    tree = work / 'pkgsrc'
    (tree / 'devel').mkdir(parents=True)
    shutil.copytree(args.pkgsrc / 'devel/bmake', tree / 'devel/bmake')
    patch = ROOT / ('profiles/common-build-tools/patches/pkgsrc-bmake-' + args.version + '.patch')
    if patch.exists():
        result = capture_streamed([str(args.git), '-C', str(tree), 'apply', '--check', str(patch)],
                                  timeout=30, stdout_limit=1024 * 1024)
        result = capture_streamed([str(args.git), '-C', str(tree), 'apply', str(patch)],
                                  timeout=30, stdout_limit=1024 * 1024)
        (work / 'patch.stdout').write_bytes(result.value)
        (work / 'patch.stderr').write_bytes(result.stderr)
    recipe = (tree / 'devel/bmake/Makefile').read_text()
    assert re.search(r'^PKGNAME=\s*bmake-' + re.escape(args.version) + r'$', recipe, re.M), 'Active bmake version differs'
    pins = {}
    for row in (ROOT / 'profiles/common-build-tools/sources.tsv').read_text().splitlines():
        if row and not row.startswith('#'):
            name, digest, url = row.split('\t')
            assert name not in pins, 'Ambiguous source pin: ' + name
            pins[name] = (digest, url)
    for file in (args.archive, args.old_archive, patch):
        assert hashlib.sha256(file.read_bytes()).hexdigest() == pins[file.name][0], file.name
    source = archive_files(args.archive)
    actual = tree_files(tree / 'devel/bmake/files')
    assert actual.keys() == source.keys(), (sorted(source.keys() - actual.keys()), sorted(actual.keys() - source.keys()))
    for name in source:
        data, executable = source[name]
        assert actual[name] == (data, MODE_OVERRIDES.get(name, executable)), name
    assert source['VERSION'][0].decode().strip().endswith('_MAKE_VERSION=' + args.version)
    for name in ('configure', 'configure.in', 'make-bootstrap.sh.in', 'boot-strap', 'LICENSE',
                 'mk/sys.mk', 'unit-tests/Makefile', 'unit-tests/Makefile.config.in'):
        assert name in source, name
    baseline = tree_files(args.pkgsrc / 'devel/bmake/files')
    previous = archive_files(args.old_archive)
    assert baseline.keys() == previous.keys(), 'Previous vendor roster differs'
    expanded = 0
    mode_changes = {}
    for name in previous:
        assert keywords(baseline[name][0]) == keywords(previous[name][0]), 'Unpreserved pkgsrc delta: ' + name
        if baseline[name][1] != previous[name][1]:
            mode_changes[name] = baseline[name][1]
        expanded += baseline[name][0] != previous[name][0]
    assert mode_changes == MODE_OVERRIDES, mode_changes
    old_recipe = (args.pkgsrc / 'devel/bmake/Makefile').read_text()
    old_version = re.search(r'^PKGNAME=\s*bmake-(\d+)$', old_recipe, re.M).group(1)
    assert old_recipe.replace('bmake-' + old_version, 'bmake-' + args.version) == recipe
    assert '${CP} -R ${FILESDIR} ${WRKSRC}' in recipe and '${WRKDIR}/bmake' in recipe
    bootstrap = (args.pkgsrc / 'bootstrap/bootstrap').read_text()
    assert 'copy_src $pkgsrcdir/devel/bmake/files bmake' in bootstrap
    assert '$shprog make-bootstrap.sh' in bootstrap
    export = (ROOT / 'pkgsrc/export.conf').read_text()
    assert export.count('git-apply\tprofiles/common-build-tools/patches/' + patch.name + '\t') == 1
    summary = {'version': args.version, 'source_files': len(source), 'previous_files': len(previous),
               'previous_keyword_only_files': expanded, 'semantic_local_changes': 0, 'preserved_mode_overrides': mode_changes,
               'added_paths': sorted(source.keys() - previous.keys()),
               'removed_paths': sorted(previous.keys() - source.keys()),
               'tests': sum(name.startswith('unit-tests/') for name in source),
               'makefiles': sum(name.startswith('mk/') for name in source),
               'source_sha256': pins[args.archive.name][0]}
    (work / 'result.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('PASS: current bmake version, archive/import hashes and complete source payload')
    print('PASS: every previous pkgsrc file matches its release except expanded RCS keywords')
    print('PASS: ordinary recipe and bootstrap retain one source owner and payload layout')
    print('Files:', len(source), 'tests:', summary['tests'], 'makefiles:', summary['makefiles'])
    print('SCOPE: source only; no configure, compiler, new bmake or prefix writer ran')


if __name__ == '__main__':
    main()
