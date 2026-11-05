# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Use Chromium's unbundle wrappers for the verified common compression providers."""
import hashlib
import os
from pathlib import Path

NAMES = ('brotli', 'zstd')
SUPPORTED = NAMES + ('ffmpeg', 'zlib', 'libxml', 'libxslt', 'libwebp', 'dav1d', 'libaom', 'libvpx', 'opus', 'flac', 'openh264', 'pffft', 'expat')


def replacements(view, source, name):
    view.require(name in SUPPORTED, 'unknown unbundled source component')
    expected = 'third_party/' + name + '/BUILD.gn'
    view.require(view.chromium_replacements(source).get(name) == expected,
                 'invalid Chromium compression replacement mapping: ' + name)
    wrapper = source / 'build/linux/unbundle' / (name + '.gn')
    view.require(wrapper.is_file(), 'missing Chromium compression wrapper: ' + name)
    result = {Path('BUILD.gn'): wrapper}
    masks = view.shim_masks(result)
    if name == 'libxml':
        masks.update((Path('src'), Path('linux/include')))
    elif name == 'libxslt':
        masks.add(Path('src'))
    elif name in ('dav1d', 'libaom', 'libvpx', 'opus', 'flac', 'openh264', 'pffft', 'expat'):
        masks.add(Path({'dav1d': 'libdav1d', 'libaom': 'source/libaom',
                        'libvpx': 'source/libvpx', 'opus': 'src', 'flac': 'src', 'openh264': 'src', 'pffft': 'src', 'expat': 'src'}[name]))
        if name == 'expat':
            masks.add(Path('include'))
        if name == 'flac':
            masks.add(Path('include'))
    return result, masks


def verify_view(view, source, destination, names=NAMES):
    source = Path(source).resolve(strict=True)
    root = Path(destination).resolve(strict=True) / 'src/third_party'
    for name in names:
        repl, masks = replacements(view, source, name)
        view.dependency_view(source/'third_party'/name, root/name, repl, masks, verify=True)
    return Path(destination) / 'src'


def activate(view, source, destination, verify_old_whole, names=NAMES, label='compression-components'):
    """Migrate only selected sibling components under the caller's view lock."""
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve(strict=True)
    origin = source / 'third_party'
    # The transaction identity describes the actual selected wrapper contents.
    digest = hashlib.sha256()
    for name in names:
        repl, _ = replacements(view, source, name)
        digest.update(name.encode() + b'\0' + repl[Path('BUILD.gn')].read_bytes() + b'\0')
    def build(name, path):
        repl, masks = replacements(view, source, name)
        view.dependency_view(origin/name, path, repl, masks)
    def verify_new(_migration):
        return verify_view(view, source, destination, names)
    return view.sibling_component_transaction(
        destination, origin, list(names), digest.hexdigest(), label,
        verify_old_whole, build, verify_new)
