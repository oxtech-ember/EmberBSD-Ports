#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check the owner's Blink buffer sentinel against annotation include order."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[3]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', required=True, type=Path, help='Unpatched Chromium literal_buffer.h')
p.add_argument('--container-source', required=True, type=Path, help='Chromium container_annotations.h with owner sentinel')
p.add_argument('--patch-tool', required=True, type=Path)
a = p.parse_args()
cxx = os.environ.get('CXX')
if not cxx:
    p.error('CXX must select the native SDK C++ compiler')
owner = (root / 'probes/electron/patches/blink-wtf-container-annotation-sentinel.patch').read_text()
marker = '--- a/third_party/blink/renderer/core/html/parser/literal_buffer.h\n'
if owner.count(marker) != 1:
    raise SystemExit('expected one literal_buffer owner patch')
section = marker + owner.split(marker, 1)[1].split('\n--- a/', 1)[0] + '\n'
with tempfile.TemporaryDirectory() as td:
    d = Path(td)
    header = d / 'third_party/blink/renderer/core/html/parser/literal_buffer.h'
    header.parent.mkdir(parents=True)
    header.write_bytes(a.source.read_bytes())
    patch = d / 'literal.patch'
    patch.write_text(section)
    subprocess.run([str(a.patch_tool), '-s', '-p1', '-i', str(patch)], cwd=d, check=True)
    text = header.read_text()
    original = a.source.read_text()
    if '#include "third_party/blink/renderer/platform/wtf/container_annotations.h"' not in text:
        raise SystemExit('literal buffer must include sentinel owner header')
    m = re.search(r'(?m)^#ifdef WTF_ANNOTATE_CONTIGUOUS_CONTAINER\n#define BUFFER_INLINE_CAPACITY 0\n#else\n#define BUFFER_INLINE_CAPACITY kInlineSize\n#endif', text)
    if not m:
        raise SystemExit('owner inline-capacity guard not found')
    container = a.container_source.read_text()
    condition = re.search(r'(?m)^#if defined\(ADDRESS_SANITIZER\).*?defined\(ARCH_CPU_X86_64\)', container, re.S)
    if not condition or '#define WTF_ANNOTATE_CONTIGUOUS_CONTAINER' not in container:
        raise SystemExit('owner sentinel condition not found')
    sentinel = condition.group() + '\n#define WTF_ANNOTATE_CONTIGUOUS_CONTAINER\n#endif\n'
    old = re.search(r'(?m)^#ifdef ANNOTATE_CONTIGUOUS_CONTAINER\n#define BUFFER_INLINE_CAPACITY 0\n#else\n#define BUFFER_INLINE_CAPACITY kInlineSize\n#endif', original)
    if not old:
        raise SystemExit('original annotation-dependent guard not found')
    annotation = '#define ANNOTATE_CONTIGUOUS_CONTAINER(...)\n'
    layout = ('template<int kInlineSize> struct Buffer { char data[BUFFER_INLINE_CAPACITY + 1]; };\n'
              'static_assert(sizeof(Buffer<256>) == 257);\n')
    for before in (False, True):
        src = d / 'baseline.cc'
        src.write_text((annotation if before else '') + old.group() + '\n' +
                       ('' if before else annotation) + layout)
        result = subprocess.run([cxx, '-std=c++17', '-fsyntax-only', str(src)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if (result.returncode == 0) != (not before):
            raise SystemExit('original guard did not reproduce include-order mismatch')
    # Exercise the real owner condition and real patched guard with a minimal
    # template: no Chromium tree build is needed for this layout contract.
    for asan in (False, True):
        for platform in ('linux', 'chromeos', 'bsd', 'other'):
            for x64 in (False, True):
                for annotations in (False, True):
                    for order in ('before', 'after'):
                        annotation = '#define ANNOTATE_CONTIGUOUS_CONTAINER(...)\n' if annotations else ''
                        defs = (('#define ADDRESS_SANITIZER 1\n' if asan else '') +
                                ('#define ARCH_CPU_X86_64 1\n' if x64 else '') +
                                '#define BUILDFLAG(x) x\n' +
                                ''.join(f'#define IS_{name.upper()} {int(platform == name)}\n' for name in ('linux', 'chromeos', 'bsd')))
                        expected = 1 if asan and x64 and platform != 'other' else 257
                        src = d / 'case.cc'
                        src.write_text(defs + (annotation if order == 'before' else '') + sentinel +
                                       m.group() + '\n' + (annotation if order == 'after' else '') +
                                       'template<int kInlineSize> struct Buffer { char data[BUFFER_INLINE_CAPACITY + 1]; };\n' +
                                       f'static_assert(sizeof(Buffer<256>) == {expected});\n')
                        subprocess.run([cxx, '-std=c++17', *(['-fsanitize=address'] if asan else []),
                                        '-fsyntax-only', str(src)], check=True)
print('Blink buffer sentinel: supported and unsupported ASan targets, annotation include order PASS')
