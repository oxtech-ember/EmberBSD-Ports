#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Origin: EmberBSD (AI-assisted).
"""Parse real C++ through the selected Clang Python bindings and libclang."""
import argparse
from pathlib import Path
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--bindings', type=Path, required=True)
p.add_argument('--libclang', type=Path, required=True)
a = p.parse_args()
assert a.bindings.is_absolute() and a.libclang.is_absolute()
sys.path.insert(0, str(a.bindings))
from clang import cindex
cindex.Config.set_library_file(str(a.libclang))
with tempfile.TemporaryDirectory(prefix='clang-python-') as temp:
    source = Path(temp) / 'input.cc'
    source.write_text('struct SharedBinding { int value; };\n')
    tu = cindex.Index.create().parse(str(source), args=['-x', 'c++', '-std=c++17'])
    assert not [d for d in tu.diagnostics if d.severity >= d.Error]
    assert any(c.spelling == 'SharedBinding' and c.kind == cindex.CursorKind.STRUCT_DECL
               for c in tu.cursor.get_children())
print('common Clang Python bindings and selected libclang parse PASS')
