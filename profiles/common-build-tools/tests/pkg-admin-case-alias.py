#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the actual pkg_admin and pkg_tools lifecycle on two existing filesystems."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tarfile
import tempfile

parser = argparse.ArgumentParser()
for name in ('prefix', 'candidate', 'baseline', 'archive', 'case-sensitive-parent'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
prefix = args.prefix.resolve()
env = {'PATH': f'{prefix}/bin:{prefix}/gnu/bin:{prefix}/sbin', 'LC_ALL': 'C'}
def run(argv):
    return subprocess.run([str(a) for a in argv], env=env, capture_output=True, text=True, timeout=120)
with tempfile.TemporaryDirectory(prefix='pkgcheck-folded-') as temp:
    root = Path(temp) / 'root'
    root.mkdir()
    probe = root / 'Probe'
    probe.write_bytes(b'x')
    assert (root / 'probe').exists(), 'temporary filesystem must fold case'
    probe.unlink()
    dbarg = Path('/usr/pkg/pkgdb')
    package = 'openssl-4.1.0nb3'
    common = ['-P', root, '-K', dbarg]
    install = [prefix/'sbin/pkg_add', '-f', '-I', '-K', dbarg, '-P', root,
               '-p', '/usr/pkg', args.archive]
    result = run(install)
    assert result.returncode == 0, result.stderr
    # pkg_add applies -P to -K; pkg_admin reads the resulting physical path.
    physical_db = root / 'usr/pkg/pkgdb'
    check = ['-P', root, '-K', physical_db, 'check', package]
    old = run([args.baseline, *check])
    assert old.returncode and "can't readlink" in old.stderr
    new = run([args.candidate, *check])
    assert not new.returncode, new.stderr
    target = root/'usr/pkg/man/man3/OSSL_trace_enabled.3'
    data = target.read_bytes()
    target.write_bytes(data + b'corruption')
    bad = run([args.candidate, *check])
    assert bad.returncode and 'fails MD5 checksum' in bad.stderr
    target.write_bytes(data)
    deleted = run([prefix/'sbin/pkg_delete', '-f', *common, package])
    assert not deleted.returncode, deleted.stderr
    assert not target.exists() and not (physical_db / package).exists()
    assert run(install).returncode == 0
    assert run([args.candidate, *check]).returncode == 0
with tempfile.TemporaryDirectory(prefix='pkgcheck-exact-', dir=args.case_sensitive_parent) as temp:
    root = Path(temp)
    directory = root/'files'
    directory.mkdir()
    target = directory/'name'
    alias = directory/'NAME'
    target.write_bytes(b'payload\n')
    assert not alias.exists(), 'case-sensitive fixture parent required'
    db = root/'pkgdb/demo-1'
    db.mkdir(parents=True)
    digest = hashlib.md5(target.read_bytes()).hexdigest()
    (db/'+CONTENTS').write_text(f'@name demo-1\n@cwd {directory}\nNAME\n'
        f'@comment Symlink:name\nname\n@comment MD5:{digest}\n')
    check = [args.candidate, '-K', db.parent, 'check', 'demo-1']
    alias.hardlink_to(target)
    assert run(check).returncode != 0
    alias.unlink()
    alias.write_bytes(target.read_bytes())
    assert run(check).returncode != 0
    alias.unlink()
    alias.symlink_to('name')
    assert run(check).returncode == 0
    with tarfile.open(args.archive, 'r:*') as archive:
        names = ('man/man3/OSSL_TRACE_ENABLED.3', 'man/man3/OSSL_trace_enabled.3')
        for name in names:
            archive.extract(archive.getmember(name), root, filter='data')
    assert (root/names[0]).is_symlink() and (root/names[1]).is_file()
print('PASS: installed alias, corruption, pkg lifecycle and case-sensitive transfer')
