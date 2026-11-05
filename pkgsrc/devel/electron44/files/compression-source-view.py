# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Use Chromium's unbundle wrappers for the verified common compression providers."""
import hashlib
import os
from pathlib import Path

NAMES = ('brotli', 'zstd')


def replacements(view, source, name):
    view.require(name in NAMES, 'unknown compression source component')
    expected = 'third_party/' + name + '/BUILD.gn'
    view.require(view.chromium_replacements(source).get(name) == expected,
                 'invalid Chromium compression replacement mapping: ' + name)
    wrapper = source / 'build/linux/unbundle' / (name + '.gn')
    view.require(wrapper.is_file(), 'missing Chromium compression wrapper: ' + name)
    result = {Path('BUILD.gn'): wrapper}
    return result, view.shim_masks(result)


def verify_view(view, source, destination):
    source = Path(source).resolve(strict=True)
    root = Path(destination).resolve(strict=True) / 'src/third_party'
    for name in NAMES:
        repl, masks = replacements(view, source, name)
        view.dependency_view(source/'third_party'/name, root/name, repl, masks, verify=True)
    return Path(destination) / 'src'


def activate(view, source, destination, verify_old_whole):
    """Migrate only selected sibling components under the caller's view lock."""
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve(strict=True)
    origin = source / 'third_party'
    # The transaction identity describes the actual selected wrapper contents.
    digest = hashlib.sha256()
    for name in NAMES:
        repl, _ = replacements(view, source, name)
        digest.update(name.encode() + b'\0' + repl[Path('BUILD.gn')].read_bytes() + b'\0')
    def build(name, path):
        repl, masks = replacements(view, source, name)
        view.dependency_view(origin/name, path, repl, masks)
    def verify_new(_migration):
        return verify_view(view, source, destination)
    return view.sibling_component_transaction(
        destination, origin, list(NAMES), digest.hexdigest(), 'compression-components',
        verify_old_whole, build, verify_new)
