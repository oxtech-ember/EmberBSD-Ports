# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise pkgsrc patch.mk failure behavior with real bmake and patch tools."""

import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
OVERLAY = ROOT / 'profiles/common-build-tools/patches/pkgsrc-patch-fail-fast.patch'
GOOD = b'--- input.txt\n+++ input.txt\n@@ -1 +1 @@\n-old\n+new\n'
BAD = b'--- a/tests/missing.c\n+++ b/tests/missing.c\n@@ -1 +1 @@\n-old\n+new\n'


def run(command, *, data=None, timeout=5, stdout=subprocess.PIPE, timeout_is_result=False):
    process = subprocess.Popen(command, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                               stdout=stdout, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        output, _ = process.communicate(data, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
        if timeout_is_result:
            return None
        raise AssertionError(f"command prompted or stalled: {command[0]}") from error
    return subprocess.CompletedProcess(command, process.returncode, output)


def make_view(root, pkgsrc, gpatch, *, overlay_applied):
    mk = root / 'mk'
    mk.mkdir()
    for entry in (pkgsrc / 'mk').iterdir():
        if entry.name != 'patch':
            (mk / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    patch_mk = mk / 'patch'
    patch_mk.mkdir()
    for name in ('bsd.patch-vars.mk', 'bsd.patch.mk', 'patch.mk'):
        shutil.copy2(pkgsrc / 'mk/patch' / name, patch_mk / name)
    forward_ok = run([gpatch, '--dry-run', '--batch', '--forward', '-d', str(root),
                      '-p1', '-F0'], data=OVERLAY.read_bytes()).returncode == 0
    reverse_ok = run([gpatch, '--dry-run', '--batch', '--reverse', '--force',
                      '-d', str(root), '-p1', '-F0'],
                     data=OVERLAY.read_bytes()).returncode == 0
    if forward_ok == reverse_ok:
        raise AssertionError('pkgsrc patch.mk is neither pristine nor patched by this overlay')
    currently_applied = reverse_ok
    if currently_applied != overlay_applied:
        direction = ['-R'] if currently_applied else []
        result = run([gpatch, '-f', '-E', '-d', str(root), *direction,
                      '-p1', '-F0', '-V', 'none'], data=OVERLAY.read_bytes())
        if result.returncode:
            raise AssertionError(result.stdout.decode(errors='replace'))


def package_fixture(root, patch_tool, cat, shell):
    package = root / 'devel/test'
    patch_dir = package / 'patches'
    source = root / 'work/src'
    work = root / 'work'
    dist = work / 'dist'
    patch_dir.mkdir(parents=True)
    source.mkdir(parents=True)
    dist.mkdir()
    makefile = f'''.SHELL: name=sh path={shell}
SHELL=\t{shell}
WRKSRC=\t{source}
WRKDIR=\t{work}
PKGNAME=\ttest-1.0
PKGPATH=\tdevel/test
PATCHDIR=\t${{.CURDIR}}/patches
DISTINFO_FILE=\t${{.CURDIR}}/distinfo
_DISTDIR=\t{dist}
PATCH=\t{patch_tool}
PATCH_STRIP=\t-p0
PATCH_FUZZ_FACTOR=\t-F0
PATCH_DEBUG=\tyes
PATCHFILES=\tdist.patch
PATCH_DIST_ARGS.dist.patch=\t-d ${{WRKSRC}} -E -p0
PATCH_DIST_CAT.dist.patch=\t${{CAT}} ${{_DISTDIR}}/dist.patch
CAT=\t{cat}
RUN=\t@
STEP_MSG=\techo
ECHO_MSG=\techo
ECHO=\techo
TEST=\ttest
PKG_OPTIONS=\nLOCALPATCHES=\nERROR_MSG=\techo
.include "../../mk/patch/patch.mk"
'''
    (package / 'Makefile').write_text(makefile)
    return package, patch_dir, source, dist


def scenario(bmake, package, patch_dir, source, dist, patch_tool,
             name, payload, content, target, expected_status, expected_content):
    for old in patch_dir.iterdir():
        old.unlink()
    (source / 'input.txt').write_bytes(content)
    if target == 'do-pkgsrc-patch':
        (patch_dir / 'patch-local-case').write_bytes(payload)
    else:
        (dist / 'dist.patch').write_bytes(payload)
    result = run([bmake, '-C', str(package), target], stdout=subprocess.DEVNULL)
    actual = (source / 'input.txt').read_bytes() if (source / 'input.txt').exists() else None
    if result.returncode != expected_status or actual != expected_content:
        raise AssertionError(
            f'{patch_tool} {name}: exit={result.returncode}, content={actual!r}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True)
    parser.add_argument('--pkgsrc', required=True,
                        help='pkgsrc tree with the selected mk infrastructure')
    parser.add_argument('--gpatch', required=True,
                        help='selected gpatch used to apply infrastructure overlays')
    parser.add_argument('--cat', required=True,
                        help='selected SDK cat executable used by distribution patches')
    parser.add_argument('--shell', required=True,
                        help='selected SDK shell used by pkgsrc make recipes')
    parser.add_argument('--patch-tool', action='append', required=True,
                        help='patch executable to exercise; repeat for each supported tool')
    args = parser.parse_args()
    pkgsrc = Path(args.pkgsrc).resolve()
    if not (pkgsrc / 'mk/patch/patch.mk').is_file():
        parser.error('--pkgsrc must contain mk/patch/patch.mk')
    if not Path(args.cat).is_file() or not Path(args.cat).stat().st_mode & 0o111:
        parser.error('--cat must be an executable selected SDK tool')
    if not Path(args.shell).is_file() or not Path(args.shell).stat().st_mode & 0o111:
        parser.error('--shell must be an executable selected SDK tool')

    # Demonstrate the regression without retaining the unbounded prompt output.
    with tempfile.TemporaryDirectory(prefix='pkgsrc-patch-before-') as directory:
        root = Path(directory)
        make_view(root, pkgsrc, args.gpatch, overlay_applied=False)
        package, patches, source, dist = package_fixture(
            root, args.patch_tool[0], args.cat, args.shell)
        (source / 'input.txt').write_text('old\n')
        (patches / 'patch-local-case').write_bytes(BAD)
        result = run([args.bmake, '-C', str(package), 'do-pkgsrc-patch'],
                     stdout=subprocess.DEVNULL, timeout=1, timeout_is_result=True)
        if result is not None:
            raise AssertionError('unpatched wrong-path case did not prompt as expected')

    for tool in args.patch_tool:
        with tempfile.TemporaryDirectory(prefix='pkgsrc-patch-after-') as directory:
            root = Path(directory)
            make_view(root, pkgsrc, args.gpatch, overlay_applied=True)
            package, patches, source, dist = package_fixture(root, tool, args.cat, args.shell)
            scenario(args.bmake, package, patches, source, dist, tool,
                     'valid', GOOD, b'old\n', 'do-pkgsrc-patch', 0, b'new\n')
            scenario(args.bmake, package, patches, source, dist, tool,
                     'wrong-path', BAD, b'old\n', 'do-pkgsrc-patch', 1, b'old\n')
            scenario(args.bmake, package, patches, source, dist, tool,
                     'already-applied', GOOD, b'new\n', 'do-pkgsrc-patch', 1, b'new\n')
            scenario(args.bmake, package, patches, source, dist, tool,
                     'distribution-override', GOOD, b'new\n',
                     'do-distribution-patch', 1, b'new\n')
        print(f'{Path(tool).name}: valid, wrong-path, already-applied and per-file override passed')

if __name__ == '__main__':
    main()
