# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Use Chromium's unbundle wrappers for the verified common compression providers."""
import hashlib
import os
from pathlib import Path

NAMES = ('brotli', 'zstd')
SUPPORTED = NAMES + ('ffmpeg', 'zlib', 'libxml', 'libxslt', 'libwebp', 'dav1d', 'libaom', 'libvpx', 'opus', 'flac', 'openh264', 'pffft', 'expat', 'cpuinfo', 'woff2', 'vulkan-loader', 'vulkan-headers')


def replacements(view, source, name, *, registry=None):
    view.require(name in SUPPORTED, 'unknown unbundled source component')
    nested = name in ('vulkan-loader', 'vulkan-headers')
    expected = 'third_party/' + name + ('/src/BUILD.gn' if nested else '/BUILD.gn')
    view.require(view.chromium_replacements(source).get(name) == expected,
                 'invalid Chromium compression replacement mapping: ' + name)
    wrapper = source / 'build/linux/unbundle' / (name + '.gn')
    view.require(wrapper.is_file(), 'missing Chromium compression wrapper: ' + name)
    result = {Path('src/BUILD.gn') if nested else Path('BUILD.gn'): wrapper}
    masks = view.shim_masks(result)
    if nested:
        vendor = source / 'third_party' / name / 'src'
        view.require(vendor.is_dir() and not vendor.is_symlink(), 'invalid Vulkan source directory')
        keep = {'BUILD.gn'}
        if name == 'vulkan-headers':
            view.require(registry is not None, 'verified Vulkan registry is missing')
            registry = Path(registry).resolve(strict=True)
            view.require(registry.is_dir(), 'verified Vulkan registry is invalid')
            result[Path('src/registry')] = registry
            keep.add('registry')
        masks.update(Path('src') / item.name for item in vendor.iterdir() if item.name not in keep)

    if name == 'libxml':
        masks.update((Path('src'), Path('linux/include')))
    elif name == 'libxslt':
        masks.add(Path('src'))
    elif name in ('dav1d', 'libaom', 'libvpx', 'opus', 'flac', 'openh264', 'pffft', 'expat', 'cpuinfo', 'woff2'):
        masks.add(Path({'dav1d': 'libdav1d', 'libaom': 'source/libaom',
                        'libvpx': 'source/libvpx', 'opus': 'src', 'flac': 'src', 'openh264': 'src', 'pffft': 'src', 'expat': 'src', 'cpuinfo': 'src', 'woff2': 'src'}[name]))
        if name == 'expat':
            masks.add(Path('include'))
        if name == 'flac':
            masks.add(Path('include'))
    return result, masks


def verify_view(view, source, destination, names=NAMES, *, registry=None):
    source = Path(source).resolve(strict=True)
    root = Path(destination).resolve(strict=True) / 'src/third_party'
    for name in names:
        repl, masks = replacements(view, source, name, registry=registry)
        view.dependency_view(source/'third_party'/name, root/name, repl, masks, verify=True)
    return Path(destination) / 'src'


def activate(view, source, destination, verify_old_whole, names=NAMES, label='compression-components', *, registry=None):
    """Migrate only selected sibling components under the caller's view lock."""
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve(strict=True)
    origin = source / 'third_party'
    # The transaction identity describes the actual selected wrapper contents.
    digest = hashlib.sha256()
    for name in names:
        repl, _ = replacements(view, source, name, registry=registry)
        wrapper = Path('src/BUILD.gn') if name in ('vulkan-loader', 'vulkan-headers') else Path('BUILD.gn')
        digest.update(name.encode() + b'\0' + repl[wrapper].read_bytes() + b'\0')
        if name == 'vulkan-headers':
            digest.update(str(repl[Path('src/registry')]).encode() + b'\0')
    def build(name, path):
        repl, masks = replacements(view, source, name, registry=registry)
        view.dependency_view(origin/name, path, repl, masks)
    def verify_new(_migration):
        if registry is None:
            return verify_view(view, source, destination, names)
        return verify_view(view, source, destination, names, registry=registry)
    return view.sibling_component_transaction(
        destination, origin, list(names), digest.hexdigest(), label,
        verify_old_whole, build, verify_new)
