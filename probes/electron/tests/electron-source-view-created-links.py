#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify selected native source link refresh and failure handling."""
import argparse
import importlib.util
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--host-prefix', type=Path, required=True)
parser.add_argument('--sdk-source', type=Path, required=True)
args = parser.parse_args()
owner = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files'
def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, owner / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj
build = module('build', 'build-electron.py')
view = module('view', 'protobuf-source-view.py')
sdk = build.load_sdk(args.sdk_source)
native = sdk['host_prefix'].load_host_prefix(args.host_prefix, required_roles=('dsymutil',))
assert native.host['os'] == 'Darwin'
selected = Path(native.tool('dsymutil')).resolve(strict=True)

def rejected(call):
    try:
        call()
    except (ValueError, OSError):
        return
    raise AssertionError('unexpected acceptance')

with tempfile.TemporaryDirectory(prefix='electron-created-link-') as directory:
    root = Path(directory).resolve()
    workspace = root / 'workspace'
    source = workspace / 'src'
    (source / 'third_party').mkdir(parents=True)
    (source / 'tools/clang/dsymutil/bin').mkdir(parents=True)
    (source / '.gn').write_text('fixture')
    (source / 'tools/clang/dsymutil/bin/tool.sha1').write_text('fixture')
    dest = root / 'source-view'
    view.create(source, None, dest)
    bindings = build.ensure_host_dsymutil(workspace, native)
    src_link = source / 'tools/clang/dsymutil/bin/dsymutil'
    dst_link = dest / 'src/tools/clang/dsymutil/bin/dsymutil'
    assert bindings == {str(src_link): str(selected)} and os.readlink(src_link) == str(selected)
    rejected(lambda: view.verify(source, None, dest))
    rejected(lambda: view._refresh_leaves(source, None, dest, {}, created_links={str(src_link): '/foreign'}))
    assert not os.path.lexists(dst_link)
    view._refresh_leaves(source, None, dest, {}, created_links=bindings)
    view.verify(source, None, dest)
    assert dst_link.is_symlink() and os.readlink(dst_link) == str(selected)
    # Resume an interrupted refresh marker for the same explicitly bound link.
    dst_link.unlink()
    marker = view._refresh_marker(dest)
    marker.write_text('source-view-leaves-v1\n')
    view._refresh_leaves(source, None, dest, {}, created_links=bindings)
    assert not marker.exists() and os.readlink(dst_link) == str(selected)
    # Another missing symlink cannot use this binding.
    extra = src_link.parent / 'other'
    extra.symlink_to(selected)
    rejected(lambda: view._refresh_leaves(source, None, dest, {}, created_links=bindings))
    assert not os.path.lexists(dst_link.parent / 'other')
    extra.unlink()
    # Source replacement during installation rolls back the owned view leaf.
    dst_link.unlink()
    real_link = os.link
    def swap(*a, **kw):
        result = real_link(*a, **kw)
        src_link.unlink()
        src_link.symlink_to('/foreign')
        return result
    with patch.object(view.os, 'link', swap):
        rejected(lambda: view._refresh_leaves(source, None, dest, {}, created_links=bindings))
    assert not os.path.lexists(dst_link) and os.readlink(src_link) == '/foreign'
    rejected(lambda: build.ensure_host_dsymutil(workspace, native))
    src_link.unlink()
    src_link.symlink_to(selected)
    view._refresh_leaves(source, None, dest, {}, created_links=bindings)
    view.verify(source, None, dest)
print('PASS: selected dsymutil source link refresh and refusal cases')
