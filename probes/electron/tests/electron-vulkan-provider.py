#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise Vulkan role ownership, cross-role payload and registry checks."""
import hashlib
import importlib.util
import json
import tempfile
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

owner = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files'
def load(name, file):
    spec = importlib.util.spec_from_file_location(name, owner / file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
controller = load('controller', 'build-electron.py')
image = load('image', 'image-provider.py')
vulkan = load('vulkan', 'vulkan-provider.py')
python = Path(sys.executable).resolve(strict=True)
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp).resolve(); host = root / 'host'; target = root / 'sysroot/usr/pkg'; view = root / 'view'
    databases = {'host': {}, 'target': {}}; selected = {}
    for role, prefix, suffix in (('host', host, '.dylib'), ('target', target, '.so')):
        for name, path, files in (
            ('vulkan-loader-1.4.363.0nb1', 'graphics/vulkan-loader',
             {'lib/libvulkan' + suffix: 'library', 'lib/pkgconfig/vulkan.pc': 'pc'}),
            ('vulkan-headers-1.4.363.0', 'graphics/vulkan-headers',
             {'include/vulkan/vulkan.h': 'header', 'include/vulkan/vulkan_core.h': 'core',
              'include/vk_video/video.h': 'video', 'share/vulkan/registry/vk.xml': 'xml',
              'share/vulkan/registry/reg.py': '#!' + (str(python) if role == 'host' else '/usr/pkg/bin/python3.15') + '\n'})):
            pkg = prefix / 'pkgdb' / name; pkg.mkdir(parents=True); databases[role][path] = [pkg]; manifest = []
            for entry, data in files.items():
                f = prefix / entry; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(data)
                manifest += [entry, '@comment MD5:' + hashlib.md5(data.encode(), usedforsecurity=False).hexdigest()]
                if role == 'host' and (entry.startswith('include/') or entry.endswith('.pc')):
                    selected[str(f)] = {}; link = view / entry; link.parent.mkdir(parents=True, exist_ok=True); link.symlink_to(f)
            (pkg / '+CONTENTS').write_text('\n'.join(manifest) + '\n')
            for item in ('+BUILD_INFO', '+BUILD_VERSION'): (pkg / item).write_text('metadata')
    meta = root / 'meta'; meta.mkdir(); (meta / 'selection.json').write_text(json.dumps({'identity': {'inputs': selected}}))
    options = SimpleNamespace(shared_vulkan=True, host_prefix=host, sysroot=root / 'sysroot', host_buildlink_pkgsrc=root / 'export',
        _common_native_packages=databases['host'], _common_target_packages=databases['target'],
        _compression_catalog={'recipes': {'graphics/vulkan-loader': {}, 'graphics/vulkan-headers': {}}})
    native = SimpleNamespace(host={'os': 'Darwin'}, tool=lambda n: str(python) if n == 'python' else '/selected/' + n)
    process = SimpleNamespace(capture=lambda command, env: SimpleNamespace(stdout=b'1.4.363\n'))
    environment = {'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK': str(meta)}
    with patch.object(controller, 'validate_package_source') as provenance:
        values = vulkan.select(image, controller, options, {'process': process}, native, environment, view)
        assert provenance.call_count == 4 and values['angle_use_custom_libvulkan'] is False
        assert values['emberbsd_vulkan_host_library'].endswith('.dylib') and values['emberbsd_vulkan_target_library'].endswith('.so')
        assert values['emberbsd_vulkan_target_runtime_dir'] == '/usr/pkg/lib'
        assert options.vulkan_registry == (host / 'share/vulkan/registry').resolve()
        header = target / 'include/vulkan/vulkan.h'; header.write_text('foreign')
        try: vulkan.select(image, controller, options, {'process': process}, native, environment, view)
        except ValueError as error: assert 'differs' in str(error)
        else: raise AssertionError('tampered target header accepted')
        header.write_text('header')
        manifest = databases['target']['graphics/vulkan-headers'][0] / '+CONTENTS'
        original_manifest = manifest.read_text()
        original_md5 = hashlib.md5(b'header', usedforsecurity=False).hexdigest()
        other_md5 = hashlib.md5(b'other', usedforsecurity=False).hexdigest()
        header.write_text('other'); manifest.write_text(original_manifest.replace(original_md5, other_md5))
        try: vulkan.select(image, controller, options, {'process': process}, native, environment, view)
        except ValueError as error: assert 'role payload differs' in str(error)
        else: raise AssertionError('different role headers accepted')
        header.write_text('header'); manifest.write_text(original_manifest)
        script = host / 'share/vulkan/registry/reg.py'; old_script = script.read_text()
        manifest = databases['host']['graphics/vulkan-headers'][0] / '+CONTENTS'; original_manifest = manifest.read_text()
        changed_script = '#!/usr/bin/env python3\n'
        manifest.write_text(original_manifest.replace(hashlib.md5(old_script.encode(), usedforsecurity=False).hexdigest(),
                                                      hashlib.md5(changed_script.encode(), usedforsecurity=False).hexdigest()))
        script.write_text(changed_script)
        try: vulkan.select(image, controller, options, {'process': process}, native, environment, view)
        except ValueError as error: assert 'interpreter differs' in str(error)
        else: raise AssertionError('foreign generator interpreter accepted')
        script.write_text(old_script); manifest.write_text(original_manifest)
        (view / 'include/vulkan/vulkan.h').unlink()
        try: vulkan.select(image, controller, options, {'process': process}, native, environment, view)
        except ValueError as error: assert 'not selected' in str(error)
        else: raise AssertionError('unselected native header accepted')
print('PASS Vulkan owned loader/header roles, selected headers and native registry')
