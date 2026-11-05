#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check native provider runtime paths with the actual GN/pkg-config template."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'gn', 'patch-tool', 'host-prefix', 'sysroot'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
source = a.source.resolve(strict=True)
prefix = a.host_prefix.resolve(strict=True)
patch = Path(__file__).resolve().parents[1] / 'patches/gn-common-native-rpath.patch'
with tempfile.TemporaryDirectory(prefix='electron-native-rpath-') as temporary:
    root = Path(temporary)
    def write(name, content):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    for name in ('build/config/linux/pkg_config.gni', 'build/config/linux/pkg-config.py',
                 'third_party/libyuv/BUILD.gn'):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target)
    subprocess.run([str(a.patch_tool), '-p1', '-i', str(patch)], cwd=root,
                   check=True, capture_output=True)
    write('.gn', 'buildconfig = "//config.gn"\n')
    write('build/config/compute_inputs_for_analyze.gni', 'compute_inputs_for_analyze = false\n')
    for name in ('build/config/gclient_args.gni', 'build/config/sysroot.gni',
                 'build/toolchain/rbe.gni'):
        write(name, '')
    write('BUILD.gn', '''import("//build/config/linux/pkg_config.gni")
toolchain("tc") {
  tool("stamp") { command = "unused" }
  tool("cxx") { command = "unused" outputs = [ "{{source_out_dir}}/{{target_output_name}}.o" ] }
}
pkg_config("zstd") { packages = [ "libzstd" ] }
pkg_config("headers_only") { packages = [ "libzstd" ] ignore_libs = true }
group("default") {
  deps = [ ":yuv_consumer", ":zstd_consumer", ":headers_consumer" ]
}
source_set("zstd_consumer") {
  sources = [ "dummy.cc" ]
  configs = [ ":zstd" ]
}
source_set("headers_consumer") { sources = [ "dummy.cc" ] configs = [ ":headers_only" ] }
source_set("yuv_consumer") { sources = [ "dummy.cc" ] deps = [ "//third_party/libyuv:libyuv" ] }
''')
    write('dummy.cc', '')
    for role in ('native', 'target'):
        is_native = role == 'native'
        library_prefix = prefix if is_native else a.sysroot / 'usr/pkg'
        suffix = '.dylib' if is_native else '.so'
        library = (library_prefix / ('lib/libyuv' + suffix)).resolve(strict=True)
        selected_role = 'host' if is_native else 'target'
        values = {
            'emberbsd_pkg_config_role': role,
            'emberbsd_native_pkg_config_prefix': str(prefix),
            'emberbsd_native_pkg_config_buildlink': False,
            'emberbsd_target_sysroot': str(a.sysroot),
            'current_os': 'mac' if is_native else 'netbsd',
            'current_cpu': 'arm64' if is_native else 'x64',
            'sysroot': '' if is_native else str(a.sysroot),
            'target_sysroot': '' if is_native else str(a.sysroot),
            'use_sysroot': False, 'use_remoteexec': False, 'build_with_chromium': False,
        }
        write('config.gn', 'set_default_toolchain("//:tc")\nhost_toolchain = "//:tc"\n' +
              ''.join(key + ' = ' + json.dumps(value) + '\n' for key, value in values.items()))
        out = root / ('out-' + role)
        out.mkdir()
        write(str(out.relative_to(root) / 'args.gn'),
              'pkg_config = ' + json.dumps(str(prefix / 'bin/pkg-config')) + '\n' +
              'host_pkg_config = ' + json.dumps(str(prefix / 'bin/pkg-config')) + '\n' +
              f'emberbsd_libyuv_{selected_role}_library = ' + json.dumps(str(library)) + '\n' +
              f'emberbsd_libyuv_{selected_role}_headers = ' + json.dumps(str(library_prefix / 'include')) + '\n' +
              f'emberbsd_libyuv_{selected_role}_inputs = [ ' + json.dumps(str(library)) + ' ]\n')
        subprocess.run([str(a.gn), 'gen', str(out), '--fail-on-unused-args',
                        '--script-executable=' + sys.executable], cwd=root,
                       check=True, capture_output=True)
        def description(label):
            result = subprocess.run([str(a.gn), 'desc', str(out), label,
                                     '--format=json', '--script-executable=' + sys.executable],
                                    cwd=root, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            return next(iter(json.loads(result.stdout).values()))
        zstd = description('//:zstd_consumer')
        libyuv = description('//:yuv_consumer')
        headers = description('//:headers_consumer')
        if is_native:
            assert zstd['ldflags'] == ['-Wl,-rpath=' + str(prefix / 'lib')], zstd
            assert libyuv['ldflags'] == ['-Wl,-rpath=' + str(library.parent)], libyuv
        else:
            assert not zstd.get('ldflags') and not libyuv.get('ldflags')
        assert not headers.get('ldflags'), headers
print('PASS: selected native library runtime paths; target and headers-only unchanged')
