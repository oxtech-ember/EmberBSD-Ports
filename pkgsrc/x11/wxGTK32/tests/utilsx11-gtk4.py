#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise actual GTK4 utility branches with external API mocks, without a display.

The keyboard and WM helper definitions are copied verbatim from --source. The
URI function is retained up to its existing argv fallback boundary: the legacy
browser-search body is replaced by a fallthrough counter, never by another
implementation of GTK/GIO launch. The actual wxGtkObject template supplies RAII.
This checks branching/ownership, not GTK ABI, a real WM or browser execution.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile


def definition(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    level, end = 1, brace + 1
    while level:
        level += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end] + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path, help='Prepared src/unix/utilsx11.cpp')
    parser.add_argument('--wx-include', required=True, type=Path)
    parser.add_argument('--cxx', required=True)
    parser.add_argument('--cxx-flag', action='append', default=[])
    parser.add_argument('--work-parent', required=True, type=Path)
    args = parser.parse_args()
    source = args.source.read_text()
    wm = definition(source, 'static bool wxQueryWMspecSupport(Display*')
    keys = definition(source, 'static bool wxGetKeyStateGTK(wxKeyCode key)')
    uri = definition(source, 'bool\nwxDoLaunchDefaultBrowser(')
    boundary = '\n    const char* argv[4];'
    if uri.count(boundary) != 1:
        raise ValueError('URI fallback boundary changed: inspect the new source')
    uri = uri.split(boundary)[0] + '\n    ++state.fallbacks;\n    return false;\n}\n'
    harness = Path(__file__).with_name('utilsx11-gtk4-harness.cpp').read_text()
    harness = harness.replace('// PRODUCTION_FUNCTIONS', wm + keys + uri)
    with tempfile.TemporaryDirectory(prefix='utilsx11-', dir=args.work_parent) as work:
        cpp = Path(work) / 'contract.cpp'
        cpp.write_text(harness)
        exe = Path(work) / 'contract'
        subprocess.run([args.cxx, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', *args.cxx_flag,
                        '-I' + str(args.wx_include), str(cpp), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True, timeout=20)


if __name__ == '__main__':
    main()
