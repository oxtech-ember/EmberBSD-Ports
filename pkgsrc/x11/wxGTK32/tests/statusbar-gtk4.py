#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check actual GTK4 statusbar helper, handlers and grip drawing without a display.

Production functions are extracted verbatim; the preprocessor selects GTK4.
External GDK calls and wx event/DC primitives are mocked. This verifies native
input forwarding, hit geometry and emitted logical drawing coordinates, not
physical pointer delivery, a real WM operation or pixel rendering.
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
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cxx', required=True)
    parser.add_argument('--cxx-flag', action='append', default=[])
    parser.add_argument('--work-parent', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.read_text()
    signatures = ['static bool wxGTKBeginStatusDrag(',
                  'wxRect wxStatusBarGeneric::GetSizeGripRect()',
                  'void wxStatusBarGeneric::OnLeftDown(',
                  'void wxStatusBarGeneric::OnRightDown(',
                  'void wxStatusBarGeneric::OnPaint(']
    harness = Path(__file__).with_name('statusbar-gtk4-harness.cpp').read_text()
    harness = harness.replace('// PRODUCTION_FUNCTIONS', '\n'.join(definition(source, name) for name in signatures))
    with tempfile.TemporaryDirectory(prefix='statusbar-', dir=args.work_parent) as work:
        cpp, exe = Path(work)/'contract.cpp', Path(work)/'contract'
        cpp.write_text(harness)
        subprocess.run([args.cxx, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', *args.cxx_flag, str(cpp), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True, timeout=20)


if __name__ == '__main__':
    main()
