#!/usr/bin/env python3.15
# Origin: EmberBSD (AI-assisted). Production GN argument regression.
"""Run the production GN template and pkg-config script with real target metadata."""
import sys

sys.dont_write_bytecode = True
if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 15):
    raise SystemExit("use the selected host CPython 3.15")

from pathlib import Path
import argparse
import json
import os
import shutil

parser = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'sysroot', 'gn', 'pkg-config', 'sdk-source'):
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('new_work', type=Path, metavar='NEW_WORK')
options = parser.parse_args()
if not options.sdk_source.is_absolute():
    parser.error('--sdk-source must be absolute')
SDK_SOURCE = options.sdk_source.resolve(strict=True)
package = SDK_SOURCE / 'src/emberbsd_sdk'
if not (package / '__init__.py').is_file():
    parser.error('the selected SDK source has no emberbsd_sdk API')
sys.path.insert(0, str(SDK_SOURCE / 'src'))
import emberbsd_sdk
if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    parser.error('the selected SDK must provide API version 1')
if Path(emberbsd_sdk.__file__).resolve().parent != package.resolve():
    parser.error('SDK package must come from the selected source')
from emberbsd_sdk import errors, inventory, jsonio, process
SDK_MODULES = (emberbsd_sdk, errors, inventory, jsonio, process)
if any(not Path(module.__file__).resolve().is_relative_to(package.resolve()) for module in SDK_MODULES):
    parser.error('SDK modules must come from the selected source')
CommandError = errors.CommandError
capture = process.capture
sha256_file = inventory.sha256_file
write_json = jsonio.write_json
SOURCE, SYSROOT, GN, PKGCONF = (path.resolve(strict=True) for path in
    (options.source, options.sysroot, options.gn, options.pkg_config))
PYTHON = Path(sys.executable).resolve(strict=True)
if not options.new_work.is_absolute():
    parser.error('NEW_WORK must be absolute')
ROOT = options.new_work.resolve()
if ROOT.is_relative_to(SOURCE) or ROOT.is_relative_to(SYSROOT):
    parser.error('NEW_WORK must be outside the source and sysroot')
ROOT.mkdir(parents=True)
LOGS = ROOT / 'logs'
LOGS.mkdir()
write_json(LOGS / 'space-before.json', shutil.disk_usage(ROOT)._asdict())
FILES = ['build/config/linux/pkg_config.gni', 'build/config/linux/pkg-config.py',
         'build/config/linux/cached_results.scope', 'build/config/compute_inputs_for_analyze.gni',
         'build/config/gclient_args.gni', 'build/config/sysroot.gni',
         'build/toolchain/sysroot.gni', 'build/toolchain/rbe.gni', 'build/toolchain/siso.gni',
         'build/config/netbsd/pkgconfig/zlib.pc']
provided = (SOURCE / FILES[0]).read_text()
before = '''# Only use the custom libdir when building with the target sysroot.
if (target_sysroot != "" && sysroot == target_sysroot) {'''
after = '''# EmberBSD's common args already select its effective pkgsrc libdir.
# Keep the ordinary target arguments and their cache keys unchanged.
if (!_emberbsd_cross_pkg_config && target_sysroot != "" &&
    sysroot == target_sysroot) {'''
if before in provided:
    assert provided.count(before) == 1
    original = provided
    patched = original.replace(before, after)
else:
    assert provided.count(after) == 1, 'unrecognized production argument owner'
    patched = provided
    original = patched.replace(after, before)
PATCH = Path(__file__).resolve().parent.parent / 'patches/gn-pkgconfig-libdir.patch'
patch = ROOT / PATCH.name
shutil.copy2(PATCH, patch)

bin_dir = ROOT / 'bin'
bin_dir.mkdir()
wrapper = '''#!{python}
import json, os, sys
with open(os.environ['E12_PKGCONF_LOG'], 'a') as output:
    output.write(json.dumps(dict(argv=sys.argv, libdir=os.environ.get('PKG_CONFIG_LIBDIR'),
        path=os.environ.get('PKG_CONFIG_PATH'), sysroot=os.environ.get('PKG_CONFIG_SYSROOT_DIR'))) + '\\n')
os.execv({pkgconf!r}, [{pkgconf!r}, *sys.argv[1:]])
'''.format(python=PYTHON, pkgconf=str(PKGCONF))
for name in ('pkg-config', 'target-wrapper', 'host-wrapper'):
    (bin_dir / name).write_text(wrapper)
    (bin_dir / name).chmod(0o755)

