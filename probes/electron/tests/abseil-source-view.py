#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise Chromium's system Abseil mappings without mutating its sources."""
import importlib.util
from pathlib import Path
import tempfile

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_view', owner / 'electron44/files/protobuf-source-view.py')
view = importlib.util.module_from_spec(spec)
spec.loader.exec_module(view)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    source = root / 'source'
    unbundle = source / 'build/linux/unbundle'
    unbundle.mkdir(parents=True)
    (source / '.gn').touch()
    (unbundle / 'replace_gn_files.py').write_text("REPLACEMENTS = {'absl_base': 'third_party/abseil-cpp/absl/base/BUILD.gn', 'absl_log_internal': 'third_party/abseil-cpp/absl/log/internal/BUILD.gn', 'zlib': 'third_party/zlib/BUILD.gn'}\n")
    for group in ('base', 'log/internal'):
        f = source / 'third_party/abseil-cpp/absl' / group / 'BUILD.gn'
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text('original')
        (f.parent / 'example.h').write_text('original header')
        (f.parent / 'internal').mkdir()
        (f.parent / 'internal/only_bundled.inc').write_text('bundled only')
    for name in ('absl_base.gn', 'absl_log_internal.gn'):
        (unbundle / name).write_text('shim_headers("check") { root_path = "." headers = [ "example.h" ] }\n')
    original = source / 'third_party/abseil-cpp/absl/base/BUILD.gn'
    normal = view.create(source, None, root / 'normal')
    assert (normal / 'third_party/abseil-cpp').is_symlink()
    view.verify(source, None, root / 'normal')
    target = view.create(source, None, root / 'selected', system_abseil=True)
    view.verify(source, None, root / 'selected', system_abseil=True)
    replacement = target / 'third_party/abseil-cpp/absl/base/BUILD.gn'
    assert replacement.resolve() == (unbundle / 'absl_base.gn').resolve()
    assert original.read_text() == 'original'
    masked = target / 'third_party/abseil-cpp/absl/base/example.h'
    assert not masked.exists() and (original.parent / 'example.h').read_text() == 'original header'
    assert not (target / 'third_party/abseil-cpp/absl/base/internal/only_bundled.inc').exists()
    assert (original.parent / 'internal/only_bundled.inc').read_text() == 'bundled only'
    masked.write_text('unexpected bundled header')
    try:
        view.verify(source, None, root / 'selected', system_abseil=True)
    except ValueError:
        pass
    else:
        raise AssertionError('masked header was accepted')
    masked.unlink()
    replacement.unlink()
    replacement.symlink_to(original)
    try:
        view.verify(source, None, root / 'selected', system_abseil=True)
    except ValueError:
        pass
    else:
        raise AssertionError('changed shim mapping accepted')
    shim = unbundle / 'absl_base.gn'
    original_shim = shim.read_text()
    for invalid in ('headers += extra', 'root_path = chosen', 'prefix = computed'):
        shim.write_text(original_shim.replace(' }', ' ' + invalid + ' }'))
        try:
            view.create(source, None, root / ('invalid-' + invalid.split()[0]), system_abseil=True)
        except ValueError:
            pass
        else:
            raise AssertionError('non-literal shim assignment accepted: ' + invalid)
    shim.write_text(original_shim.replace('[ "example.h" ]', '[ "example.h" ] + dynamic_headers'))
    try:
        view.create(source, None, root / 'invalid-concatenation', system_abseil=True)
    except ValueError:
        pass
    else:
        raise AssertionError('computed header list accepted')
    for marker in ('$header', r'escape\name'):
        shim.write_text(original_shim.replace('example.h', marker))
        try:
            view.create(source, None, root / ('invalid-string-' + str(len(marker))), system_abseil=True)
        except ValueError:
            pass
        else:
            raise AssertionError('interpolated or escaped shim string accepted')
    shim.write_text(original_shim)
    (unbundle / 'absl_base.gn').unlink()
    try:
        view.create(source, None, root / 'missing', system_abseil=True)
    except ValueError:
        pass
    else:
        raise AssertionError('missing shim accepted')
print('PASS: Chromium Abseil source-view selection and tamper checks')
