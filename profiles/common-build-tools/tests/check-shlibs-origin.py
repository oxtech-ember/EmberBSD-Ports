#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise target $ORIGIN resolution with real ELF and pkgsrc checker."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
for name in ('pkgsrc', 'cc', 'ld', 'readelf', 'awk', 'patch', 'sysroot', 'work',
             'sdk-source', 'host-prefix', 'python', 'shell', 'lock-root', 'link-context'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
for name, value in vars(args).items():
    if not value.is_absolute():
        raise ValueError(name + ' must be absolute')
if args.work.exists():
    raise ValueError('work directory must be new')
args.work.mkdir(parents=True)
root = Path(__file__).resolve().parents[3]
checker = args.work / 'mk/check/check-shlibs-elf.awk'
checker.parent.mkdir(parents=True)
checker.write_bytes((args.pkgsrc / 'mk/check/check-shlibs-elf.awk').read_bytes())
patch = root / 'profiles/common-build-tools/patches/pkgsrc-check-shlibs-origin.patch'
env = {'PATH': str(args.host_prefix / 'bin') + ':' + str(args.host_prefix / 'gnu/bin'), 'HOME': str(args.work),
       'TMPDIR': str(args.work), 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}
subprocess.run([str(args.patch), '-p1', '-i', str(patch)], cwd=args.work, env=env, check=True)
stage = args.work / 'stage space'
cross = args.work / 'cross space'
libdir = stage / 'usr/pkg/lib/electron44'
libdir.mkdir(parents=True)
crosslib = cross / 'usr/pkg/lib/external'
crosslib.mkdir(parents=True)
source = args.work / 'dependency.c'
source.write_text('int diagnostic_dependency(void) { return 7; }\n')
consumer = args.work / 'consumer.c'
consumer.write_text('extern int diagnostic_dependency(void); int use(void) { return diagnostic_dependency(); }\n')
launcher = [str(args.python), str(args.sdk_source / 'scripts/link-launcher.py'),
            '--lock-root', str(args.lock_root), '--context', str(args.link_context), '--']
cc = [str(args.cc), '--target=x86_64-unknown-netbsd', '--sysroot=' + str(args.sysroot),
      '--ld-path=' + str(args.ld), '-shared', '-nostdlib', '-fPIC']

def link(arguments):
    subprocess.run(launcher + cc + arguments, cwd=args.work, env=env, check=True)

link([str(source), '-Wl,-soname,libdiagnostic.so.1', '-o', str(libdir / 'libdiagnostic.so.1')])
(libdir / 'libdiagnostic.so').symlink_to('libdiagnostic.so.1')

def build(name, rpath, output=None):
    output = output or libdir / name
    link([str(consumer), '-L' + str(libdir), '-ldiagnostic', '-Wl,-rpath,' + rpath,
          '-o', str(output)])
    return output

same = build('same.so', '$ORIGIN')
braced = build('braced.so', '${ORIGIN}')
parent_dir = libdir / 'sub'
parent_dir.mkdir()
parent = build('parent.so', '$ORIGIN/..', parent_dir / 'parent.so')
unknown = build('unknown.so', '$UNKNOWN')
relative_rpath = build('relative.so', 'relative/path')
missing = build('missing.so', '$ORIGIN/nonexistent')

# Run old control as well: it must fail to resolve the real origin dependency.
old_checker = args.pkgsrc / 'mk/check/check-shlibs-elf.awk'
pkg_info = args.work / 'pkg-info'
pkg_info.write_text('#!' + str(args.shell) + '\nprintf "diagnostic-1.0\\n"\n')
pkg_info.chmod(0o755)
depends = args.work / 'depends'
depends.write_text('')
requires_file = args.work / 'requires'

def check(path, *, expected=None, metadata=True, checker_path=checker, staged=True,
          toxic='', extra='', dependency='', prefix='/usr/pkg'):
    if requires_file.exists():
        requires_file.unlink()
    depends.write_text(dependency)
    runenv = dict(env, DESTDIR=str(stage) if staged else '',
                  CROSS_DESTDIR=str(cross) if staged else '', PREFIX=prefix, READELF=str(args.readelf),
                  WRKDIR=str(args.work / 'build'), PLATFORM_RPATH='',
                  PKG_INFO_CMD=str(pkg_info), DEPENDS_FILE=str(depends),
                  CHECK_SHLIBS_TOXIC=toxic, CHECK_WRKREF_EXTRA_DIRS=extra,
                  REQUIRES_FILE=str(requires_file) if metadata else '')
    result = subprocess.run([str(args.awk), '-f', str(checker_path)], input=str(path) + '\n',
                            text=True, capture_output=True, env=runenv, check=True,
                            cwd=stage / 'usr/pkg')
    if expected is None:
        assert result.stdout == '', result.stdout
    else:
        assert expected in result.stdout, result.stdout
    return requires_file.read_text().splitlines() if requires_file.exists() else []

check(same, expected='missing library: libdiagnostic.so.1', checker_path=old_checker)
for path in (same, braced, parent):
    required = check(path)
    assert '/usr/pkg/lib/electron44/libdiagnostic.so.1' in required, required
    check(path, metadata=False)
check(unknown, expected='unsupported or relative rpath')
check(relative_rpath, expected='unsupported or relative rpath')
check(missing, expected='missing library: libdiagnostic.so.1')

# Staged aliases resolve the object before determining its target $ORIGIN.
bin_dir = stage / 'usr/pkg/bin'
bin_dir.mkdir(parents=True)
relative = bin_dir / 'relative'
relative.symlink_to('../lib/electron44/same.so')
absolute = bin_dir / 'absolute'
absolute.symlink_to('/usr/pkg/lib/electron44/same.so')
for alias in (relative, absolute):
    assert '/usr/pkg/lib/electron44/libdiagnostic.so.1' in check(alias)
    check(alias, metadata=False)

# Normal check-shlibs.mk supplies PREFIX-relative names and runs in DESTDIR/PREFIX.
for name in ('lib/electron44/same.so', 'bin/relative', 'bin/absolute'):
    assert '/usr/pkg/lib/electron44/libdiagnostic.so.1' in check(name)
    check(name, metadata=False)
check('lib/electron44/same.so', expected='relative object requires an absolute safe PREFIX',
      prefix='')
check('lib/electron44/same.so', expected='relative object requires an absolute safe PREFIX',
      prefix='relative')
check('../outside.so', expected='relative object requires an absolute safe PREFIX')
# Native relative names use the explicitly declared absolute PREFIX too.
check('lib/electron44/same.so', metadata=False, staged=False,
      prefix=str(stage / 'usr/pkg'))

# Native absolute origin is meaningful without DESTDIR; never rely on cwd.
check(same, metadata=False, staged=False)

# Resolve a symlink before /..: logical link/../lib is not lexical normalization.
real = stage / 'usr/pkg/other/sub'
real.mkdir(parents=True)
(real.parent / 'lib').mkdir()
(real.parent / 'lib/libdiagnostic.so.1').symlink_to('/usr/pkg/lib/electron44/libdiagnostic.so.1')
(stage / 'usr/pkg/link').symlink_to('other/sub')
linked_parent = build('linked-parent.so', '/usr/pkg/link/../lib')
assert '/usr/pkg/lib/electron44/libdiagnostic.so.1' in check(linked_parent)

# External resolution still checks runtime dependency, toxic and workref paths.
external = crosslib / 'libdiagnostic.so.1'
external.write_bytes((libdir / 'libdiagnostic.so.1').read_bytes())
external_consumer = build('external.so', '/usr/pkg/lib/external')
check(external_consumer, expected='not a runtime dependency',
      dependency='build ignored diagnostic-1.0\n')
check(external_consumer, expected='matches toxic', toxic='/usr/pkg/lib/external/.*',
      dependency='full ignored diagnostic-1.0\n')
check(external_consumer, expected='relative to CHECK_WRKREF_EXTRA_DIRS',
      extra='/usr/pkg/lib/external', dependency='full ignored diagnostic-1.0\n')

# A real host file referenced by an absolute staged symlink must not satisfy target resolution.
host_only = args.work / 'host-only.so'
host_only.write_bytes((libdir / 'libdiagnostic.so.1').read_bytes())
(libdir / 'libdiagnostic.so.1').unlink()
(libdir / 'libdiagnostic.so.1').symlink_to(host_only)
check(same, expected='missing library: libdiagnostic.so.1')
print('PASS: real ELF origin paths, aliases, refusal and existing dependency checks')
