#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the selected target Undici package and logical loader mapping."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_electron', owner / 'electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
with tempfile.TemporaryDirectory(prefix='electron-undici-selection-') as temp:
    root = Path(temp); sysroot = root / 'target'; host = root / 'host'; export = root / 'export'
    recipe = export / 'www/undici'; (recipe / 'files').mkdir(parents=True)
    metadata = []
    for name in ('Makefile', 'distinfo', 'files/generate-wasm.py'):
        item = recipe / name; item.write_text(name)
        metadata.append('www/undici/' + name + ': ' + hashlib.sha256(item.read_bytes()).hexdigest())
    package = sysroot / 'usr/pkg/pkgdb/undici-1nb1'; package.mkdir(parents=True)
    (package / '+BUILD_INFO').write_text('PKGPATH=www/undici\nEMBERBSD_UNDICI_RUNTIME_PREFIX=/usr/pkg\n')
    (package / '+BUILD_VERSION').write_text('\n'.join(metadata) + '\n')
    loader_bytes = b'createRequire("/usr/pkg/lib/node_modules/undici/loader.js")'
    contents = 'lib/node_modules/undici/loader.js\n@comment MD5:' + hashlib.md5(loader_bytes, usedforsecurity=False).hexdigest() + '\n'
    (package / '+CONTENTS').write_text(contents)
    loader = sysroot / 'usr/pkg/lib/node_modules/undici/loader.js'; loader.parent.mkdir(parents=True); loader.write_bytes(loader_bytes)
    class Process:
        @staticmethod
        def capture(command, *, env):
            return SimpleNamespace(stdout=b'undici-1nb1\n')
    options = SimpleNamespace(shared_undici=True, sysroot=sysroot, host_prefix=host, host_buildlink_pkgsrc=export)
    sdk = {'process': Process()}
    selected = build.common_undici(options, sdk, {})
    assert selected == {'node_shared_undici_path': '/usr/pkg/lib/node_modules/undici/loader.js',
                        'node_shared_undici_input': str(loader)}
    def rejected():
        try: build.common_undici(options, sdk, {})
        except (ValueError, OSError): return
        raise AssertionError('bad selected Undici accepted')
    (package / '+CONTENTS').write_text(''); rejected()
    (package / '+CONTENTS').write_text(contents)
    loader.write_text('changed'); rejected(); loader.write_bytes(loader_bytes)
    wrong = b'createRequire("/wrong/loader.js")'
    loader.write_bytes(wrong)
    (package / '+CONTENTS').write_text('lib/node_modules/undici/loader.js\n@comment MD5:' + hashlib.md5(wrong, usedforsecurity=False).hexdigest() + '\n')
    rejected(); loader.write_bytes(loader_bytes); (package / '+CONTENTS').write_text(contents)
    (recipe / 'files/generate-wasm.py').write_text('changed'); rejected()
    (recipe / 'files/generate-wasm.py').write_text('files/generate-wasm.py')
    loader.unlink(); loader.symlink_to(recipe / 'Makefile'); rejected()
    options.shared_undici = False
    assert build.common_undici(options, sdk, {}) == {}
print('common Undici selection/default and stale/ownership/escape controls PASS')