buildconfig = '''declare_args() {
  fixture_host_os = "mac"
  fixture_os = "netbsd"
  fixture_cpu = "arm64"
  fixture_host = false
  fixture_execute = false
  fixture_packages = [ "gio-unix-2.0", "gtk+-3.0" ]
}
host_os = fixture_host_os
current_os = fixture_os
current_cpu = fixture_cpu
target_os = fixture_os
target_cpu = fixture_cpu
is_android = false
is_linux = current_os == "linux"
is_chromeos = false
is_mac = current_os == "mac"
is_ios = false
is_fuchsia = false
if (fixture_host) {
  host_toolchain = "//toolchain:default"
} else {
  host_toolchain = "//toolchain:host"
}
set_default_toolchain("//toolchain:default")
'''
build = '''import("//build/config/linux/pkg_config.gni")
observed = {
  common = common_pkg_config_args
  target = pkg_config_args
  host = host_pkg_config_args
}
write_file("$root_build_dir/arguments.json", observed, "json")
if (fixture_execute) {
  pkg_config("metadata") {
    packages = fixture_packages
  }
}
group("all") {
  if (fixture_execute) {
    public_configs = [ ":metadata" ]
  }
}
'''
toolchain = '''toolchain("default") {
  tool("stamp") { command = "touch {{output}}" }
}
toolchain("host") {
  tool("stamp") { command = "touch {{output}}" }
}
'''
environment = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.defpath,
                   PKG_CONFIG_PATH='', PYTHONDONTWRITEBYTECODE='1')
for name in ('PKG_CONFIG_LIBDIR', 'PKG_CONFIG_SYSROOT_DIR', 'PYTHONPATH', 'PYTHONHOME'):
    environment.pop(name, None)
commands = []

def run(name, command, *, cwd=ROOT, env=environment, success=True):
    try:
        result = capture(list(map(str, command)), cwd=cwd, env=env)
    except CommandError as error:
        result = error
    (LOGS / (name + '.stdout')).write_bytes(result.stdout)
    (LOGS / (name + '.stderr')).write_bytes(result.stderr)
    commands.append({'name': name, 'argv': list(map(str, command)), 'cwd': str(cwd), 'status': result.returncode})
    write_json(ROOT / 'commands.json', commands, exclusive=False)
    if success:
        assert result.returncode == 0, (name, result.stdout[-5000:], result.stderr[-5000:])
    return result

for version, text in [('before', original), ('after', patched)]:
    tree = ROOT / version
    tree.mkdir()
    for relative in FILES:
        target = tree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / relative, target)
    (tree / FILES[0]).write_text(original)
    if version == 'after':
        run('apply-carried-patch', ['patch', '-p0', '-F', '0', '-i', patch], cwd=tree)
        assert (tree / FILES[0]).read_text() == patched
    (tree / '.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\nscript_executable = ' + json.dumps(str(PYTHON)) + '\n')
    (tree / 'BUILDCONFIG.gn').write_text(buildconfig)
    (tree / 'BUILD.gn').write_text(build)
    (tree / 'toolchain').mkdir()
    (tree / 'toolchain/BUILD.gn').write_text(toolchain)

base = dict(use_sysroot=False, sysroot=str(SYSROOT), target_sysroot=str(SYSROOT),
            emberbsd_target_sysroot=str(SYSROOT))
