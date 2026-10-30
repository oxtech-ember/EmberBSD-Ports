#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise explicit pkg-config roles in a small GN graph with real providers.

This Darwin-to-NetBSD graph uses patched Chromium pkg-config and the mac toolchain template;
compiler tool commands and unrelated Chromium configuration are fixtures.
It does not compile an Electron target or replace a full GN graph check.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for option in ('source', 'patch', 'gn', 'host-prefix', 'target-sysroot', 'work-dir'):
    parser.add_argument('--' + option, type=Path, required=True)
a = parser.parse_args()
if sys.platform != 'darwin':
    parser.error('this fixture exercises Darwin-to-NetBSD routing')
owner_patch = Path(__file__).resolve().parents[1] / 'patches/gn-pkgconfig-explicit-roles.patch'
files = ('build/config/BUILDCONFIG.gn', 'build/config/linux/pkg_config.gni',
         'build/config/linux/pkg-config.py', 'build/toolchain/mac/BUILD.gn',
         'build/toolchain/linux/unbundle/BUILD.gn', 'build/toolchain/gcc_toolchain.gni')
for tool in (a.patch, a.gn, a.host_prefix / 'bin/pkg-config'):
    if not tool.is_absolute() or not tool.is_file() or not os.access(tool, os.X_OK):
        parser.error('choose absolute executable tools')
env = dict(os.environ, PKG_CONFIG_PATH='/invalid/poison',
           PKG_CONFIG_LIBDIR='/invalid/poison', PKG_CONFIG_SYSROOT_DIR='/invalid/poison')

def run(argv, *, cwd=None, success=True):
    result = subprocess.run([str(x) for x in argv], cwd=cwd, env=env,
                            capture_output=True, text=True)
    if (result.returncode == 0) != success:
        raise RuntimeError(f'{argv!r} returned {result.returncode}: {result.stderr}')
    return result.stdout + result.stderr

