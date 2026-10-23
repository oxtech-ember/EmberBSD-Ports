#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). No third-party Python modules are required.
"""Check release bytes and execute the actual generated platform branches."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile


def run(argv, cwd=None, data=None):
    result = subprocess.run(argv, cwd=cwd, input=data, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(f'{argv!r}: {result.returncode}\n{result.stderr}')
    return result.stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def branches(source):
    # Execute the complete generated TEA platform branch, including its
    # AIX version rule and the build host's Debian marker rule.
    start = '\tif test "${TEA_PLATFORM}" = "windows" ; then\n'
    end = '\t\t    tcl_cv_sys_version=NetBSD-Debian\n\t\tfi\n\t    fi\n\tfi'
    found = []
    offset = 0
    while (offset := source.find(start, offset)) >= 0:
        limit = source.index(end, offset) + len(end)
        found.append(source[offset:limit])
        offset = limit
    if not found:
        raise RuntimeError('No generated platform branch')
    return found


def select(block, name, release, target=None, windows=False):
    # Function-local uname supplies a controlled build host. The branch is
    # unchanged source text. No target executable runs in this check.
    prefix = ('exec 5>/dev/null 6>/dev/null\n'
              f'TEA_PLATFORM={"windows" if windows else "unix"}\n'
              f'uname() {{ case "$1" in -s) echo {name};; '
              f'-r) echo {release};; -v) echo 7;; *) return 2;; esac; }}\n')
    if target:
        prefix += f'EMBERBSD_TCL_SYSTEM_NAME={target[0]}\n'
        prefix += f'EMBERBSD_TCL_SYSTEM_RELEASE={target[1]}\n'
    else:
        prefix += 'unset EMBERBSD_TCL_SYSTEM_NAME EMBERBSD_TCL_SYSTEM_RELEASE\n'
    return run(['sh'], data=prefix + block + '\nprintf "%s\\n" "$tcl_cv_sys_version"\n').strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tcl_archive', type=Path)
    parser.add_argument('tk_archive', type=Path)
    parser.add_argument('new_output', type=Path)
    args = parser.parse_args()
    out = args.new_output.resolve()
    if out.exists():
        parser.error('Output must not exist')
    ports = Path(__file__).resolve().parents[3]
    specs = [
        ('tcl', args.tcl_archive, '536c45543f64d6eb11832d97ba3494aacff046fbc5040273bd55258d0e448ff1',
         ports / 'pkgsrc/lang/tcl', 19, 9),
        ('tk', args.tk_archive, '772ce7a97c07c2db4c957c93af7ab4dff4bd3037772836b6afbcd0974023b3d6',
         ports / 'pkgsrc/x11/tk', 3, 1),
    ]
    for _, archive, sha, _, _, _ in specs:
        if digest(archive) != sha:
            raise RuntimeError(f'Archive SHA256 differs: {archive}')
    out.mkdir(parents=True)
    records = []
    for name, archive, sha, recipe, count, scripts in specs:
        original = out / 'upstream' / name
        original.mkdir(parents=True)
        with tarfile.open(archive) as source:
            source.extractall(original, filter='data')
        original = original / f'{name}9.1.0'
        patched = out / 'patched' / f'{name}9.1.0'
        shutil.copytree(original, patched)
        patch = recipe / 'patches/patch-target-platform'
        patch_text = patch.read_text()
        patch_sha1 = hashlib.sha1(''.join(
            line for line in patch_text.splitlines(keepends=True)
            if '$NetBSD' not in line).encode()).hexdigest()
        if f'SHA1 (patch-target-platform) = {patch_sha1}' not in (recipe / 'distinfo').read_text():
            raise RuntimeError('Patch distinfo differs')
        (out / f'{name}-patch.log').write_text(run(
            ['patch', '-f', '-p0', '-F', '0', '-i', str(patch)], cwd=patched))
        paths = re.findall(r'^\+\+\+ ([^\t\n]+)', patch_text, re.MULTILINE)
        if len(paths) != count:
            raise RuntimeError(f'Wrong patch inventory: {name}: {len(paths)}')
        files = []
        for rel in paths:
            before = (original / rel).read_text()
            after = (patched / rel).read_text()
            expected = before.replace('`uname -s`', '${EMBERBSD_TCL_SYSTEM_NAME:-`uname -s`}')
            expected = expected.replace('`uname -r`', '${EMBERBSD_TCL_SYSTEM_RELEASE:-`uname -r`}')
            old = 'if test "${EMBERBSD_TCL_SYSTEM_NAME:-`uname -s`}" = "NetBSD" -a -f /etc/debian_version ; then'
            new = 'if test -z "${EMBERBSD_TCL_SYSTEM_NAME-}" && test "${EMBERBSD_TCL_SYSTEM_NAME:-`uname -s`}" = "NetBSD" -a -f /etc/debian_version ; then'
            if after != expected.replace(old, new):
                raise RuntimeError(f'Unexpected source change: {rel}')
            files.append({'path': rel, 'upstream_sha256': digest(original / rel),
                          'patched_sha256': digest(patched / rel)})
        generated = [rel for rel in paths if Path(rel).name == 'configure']
        if len(generated) != scripts:
            raise RuntimeError('Wrong generated script count')
        checks = []
        for rel in generated:
            run(['sh', '-n', str(patched / rel)])
            old = branches((original / rel).read_text())
            new = branches((patched / rel).read_text())
            if len(old) != len(new):
                raise RuntimeError('Generated platform branch count changed')
            for ordinal, (baseline, repaired) in enumerate(zip(old, new), 1):
                cases = [
                    ('native-linux', 'Linux', '6.9', None, False, 'Linux-6.9', 'Linux-6.9'),
                    ('native-darwin', 'Darwin', '25.0', None, False, 'Darwin-25.0', 'Darwin-25.0'),
                    ('linux-to-netbsd', 'Linux', '6.9', ('NetBSD', '11.0'), False, 'Linux-6.9', 'NetBSD-11.0'),
                    ('darwin-to-netbsd', 'Darwin', '25.0', ('NetBSD', '11.0'), False, 'Darwin-25.0', 'NetBSD-11.0'),
                    ('windows', 'Linux', '6.9', ('NetBSD', '11.0'), True, 'windows', 'windows'),
                ]
                if Path('/etc/debian_version').is_file():
                    cases.append(('debian-marker', 'NetBSD', '6.9', ('NetBSD', '11.0'), False, 'NetBSD-Debian', 'NetBSD-11.0'))
                for case, host, release, target, windows, want_old, want_new in cases:
                    actual_old = select(baseline, host, release, target, windows)
                    actual_new = select(repaired, host, release, target, windows)
                    if (actual_old, actual_new) != (want_old, want_new):
                        raise RuntimeError(f'{name}/{rel}/{case}: {actual_old!r}, {actual_new!r}')
                    checks.append({'script': rel, 'branch': ordinal, 'case': case,
                                   'upstream': actual_old, 'patched': actual_new})
        manual = None
        if name == 'tcl':
            sqlite_patch = recipe / 'patches/patch-sqlite-system-extern'
            run(['patch', '-f', '-p0', '-F', '0', '-i', str(sqlite_patch)], cwd=patched)
            sqlite = patched / 'pkgs/sqlite3.53.4'
            if 'PKG_CFLAGS\t= @PKG_CFLAGS@ -DSQLITE_EXTERN=' in (sqlite / 'Makefile.in').read_text():
                raise RuntimeError('System SQLite still overrides extern declarations')
            if 'TEA_ADD_CFLAGS([-DSQLITE_API=MODULE_SCOPE -DSQLITE_EXTERN=])' not in (sqlite / 'configure.ac').read_text():
                raise RuntimeError('Bundled SQLite extern flags changed')
            if 'PKG_CFLAGS="$PKG_CFLAGS -DSQLITE_API=MODULE_SCOPE -DSQLITE_EXTERN="' not in (sqlite / 'configure').read_text():
                raise RuntimeError('Generated SQLite extern flags differ')
            run(['sh', '-n', str(sqlite / 'configure')])
            doc_patch = recipe / 'patches/patch-doc_Encoding.3'
            run(['patch', '-f', '-p0', '-F', '0', '-i', str(doc_patch)], cwd=patched)
            destinations = []
            for label, tree in [('upstream', original), ('patched', patched)]:
                destination = out / f'{label}-encoding-manual'
                destination.mkdir()
                run(['sh', str(tree / 'unix/installManPage'),
                     str(tree / 'doc/Encoding.3'), str(destination)])
                destinations.append({path.name for path in destination.iterdir()})
            combined = 'Tcl_ExternalToUtfTcl_ExternalToUtfEx.3'
            aliases = {'Tcl_ExternalToUtf.3', 'Tcl_ExternalToUtfEx.3'}
            if (combined not in destinations[0] or aliases & destinations[0]
                    or combined in destinations[1] or not aliases <= destinations[1]):
                raise RuntimeError('Encoding manual alias regression')
            manual = {'upstream_aliases': sorted(destinations[0]),
                      'patched_aliases': sorted(destinations[1]),
                      'patch_sha256': digest(doc_patch)}
        records.append({'source': name, 'archive_sha256': sha, 'patch_sha256': digest(patch),
                        'files': files, 'generated_scripts': scripts, 'cases': checks,
                        'encoding_manual': manual})
    result = {'status': 'PASS', 'scope': 'Verified release bytes, zero-fuzz patching, maintained/generated deltas, shell syntax and actual generated platform branches. Full configure, compilation, package and runtime are separate checks.',
              'sources': records}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'PASS: {sum(len(r["files"]) for r in records)} files; '
          f'{sum(r["generated_scripts"] for r in records)} scripts; '
          f'{sum(len(r["cases"]) for r in records)} causal branch cases')


if __name__ == '__main__':
    main()
