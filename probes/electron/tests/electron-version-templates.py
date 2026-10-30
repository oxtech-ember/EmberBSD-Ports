#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise all real Electron version templates with the selected provider stamp."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for option in ('electron', 'semver', 'python', 'node', 'gn', 'ninja', 'touch'):
    p.add_argument('--' + option, type=Path, required=True)
a = p.parse_args()
for path in vars(a).values():
    if not path.is_absolute() or not path.exists(): p.error('inputs must be existing absolute paths')
owner = Path(__file__).resolve().parents[1] / 'electron44/files'
electron = a.electron.resolve()
expected = 'args_files = [ "$target_gen_dir/electron_version.args" ]'
if (electron / 'BUILD.gn').read_text().count(expected) != 3:
    raise ValueError('Electron version templates do not select exactly the JSON argument file')
with tempfile.TemporaryDirectory(prefix='ember-electron-version-templates-') as tmp:
    root = Path(tmp).resolve(); local = root / 'owner'; local.mkdir()
    for name in ('electron-version-provider.py', 'node-providers.py'):
        shutil.copyfile(owner / name, local / name)
    prefix = root / 'prefix'; modules = prefix / 'lib/node_modules'
    shutil.copytree(a.semver, modules / 'semver')
    stub = '''class Native:\n bundle_root={prefix!r}\n host={{'os':'Darwin','cpu':'arm64'}}\n path={path!r}\n def tool(self, role): return {{'node':{node!r}}}[role]\nclass Host:\n def load_host_prefix(self,*a,**k): return Native()\nclass Process:\n def sanitized_environment(self): return {{}}\ndef load_sdk(root): return {{'host_prefix':Host(), 'process':Process()}}\n'''.format(prefix=str(prefix), path=str(a.node.parent), node=str(a.node))
    (local / 'build-electron.py').write_text(stub)
    source = root / 'electron'; (source / 'build').mkdir(parents=True); (source / 'script').mkdir()
    for name in ('npm.gni', 'templated_file.gni', 'generate-template.py'):
        shutil.copyfile(electron / 'build' / name, source / 'build' / name)
    shutil.copytree(electron / 'build/templates', source / 'build/templates')
    shutil.copyfile(electron / 'script/generate-version-json.js', source / 'script/generate-version-json.js')
    shutil.copyfile(electron / 'package.json', source / 'package.json')
    (root / '.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\n')
    (root / 'BUILDCONFIG.gn').write_text('set_default_toolchain("//:tools")\n')
    build = '''toolchain("tools") { tool("stamp") { command = %s + " {{output}}" } }
import("//electron/build/npm.gni")
import("//electron/build/templated_file.gni")
npm_action("electron_version_args") {
  script = "generate-version-json"
  args = [ rebase_path("$target_gen_dir/electron_version.args"), "45.0.0-beta.2" ]
  inputs = [ "//electron/script/generate-version-json.js" ]
  outputs = [ "$target_gen_dir/electron_version.args" ]
}
''' % json.dumps(str(a.touch))
    for label, template, output in (('header','electron_version.tmpl','electron_version.h'),
                                    ('rc','electron_rc.tmpl','electron.rc'),
                                    ('version','version_string.tmpl','version')):
        build += '''templated_file("%s") {
  deps = [ ":electron_version_args" ]
  template = "//electron/build/templates/%s"
  output = "$target_gen_dir/%s"
  args_files = get_target_outputs(":electron_version_args")
}
''' % (label, template, output)
    (root / 'out').mkdir()
    values = {'emberbsd_electron_node': str(a.node), 'emberbsd_electron_version_provider': str(local / 'electron-version-provider.py'),
              'emberbsd_electron_provider_selector': str(local / 'node-providers.py'), 'emberbsd_electron_sdk_source': str(root),
              'emberbsd_electron_host_prefix': str(prefix), 'emberbsd_electron_semver_inputs': sorted(str(x) for x in (modules / 'semver').rglob('*') if x.is_file())}
    (root / 'out/args.gn').write_text(''.join(k + ' = ' + json.dumps(v) + '\n' for k, v in values.items()))
    def generate():
        subprocess.run([str(a.gn), 'gen', 'out', '--script-executable=' + str(a.python)], cwd=root, check=True, capture_output=True)
    def build_targets():
        return subprocess.run([str(a.ninja), '-C', 'out', '-j1', 'gen/electron_version.h', 'gen/electron.rc', 'gen/version'], cwd=root, capture_output=True, text=True)
    (root / 'BUILD.gn').write_text(build); generate(); before = build_targets()
    if not before.returncode or 'JSONDecodeError' not in before.stdout + before.stderr:
        raise RuntimeError('original stamp-as-JSON failure did not reproduce')
    (root / 'BUILD.gn').write_text(build.replace('args_files = get_target_outputs(":electron_version_args")', expected))
    generate(); after = build_targets()
    if after.returncode: raise RuntimeError(after.stdout + after.stderr)
    if '#define ELECTRON_MAJOR_VERSION 45' not in (root / 'out/gen/electron_version.h').read_text():
        raise RuntimeError('version template output is incorrect')
    if not (root / 'out/gen/electron_version_provider/electron_version_args.stamp').is_file():
        raise RuntimeError('provider stamp is absent')
print('Electron version GN/Ninja templates and provider stamp PASS')