cases = {
    'e12-real-default': dict(base, fixture_execute=True),
    'e12-real-custom': dict(base, fixture_execute=True, pkg_config=str(bin_dir / 'target-wrapper')),
    'e12-separate-sysroot': dict(base, sysroot='', target_sysroot='', fixture_execute=True),
    'linux-target': dict(base, fixture_os='linux', system_libdir='lib64'),
    'linux-custom': dict(base, fixture_os='linux', system_libdir='lib64', pkg_config=str(bin_dir / 'target-wrapper')),
    'native-no-sysroot': dict(base, fixture_os='linux', sysroot='', target_sysroot='', emberbsd_target_sysroot=''),
    'host-custom': dict(base, fixture_os='mac', fixture_host=True, sysroot='/fixture/host-sdk',
                        host_pkg_config=str(bin_dir / 'host-wrapper'), pkg_config=str(bin_dir / 'target-wrapper')),
    'linux-cached': dict(base, fixture_os='linux', fixture_cpu='x64', fixture_execute=True,
                         sysroot='//build/linux/debian_bullseye_amd64-sysroot', target_sysroot='',
                         emberbsd_target_sysroot='', fixture_packages=['gio-2.0', 'gio-unix-2.0']),
}
observations = {}
for version in ('before', 'after'):
    for name, values in cases.items():
        tree = ROOT / version
        output = tree / 'out' / name
        output.mkdir(parents=True)
        (output / 'args.gn').write_text('\n'.join(key + ' = ' + json.dumps(value) for key, value in values.items()) + '\n')
        log = LOGS / (version + '-' + name + '.pkgconf.jsonl')
        env = dict(environment, E12_PKGCONF_LOG=str(log))
        failed = version == 'before' and name in ('e12-real-default', 'e12-real-custom')
        result = run(version + '-' + name, [GN, 'gen', output, '--root=' + str(tree)],
                     env=env, success=not failed)
        if failed:
            assert result.returncode != 0 and b'gio-unix-2.0' in result.stdout + result.stderr
            assert b'--system_libdir pkg/lib' in result.stdout + result.stderr
            assert b'--system_libdir lib' in result.stdout + result.stderr
        args = json.loads((output / 'arguments.json').read_text())
        rows = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        observations[version + '-' + name] = {'args': args, 'pkgconf_calls': rows, 'status': result.returncode}
        if name == 'linux-cached':
            assert not rows, 'cached query unexpectedly executed pkg-config'
        if values.get('fixture_execute') and not failed:
            desc = run(version + '-' + name + '-desc',
                       [GN, 'desc', output, '//:metadata', '--format=json', '--root=' + str(tree)], env=env)
            decoded = json.loads(desc.stdout)
            observations[version + '-' + name]['config'] = decoded
            if name != 'linux-cached':
                config = next(iter(decoded.values()))
                assert 'gio-2.0' in config['libs'] and 'gtk-3' in config['libs']
                for item in config.get('cflags_c', []):
                    assert item.startswith('-isystem')
                    include = item.removeprefix('-isystem')
                    assert (output / include).resolve().is_relative_to(SYSROOT.resolve()), include
                for directory in config.get('lib_dirs', []):
                    assert (output / directory).resolve().is_relative_to(SYSROOT.resolve()), directory
                assert rows and all(row['path'] == '' and row['sysroot'] is None for row in rows)
                assert all((output / row['libdir'].split(':')[0]).resolve() ==
                           (SYSROOT / 'usr/pkg/lib/pkgconfig').resolve() for row in rows)
        if version == 'after' and name.startswith('e12-'):
            combined = args['common'] + args['target']
            assert combined.count('--system_libdir') == 1
            assert combined[combined.index('--system_libdir') + 1] == 'pkg/lib'
for name in ('linux-target', 'linux-custom', 'native-no-sysroot', 'host-custom', 'linux-cached'):
    assert observations['before-' + name]['args'] == observations['after-' + name]['args'], name
assert observations['before-linux-cached']['config'] == observations['after-linux-cached']['config']

target_env = dict(environment, PKG_CONFIG_LIBDIR=str(SYSROOT / 'usr/pkg/lib/pkgconfig') + ':' + str(SYSROOT / 'usr/pkg/share/pkgconfig'))
metadata = {}
for package in ('gio-unix-2.0', 'gtk+-3.0'):
    pc = SYSROOT / 'usr/pkg/lib/pkgconfig' / (package + '.pc')
    located = run('pcfiledir-' + package, [PKGCONF, '--variable=pcfiledir', package], env=target_env).stdout.decode().strip()
    assert Path(located).resolve() == pc.parent.resolve()
    metadata[package] = {'path': str(pc), 'sha256': sha256_file(pc),
                         'version': run('modversion-' + package, [PKGCONF, '--modversion', package], env=target_env).stdout.decode().strip()}
assert (SOURCE / FILES[0]).read_text() == provided
for relative in FILES:
    if relative != FILES[0]:
        assert (ROOT / 'before' / relative).read_bytes() == (SOURCE / relative).read_bytes()
run('gn-format', [GN, 'format', '--dry-run', ROOT / 'after' / FILES[0]])
check = ROOT / 'patch-check/build/config/linux'
check.mkdir(parents=True)
(check / 'pkg_config.gni').write_text(original)
run('patch-apply', ['patch', '-p0', '-F', '0', '-i', patch], cwd=ROOT / 'patch-check')
assert (check / 'pkg_config.gni').read_text() == patched
result = {'status': 'PASS', 'source': str(SOURCE), 'sysroot': str(SYSROOT), 'patch': str(patch), 'patch_sha256': sha256_file(patch),
    'cases': observations, 'metadata': metadata, 'commands': commands,
    'sdk_source': str(SDK_SOURCE), 'sdk_api': 1,
    'sdk_sha256': {str(m.__file__): sha256_file(m.__file__) for m in SDK_MODULES},
    'source_sha256': {relative: sha256_file(SOURCE / relative) for relative in FILES},
    'tools': {str(path): sha256_file(path) for path in (GN, PYTHON, PKGCONF)},
    'scope': 'Production GN template, script and cached-results bytes in an isolated GN root; actual installed target gio-unix/GTK metadata and real pkgconf. Platform/toolchain values are controlled fixture inputs. No target compilation, linking, execution or complete Electron GN generation.'}
write_json(ROOT / 'result.json', result)
print(json.dumps({'status': 'PASS', 'GN_cases': len(cases) * 2, 'metadata': metadata,
                  'result': str(ROOT / 'result.json')}, indent=2))