with tempfile.TemporaryDirectory(dir=a.work_dir) as directory:
    root = Path(directory)
    for item in files:
        dest = root / item
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(a.source / item, dest)
    original_mac = (root / 'build/toolchain/mac/BUILD.gn').read_text()
    run([a.patch, '--batch', '--forward', '--fuzz=0', '-p1', '-i', owner_patch], cwd=root)
    original_config = (root / 'build/config/BUILDCONFIG.gn').read_text()
    first = original_config.index('# Explicit pkg-config routing')
    last = original_config.index('\n}\n', first) + 3
    role_declarations = original_config[first:last]
    (root / '.gn').write_text('buildconfig = "//build/config/BUILDCONFIG.gn"\n')
    (root / 'build/config/BUILDCONFIG.gn').write_text(role_declarations + '''
declare_args() {
  v8_current_cpu = "x64"
  is_clang = true
  use_debug_fission = false
  use_sysroot = true
  use_remoteexec = false
}
if (current_os == "") { current_os = target_os }
if (current_cpu == "") { current_cpu = target_cpu }
set_default_toolchain("//tc:target")
host_toolchain = "//build/toolchain/mac:clang_arm64"
''')
    def write(name, text):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    write('build/config/compute_inputs_for_analyze.gni', 'compute_inputs_for_analyze = false\n')
    write('build/config/gclient_args.gni', 'declare_args() { emberbsd_target_sysroot = "" }\n')
    write('build/config/sysroot.gni', '''import("//build/config/gclient_args.gni")
target_sysroot = emberbsd_target_sysroot
if (current_os == "mac") {
  sysroot = "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
} else {
  sysroot = emberbsd_target_sysroot
}
''')
    write('build/toolchain/rbe.gni', '')
    write('build/config/mac/mac_sdk.gni', 'mac_bin_path = "selected"\n')
    write('build/config/v8_target_cpu.gni', '')
    write('build_overrides/build.gni', 'build_with_chromium = false\n')
    # The actual mac template chooses role and forwards its arguments. This
    # miniature apple-toolchain adapter exercises that flow without compiling.
    write('build/toolchain/apple/toolchain.gni', '''template("apple_toolchain") {
  not_needed(invoker, "*", [ "toolchain_args" ])
  _args = invoker.toolchain_args
  toolchain(target_name) {
    tool("cxx") { command = "/usr/bin/true"\n outputs = [ "{{source_out_dir}}/{{source_name_part}}.o" ] }
    tool("stamp") { command = "/usr/bin/touch {{output}}" }
    toolchain_args = { forward_variables_from(_args, "*") }
  }
  toolchain(target_name + "_for_rust_host_build_tools") {
    tool("cxx") { command = "/usr/bin/true"\n outputs = [ "{{source_out_dir}}/{{source_name_part}}.o" ] }
    tool("stamp") { command = "/usr/bin/touch {{output}}" }
    toolchain_args = { forward_variables_from(_args, "*") }
  }
}
''')
    write('tc/BUILD.gn', '''toolchain("target") {
  tool("cxx") { command = "/usr/bin/true"\n outputs = [ "{{source_out_dir}}/{{source_name_part}}.o" ] }
  tool("stamp") { command = "/usr/bin/touch {{output}}" }
}
''')
    write('BUILD.gn', '''import("//build/config/linux/pkg_config.gni")
pkg_config("ffi") { packages = [ "libffi" ] }
source_set("probe") { sources = [ "empty.cc" ]\n configs = [ ":ffi" ] }
group("all") { deps = [ ":probe", ":probe(//build/toolchain/mac:clang_arm64)",
  ":probe(//build/toolchain/mac:clang_arm64_v8_x64)",
  ":probe(//build/toolchain/mac:clang_arm64_for_rust_host_build_tools)" ] }
''')
    write('empty.cc', '')
    host = str(a.host_prefix.resolve())
    target = str(a.target_sysroot.resolve())
    args = ' '.join((
        'target_os="netbsd"', 'target_cpu="x64"',
        'emberbsd_pkg_config_role="explicit"',
        'emberbsd_native_pkg_config_prefix=' + json.dumps(host),
        'emberbsd_target_sysroot=' + json.dumps(target),
        'pkg_config=' + json.dumps(host + '/bin/pkg-config'),
        'host_pkg_config=' + json.dumps(host + '/bin/pkg-config')))
    script = '--script-executable=' + sys.executable
    run([a.gn, 'gen', root / 'out', '--root=' + str(root), script, '--args=' + args], cwd=root)
    labels = ('//:probe(//tc:target)', '//:probe(//build/toolchain/mac:clang_arm64)',
              '//:probe(//build/toolchain/mac:clang_arm64_v8_x64)',
              '//:probe(//build/toolchain/mac:clang_arm64_for_rust_host_build_tools)')
    for index, label in enumerate(labels):
        dirs = run([a.gn, 'desc', root / 'out', label, 'lib_dirs', script], cwd=root).splitlines()
        expected = Path(target) / 'usr/pkg/lib' if index == 0 else Path(host) / 'lib'
        assert [Path(d).resolve() for d in dirs] == [expected.resolve()], (label, dirs)
        flags = run([a.gn, 'desc', root / 'out', label, 'cflags_cc', script], cwd=root)
        expected_include = Path(target) / 'usr/pkg/include' if index == 0 else Path(host) / 'include'
        assert any(line.startswith('-isystem') and
                   (root / 'out' / line.removeprefix('-isystem')).resolve() == expected_include.resolve()
                   for line in flags.splitlines()), (label, flags)
    # The host and target wrappers happen to use the same selected executable
    # in production. Poison each input separately to prove the GN role really
    # selects that input rather than only producing the right include paths.
    for key in ('host_pkg_config', 'pkg_config'):
        selected = ' ' + key + '=' + json.dumps(host + '/bin/pkg-config')
        assert selected in args
        poisoned = args.replace(selected, ' ' + key + '="/invalid/not-a-pkg-config"')
        error = run([a.gn, 'gen', root / ('out-bad-' + key), '--root=' + str(root),
                     script, '--args=' + poisoned], cwd=root, success=False)
        assert 'Could not run pkg-config' in error or 'FileNotFoundError' in error
    (root / 'build/toolchain/mac/BUILD.gn').write_text(original_mac)
    error = run([a.gn, 'gen', root / 'out-missing', '--root=' + str(root), script,
                 '--args=' + args], cwd=root, success=False)
    assert 'Every secondary toolchain must declare its pkg-config role' in error
    bad_args = args.replace('emberbsd_pkg_config_role="explicit"', 'emberbsd_pkg_config_role="invalid"')
    error = run([a.gn, 'gen', root / 'out-invalid', '--root=' + str(root), script,
                 '--args=' + bad_args], cwd=root, success=False)
    assert 'Unknown pkg-config role' in error
    python_script = root / 'build/config/linux/pkg-config.py'
    upstream = a.source / 'build/config/linux/pkg-config.py'
    plain_args = ['-p', a.host_prefix / 'bin/pkg-config', 'libffi']
    assert run([sys.executable, upstream, *plain_args], cwd=root) == \
           run([sys.executable, python_script, *plain_args], cwd=root)
    spaced = root / 'native prefix with spaces'
    (spaced / 'lib/pkgconfig').mkdir(parents=True)
    escaped = str(spaced).replace(' ', r'\ ')
    (spaced / 'lib/pkgconfig/ember-spaces.pc').write_text(
        'prefix=' + escaped + '\n'
        'libdir=${prefix}/lib\nincludedir=${prefix}/include\n'
        'Name: ember-spaces\nDescription: escaped prefix test\nVersion: 1\n'
        'Libs: -L${libdir} -lember_spaces\nCflags: -I${includedir}\n')
    result = json.loads(run([sys.executable, python_script, '--emberbsd-native-prefix',
                             spaced, '-p', a.host_prefix / 'bin/pkg-config', 'ember-spaces'], cwd=root))
    assert result[0] == [str(spaced / 'include')] and result[3] == [str(spaced / 'lib')]
    error = run([sys.executable, python_script, '--emberbsd-native-prefix', '', 'libffi'],
                cwd=root, success=False)
    assert 'native pkg-config prefix must be absolute' in error
    error = run([sys.executable, python_script, '--allow-cross-sysroot', 'libffi'],
                cwd=root, success=False)
    assert 'cross pkg-config requires a sysroot and architecture' in error
    error = run([sys.executable, python_script, '--emberbsd-native-prefix', host,
                 '-s', target, '-a', 'x64', 'libffi'], cwd=root, success=False)
    assert 'native pkg-config cannot use a target sysroot' in error
print('PASS: host, snapshot, Rust-host and target GN pkg-config routing; missing/invalid roles rejected')
