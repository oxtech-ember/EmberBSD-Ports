#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the actual pkgsrc scanner selector with installed native tools."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'host-prefix', 'sdk-source', 'utility-path', 'distdir', 'work'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if not args.work.is_absolute() or args.work.exists():
        parser.error('use a new absolute work directory')
    prefix = args.host_prefix.resolve()
    if not Path(sys.executable).resolve().is_relative_to(prefix):
        parser.error('run with the selected native prefix Python')
    args.work.mkdir()
    owner = Path(__file__).resolve().parents[3]
    view = args.work/'pkgsrc'
    view.mkdir()
    (view/'devel').mkdir()
    for source, destination, excluded in ((args.pkgsrc, view, {'devel'}),
            (args.pkgsrc/'devel', view/'devel', {'wayland', 'wayland-protocols'})):
        for item in source.iterdir():
            if item.name not in excluded:
                (destination/item.name).symlink_to(item.resolve(), target_is_directory=item.is_dir())
    for name in ('wayland', 'wayland-protocols'):
        shutil.copytree(owner/'pkgsrc/devel'/name, view/'devel'/name)
    recipe = view/'devel/wayland-protocols'
    # pkgsrc's generic cross metadata requires stddef.h to exist even for
    # fetch. This deliberately unusable header satisfies that shape only;
    # any accidental target compilation must fail, not qualify a sysroot.
    cross_root = args.work/'metadata-only-cross-root'
    (cross_root/'usr/include').mkdir(parents=True)
    (cross_root/'usr/include/stddef.h').write_text('#error metadata fixture must not compile\n')
    makeconf = args.work/'cross.mk.conf'
    makeconf.write_text('LOCALBASE='+str(prefix)+'\nPYTHON_VERSION_DEFAULT=315\nPKGSRC_COMPILER=clang\n')
    environment = dict(os.environ, PATH=str(args.utility_path), TMPDIR=str(args.work),
                       PKG_CONFIG_PATH='/not-the-native-prefix', PKG_CONFIG_SYSROOT_DIR='/target')
    environment.pop('EMBERBSD_DARWIN_BOOTSTRAP', None)
    base = [str(prefix/'bin/bmake'), '-m', str(prefix/'share/mk'),
            'SHELL='+str(prefix/'bin/mksh'), 'MAKECONF='+str(makeconf),
            'WRKOBJDIR='+str(args.work/'objects'), 'USE_CROSS_COMPILE=yes',
            'CROSS_DESTDIR='+str(cross_root), 'CROSS_OPSYS=NetBSD', 'CROSS_OS_VERSION=11.0', 'CROSS_MACHINE_ARCH=x86_64',
            'CROSS_OPSYS_VERSION=110000', 'CROSS_LOWER_OPSYS=netbsd',
            'CROSS_LOWER_OPSYS_VERSUFFIX=', 'CROSS_LOWER_VARIANT_VERSION=',
            'CROSS_LOWER_VENDOR=', 'CROSS_LOWER_OS_VARIANT=', 'CROSS_OBJECT_FMT=ELF',
            'EMBERBSD_SDK_SOURCE='+str(args.sdk_source),
            'PKG_TOOLS_BIN='+str(prefix/'sbin'), 'NATIVE_PKG_TOOLS_BIN='+str(prefix/'sbin'),
            'DISTDIR='+str(args.distdir)]
    cases = {}

    def run(name, selected=prefix, extra=(), success=True, scanner=None, cwd=recipe):
        command = [*base, 'TOOLBASE='+str(selected), 'TOOL_PYTHONBIN='+str(selected/'bin/python3.15'),
                   'EMBERBSD_WAYLAND_SCANNER='+str(scanner or selected/'bin/wayland-scanner'), *extra]
        result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True)
        output = result.stdout+result.stderr
        (args.work/(name+'.log')).write_text(shlex.join(command)+'\n'+output)
        assert (result.returncode == 0) == success, name+'\n'+output
        if not success:
            expected = {
                'missing-python': 'requires the native Python tool',
                'empty-python': 'requires the native Python tool',
                'relative-path': 'differs from the native Ports prefix',
                'outside-prefix': 'differs from the native Ports prefix',
                'missing-sdk': 'absent-sdk',
                'old-version': 'must report exactly 1.26.0',
                'failed-version': 'command failed (1)',
                'extra-output': 'must report exactly 1.26.0',
                'nonexecutable': 'not executable',
                'absent-scanner': 'missing native tool',
                'escaping-symlink': 'escapes host prefix',
                'external-interpreter': 'escapes host prefix',
                'foreign-cpu': 'expected a native executable',
                'missing-pc': 'test -s ',
            }.get(name, 'native metadata disagrees')
            assert expected in output, name+' failed for a different reason\n'+output
        cases[name] = 'passed' if success else 'refused'
        return output

    tools = run('source-tool-selection', extra=('-V', '${NATIVE_PKG_INFO_CMD}', '-V', '${PKGTOOLS_VERSION}'))
    assert str(prefix/'sbin/pkg_info') in tools and '20010302' not in tools
    run('source-fetch-checksum-without-generator', scanner=args.work/'absent-scanner',
        extra=('EMBERBSD_SDK_SOURCE='+str(args.work/'absent-sdk'),
               'TOOL_PYTHONBIN='+str(args.work/'absent-python'), 'fetch', 'checksum'),
        cwd=view/'devel/wayland')
    run('ordinary-prefix', extra=('emberbsd-scanner-check',))
    for name, value in (('missing-python', str(args.work/'absent-python')), ('empty-python', '')):
        output = run(name, extra=('TOOL_PYTHONBIN='+value, 'emberbsd-scanner-check'), success=False)
        assert '(ignored)' not in output
    # The real prefix has no legacy standalone-builder receipt. Its installed
    # executable and .pc metadata are sufficient, even with poisoned target env.
    assert not (prefix.parent/'installed.sha256').exists()
    native = args.work/'scanner-native.ini'
    run('native-file', extra=('_EMBERBSD_SCANNER_NATIVE='+str(native), str(native)))
    text = native.read_text()
    assert 'PKG_CONFIG_SYSROOT_DIR=' in text and 'pkg_config_path = []' in text
    assert str(prefix/'lib/pkgconfig') in text and '/target' not in text
    run('relative-path', scanner=Path('scanner'), extra=('emberbsd-scanner-check',), success=False)
    run('outside-prefix', scanner=args.work/'outside-scanner', extra=('emberbsd-scanner-check',), success=False)
    run('missing-sdk', extra=('EMBERBSD_SDK_SOURCE='+str(args.work/'absent-sdk'), 'emberbsd-scanner-check'), success=False)
    conflict = run('conflicting-meson-scanner', extra=('MESON_BINARY.wayland-scanner=/target/bin/scanner', '-V', '${PKG_FAIL_REASON}'))
    assert 'different host Wayland scanner' in conflict

    # Copies are disposable negative-test inputs, not another maintained tool
    # provider. No compiler, installed.sha256, or producer record is present.
    selected = args.work/'negative-prefix'
    (selected/'bin').mkdir(parents=True)
    (selected/'lib/pkgconfig').mkdir(parents=True)
    for name in ('python3.15', 'wayland-scanner', 'pkg-config'):
        shutil.copy2(prefix/'bin'/name, selected/'bin'/name)
    pc = selected/'lib/pkgconfig/wayland-scanner.pc'
    original_pc = (prefix/'lib/pkgconfig/wayland-scanner.pc').read_text().replace(str(prefix), str(selected))
    pc.write_text(original_pc)
    # Python's shared runtime remains the installed native provider. The copied
    # executable still runs and reports its own selected path to SDK validation.
    run('copied-native-inputs', selected, ('emberbsd-scanner-check',))
    scanner = selected/'bin/wayland-scanner'
    original = scanner.read_bytes()
    mode = scanner.stat().st_mode
    for name, body in (
            ('old-version', 'print("wayland-scanner 1.25.0")'),
            ('failed-version', 'print("wayland-scanner 1.26.0");raise SystemExit(1)'),
            ('extra-output', 'print("wayland-scanner 1.26.0");print("unexpected")')):
        scanner.write_text('#!'+str(selected/'bin/python3.15')+'\n'+body+'\n')
        scanner.chmod(mode)
        run(name, selected, ('emberbsd-scanner-check',), success=False)
    scanner.write_bytes(original);scanner.chmod(mode & ~0o111)
    run('nonexecutable', selected, ('emberbsd-scanner-check',), success=False)
    scanner.chmod(mode);scanner.unlink()
    run('absent-scanner', selected, ('emberbsd-scanner-check',), success=False)
    scanner.symlink_to(prefix/'bin/wayland-scanner')
    run('escaping-symlink', selected, ('emberbsd-scanner-check',), success=False)
    scanner.unlink()
    scanner.write_text('#!/usr/bin/python3\nraise SystemExit("must not execute")\n');scanner.chmod(mode)
    run('external-interpreter', selected, ('emberbsd-scanner-check',), success=False)
    scanner.write_bytes(original);scanner.chmod(mode)
    # Change only Mach-O CPU metadata: shared SDK inspection must refuse it
    # before the OS loader attempts execution. Other native formats are outside
    # this Darwin fixture's foreign-CPU control.
    if original[:4] == b'\xcf\xfa\xed\xfe':
        altered = bytearray(original)
        cpu = struct.unpack_from('<I', altered, 4)[0]
        struct.pack_into('<I', altered, 4, 0x01000007 if cpu != 0x01000007 else 0x0100000c)
        scanner.write_bytes(altered)
        run('foreign-cpu', selected, ('emberbsd-scanner-check',), success=False)
        scanner.write_bytes(original)
    for name, content in (
            ('pc-version', original_pc.replace('Version: 1.26.0', 'Version: 0.0')),
            ('pc-prefix', original_pc.replace('prefix='+str(selected), 'prefix=/target')),
            ('pc-scanner', original_pc.replace('wayland_scanner=${bindir}/wayland-scanner', 'wayland_scanner=/target/bin/scanner'))):
        assert content != original_pc, name
        pc.write_text(content)
        run(name, selected, ('emberbsd-scanner-check',), success=False)
    pc.unlink()
    run('missing-pc', selected, ('emberbsd-scanner-check',), success=False)
    summary = {'actual_pkgsrc_cases': cases,
               'scope': 'native selection and metadata; no scanner rebuild or target compilation'}
    (args.work/'result.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
