#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check selected Node's Electron ABI in GN, generated header and config."""
import argparse
import importlib.util
import json
import shutil
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--node-source', type=Path, required=True)
p.add_argument('--electron', type=Path, required=True)
p.add_argument('--gn', type=Path, required=True)
p.add_argument('--python', type=Path, required=True)
a = p.parse_args()
node = a.node_source.resolve(strict=True)
electron = a.electron.resolve(strict=True)
helper = node / 'tools/getmoduleversion.py'
header = node / 'src/node_version.h'
abi = subprocess.check_output([str(a.python), str(helper), '--electron'], text=True).strip()
if not abi.isdecimal():
    raise ValueError('Node helper did not return a decimal ABI')
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    owner = Path(__file__).resolve().parents[1] / 'electron44/files/build-electron.py'
    spec = importlib.util.spec_from_file_location('electron_build', owner)
    build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
    class Native:
        def tool(self, role):
            assert role == 'python'
            return str(a.python)
    class Process:
        @staticmethod
        def capture(command, env):
            return subprocess.run(command, env=env, capture_output=True, check=True)
    selected, hashes = build.selected_node_abi(node, Native(), {}, {'process': Process()})
    assert str(selected) == abi and len(hashes) == 2
    # Build/reconfigure compare these hashes and the GN argument with the saved
    # producer inputs. Exercise both classes of drift on an isolated copy.
    copied = root / 'node-copy'
    (copied / 'tools').mkdir(parents=True); (copied / 'src').mkdir()
    shutil.copyfile(helper, copied / 'tools/getmoduleversion.py')
    shutil.copyfile(header, copied / 'src/node_version.h')
    before, old_hashes = build.selected_node_abi(copied, Native(), {}, {'process': Process()})
    h = copied / 'src/node_version.h'
    h.write_text(h.read_text().replace('#define NODE_EMBER_ELECTRON_MODULE_VERSION ' + abi,
                                       '#define NODE_EMBER_ELECTRON_MODULE_VERSION ' + str(int(abi) + 1)))
    after, new_hashes = build.selected_node_abi(copied, Native(), {}, {'process': Process()})
    assert after == before + 1 and old_hashes != new_hashes
    helper_copy = copied / 'tools/getmoduleversion.py'
    helper_copy.write_text(helper_copy.read_text() + '\n# drift\n')
    _, helper_hashes = build.selected_node_abi(copied, Native(), {}, {'process': Process()})
    assert helper_hashes != new_hashes
    (root / '.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\n')
    (root / 'BUILDCONFIG.gn').write_text('set_default_toolchain("//:toolchain")\n')
    (root / 'BUILD.gn').write_text('''declare_args() { node_module_version = 0 }
toolchain("toolchain") { tool("stamp") { command = "touch {{output}}" } }
assert(node_module_version == %s)
group("abi") {}
''' % abi)
    (root / 'out').mkdir()
    (root / 'out/args.gn').write_text('node_module_version = ' + abi + '\n')
    subprocess.run([str(a.gn), 'gen', 'out', '--script-executable=' + str(a.python)], cwd=root, check=True)
    generated = root / 'node_version.h'
    subprocess.run([str(a.python), str(electron / 'script/node/generate_node_version_header.py'), str(header), str(generated), abi], check=True)
    assert '#define NODE_MODULE_VERSION ' + abi in generated.read_text()
    # The config action is exercised with a controlled configure result; the
    # real Node configure runs separately in the Electron build.
    spec = importlib.util.spec_from_file_location('electron_config', electron / 'script/generate-config-gypi.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    # Source-view's Electron directory is a symlink; lexical '..' must not
    # traverse the symlink target's sibling Node tree.
    actual = root / 'actual'; view = root / 'view'
    (actual / 'electron/script').mkdir(parents=True)
    (actual / 'third_party/electron_node').mkdir(parents=True)
    (view / 'third_party/electron_node').mkdir(parents=True)
    shutil.copyfile(electron / 'script/generate-config-gypi.py', actual / 'electron/script/generate-config-gypi.py')
    (view / 'electron').symlink_to(actual / 'electron', target_is_directory=True)
    view_script = view / 'electron/script/generate-config-gypi.py'
    view_spec = importlib.util.spec_from_file_location('electron_view_config', view_script)
    view_module = importlib.util.module_from_spec(view_spec); view_spec.loader.exec_module(view_module)
    assert Path(view_module.NODE_DIR) == view / 'third_party/electron_node'
    assert Path(view_module.NODE_DIR).resolve() != (actual / 'third_party/electron_node').resolve()
    calls = []
    original_check_call = module.subprocess.check_call
    module.subprocess.check_call = lambda command, env=None: calls.append(command)
    try:
        module.run_node_configure(str(root), 'x64', 'netbsd')
        module.run_node_configure(str(root), 'x64', 'chromeos')
        module.run_node_configure(str(root), 'x64', 'unsupported-os')
        module.run_node_configure(str(root), 'x64', 'netbsd', configure_helper='/selected/helper.py', configure_inputs=['v8-source=/selected/v8'])
    finally:
        module.subprocess.check_call = original_check_call
    assert calls[0][calls[0].index('--dest-os') + 1] == 'netbsd'
    assert calls[1][calls[1].index('--dest-os') + 1] == 'linux'
    assert calls[2][calls[2].index('--dest-os') + 1] == 'unsupported-os'
    assert calls[3][1:3] == ['/selected/helper.py', 'configure']
    assert calls[3][calls[3].index('--v8-source') + 1] == '/selected/v8'
    assert calls[3][calls[3].index('--') + 1:] == ['--dest-cpu', 'x64', '--dest-os', 'netbsd', '--experimental-enable-pointer-compression', '--openssl-no-asm']
    source_copy = root / 'fixture-node'; source_copy.mkdir()
    (source_copy / 'input').write_text('unchanged')
    module.NODE_DIR = str(source_copy)
    def run_configure(node_dir, cpu, target_os, pkg_config=None, icu_pkgconfig_dir=None, configure_helper=None, configure_inputs=None):
        assert cpu == 'x64' and target_os == 'netbsd'
        Path(node_dir, 'config.gypi').write_text('{}')
    module.run_node_configure = run_configure
    for suffix, expected in [('so.1162674177', 'so.' + abi),
                             ('1162674177.dylib', abi + '.dylib'),
                             ('1162674177.a', abi + '.a'), ('1162674177.x', abi + '.x'), ('so', 'so')]:
        module.read_node_config_gypi = lambda node_dir: {'variables': {'node_module_version': 1162674177, 'shlib_suffix': suffix}}
        module.main(str(root / 'generated.gypi'), 'x64', 'netbsd', abi)
        variables = json.loads((root / 'generated.gypi').read_text())['variables']
        assert variables['node_module_version'] == int(abi)
        assert variables['shlib_suffix'] == expected
    module.read_node_config_gypi = lambda node_dir: {'variables': {'node_module_version': 1162674177, 'shlib_suffix': 'unexpected'}}
    try:
        module.main(str(root / 'generated.gypi'), 'x64', 'netbsd', abi)
        raise AssertionError('unknown suffix accepted')
    except ValueError as error:
        assert 'unexpected Node shared library suffix' in str(error)
    assert sorted(p.name for p in source_copy.iterdir()) == ['input']
print('Node ABI selected helper, GN argument, header and config PASS')
