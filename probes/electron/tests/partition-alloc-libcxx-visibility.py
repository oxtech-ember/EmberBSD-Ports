#!/usr/bin/env python3
"""Regression: partition_alloc must not force hidden global new/delete with
the shared (non-bundled) libc++; otherwise clang reports 'visibility does not
match previous declaration' in allocator_shim on macOS hosts."""
import json, pathlib, subprocess, sys, tempfile
root = pathlib.Path(__file__).resolve().parents[1]
name = 'partition-alloc-system-libcxx-new-delete-visibility.patch'
series = json.loads((root/'electron44/files/source-series.json').read_text())
paths = [e.get('path') for v in series.values() if isinstance(v, list) for e in v if isinstance(e, dict)]
assert name in paths, 'patch missing from source-series.json'
rel = 'base/allocator/partition_allocator/src/partition_alloc/BUILD.gn'
fixture = '''  }

  config("mac_no_default_new_delete_symbols") {
    if (!is_component_build) {
      # This is already set when we compile libc++, see
      # buildtools/third_party/libc++/BUILD.gn. But it needs to be set here as
      # well, since the shim defines the symbols, to prevent them being
      # exported.
      cflags = [ "-fvisibility-global-new-delete=force-hidden" ]
    }
  }
'''
with tempfile.TemporaryDirectory() as d:
    f = pathlib.Path(d)/rel; f.parent.mkdir(parents=True)
    f.write_text('\n'*356 + fixture)
    patch = sys.argv[1] if len(sys.argv) > 1 else 'patch'
    r = subprocess.run([patch, '-p1', '-F0', '-s', '-i', str(root/'patches'/name)], cwd=d, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    out = f.read_text()
    assert 'if (!is_component_build && use_custom_libcxx) {' in out
    assert 'force-hidden' in out
print('PASS partition-alloc-libcxx-visibility')
