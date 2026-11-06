# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Select the common Vulkan loader, headers and host generator registry."""
import hashlib
import json
import re
import shlex
from pathlib import Path, PurePosixPath

LOADER = ('graphics/vulkan-loader', 'vulkan-loader', (1, 4, 363, 0, 1),
          ('libvulkan',), ('vulkan',), ())
HEADER_PATH = 'graphics/vulkan-headers'
HEADER_FLOOR = (1, 4, 363, 0, 0)


def selected_entries(controller, package):
    lines = (package / '+CONTENTS').read_text().splitlines()
    entries = {}
    prefixes = ('include/vulkan/', 'include/vk_video/', 'share/vulkan/registry/')
    for index, entry in enumerate(lines):
        if not entry.startswith(prefixes):
            continue
        path = PurePosixPath(entry)
        controller.require(not path.is_absolute() and '..' not in path.parts and str(path) == entry and entry not in entries,
                           'invalid Vulkan package input: ' + entry)
        controller.require(index + 1 < len(lines) and re.fullmatch(r'@comment MD5:[0-9a-f]{32}', lines[index + 1]),
                           'Vulkan package input has no checksum: ' + entry)
        entries[entry] = lines[index + 1].split(':', 1)[1]
    for entry in ('include/vulkan/vulkan.h', 'include/vulkan/vulkan_core.h',
                  'share/vulkan/registry/vk.xml', 'share/vulkan/registry/reg.py'):
        controller.require(entry in entries, 'Vulkan package input is missing: ' + entry)
    controller.require(any(entry.startswith('include/vk_video/') for entry in entries),
                       'Vulkan video headers are missing')
    return entries


def read_selected(controller, path, expected):
    before = path.stat(); content = path.read_bytes(); after = path.stat()
    stable = lambda v: (v.st_dev, v.st_ino, v.st_mode, v.st_size, v.st_mtime_ns, v.st_ctime_ns)
    controller.require(stable(before) == stable(after) and
                       hashlib.md5(content, usedforsecurity=False).hexdigest() == expected,
                       'Vulkan package input changed: ' + str(path))
    return content


def select(image, controller, options, sdk, native, environment, buildlink):
    if not getattr(options, 'shared_vulkan', False):
        return {}
    hosts = options._common_native_packages.get(HEADER_PATH, [])
    targets = options._common_target_packages.get(HEADER_PATH, [])
    controller.require(len(hosts) == len(targets) == 1, 'Vulkan headers are missing in a toolchain role')
    host_entries, target_entries = selected_entries(controller, hosts[0]), selected_entries(controller, targets[0])
    controller.require(host_entries.keys() == target_entries.keys(), 'Vulkan role header/registry inventories differ')
    header_provider = (HEADER_PATH, 'vulkan-headers', HEADER_FLOOR, (), (), tuple(sorted(host_entries)))
    controller.require(not header_provider[3] and not header_provider[4] and header_provider[5],
                       'invalid header-only Vulkan provider')
    values = image.select_roles(controller, options, sdk, native, environment, buildlink,
                                {'vulkan': LOADER, 'vulkan_headers': header_provider},
                                {'emberbsd_common_vulkan': True, 'angle_use_custom_libvulkan': False},
                                'EMBERBSD_VULKAN_SOURCE_SHA256')
    host_prefix = Path(options.host_prefix).resolve(strict=True)
    target_root = Path(options.sysroot).resolve(strict=True)
    target_prefix = (target_root / 'usr/pkg').resolve(strict=True)
    for entry in host_entries:
        if entry.startswith(('include/vulkan/', 'include/vk_video/')) or entry.endswith('.xml'):
            left = read_selected(controller, host_prefix / entry, host_entries[entry])
            right = read_selected(controller, target_prefix / entry, target_entries[entry])
            controller.require(hashlib.sha256(left).digest() == hashlib.sha256(right).digest(),
                               'Vulkan role payload differs: ' + entry)
    selected = json.loads((Path(environment['EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK']) / 'selection.json').read_text())['identity']['inputs']
    for entry in host_entries:
        if entry.startswith(('include/vulkan/', 'include/vk_video/')):
            link = Path(buildlink) / entry
            actual = (host_prefix / entry).resolve(strict=True)
            controller.require(str(actual) in selected and link.is_file() and link.resolve(strict=True) == actual,
                               'native Vulkan header is not selected: ' + entry)
    for role, prefix in (('host', host_prefix), ('target', target_prefix)):
        libraries = values.pop('emberbsd_vulkan_' + role + '_libraries')
        controller.require(len(libraries) == 1, 'Vulkan role must select one loader')
        library = Path(libraries[0]).resolve(strict=True)
        values['emberbsd_vulkan_' + role + '_library'] = str(library)
        if role == 'host':
            runtime_dir = str(library.parent)
        else:
            controller.require(library.parent.is_relative_to(target_root), 'Vulkan loader escapes target sysroot')
            runtime_dir = '/' + library.parent.relative_to(target_root).as_posix()
        values['emberbsd_vulkan_' + role + '_runtime_dir'] = runtime_dir
        values.pop('emberbsd_vulkan_headers_' + role + '_libraries')
        values['emberbsd_vulkan_headers_' + role + '_include'] = str(prefix / 'include')
    registry = (host_prefix / 'share/vulkan/registry').resolve(strict=True)
    controller.require(registry.is_dir() and registry.is_relative_to(host_prefix), 'Vulkan registry escapes host prefix')
    python = Path(native.tool('python')).resolve(strict=True)
    for entry in host_entries:
        if not entry.startswith('share/vulkan/registry/') or not entry.endswith('.py'):
            continue
        path = host_prefix / entry
        content = read_selected(controller, path, host_entries[entry])
        if content.startswith(b'#!'):
            words = shlex.split(content.splitlines()[0][2:].decode('utf-8'))
            controller.require(words and Path(words[0]).resolve(strict=True) == python,
                               'Vulkan registry interpreter differs: ' + entry)
    options.vulkan_registry = registry
    return values
