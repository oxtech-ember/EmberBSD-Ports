#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the production GTK4 wxFontButton async lifetime and label logic.

GTK/GObject operations and lifetime counters are mocked; production request
ownership, callbacks, destruction, update, and SetNativeFontInfo methods are
extracted verbatim. This is not real GLib/GObject or leak-proof GTK runtime
acceptance, and does not test GUI presentation.
"""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


def between(text, start, end):
    first = text.index(start)
    last = text.index(end, first)
    return text[first:last]


def gtk4_method(source, signature, next_signature):
    whole = between(source, signature, next_signature)
    brace = whole.index('{', len(signature))
    header = whole[:brace + 1]
    directive = '#ifdef __WXGTK4__'
    first = whole.index(directive) + len(directive)
    endings = [i for token in ('#else', '#endif')
               if (i := whole.find(token, first)) >= 0]
    last = min(endings)
    return header + whole[brace + 1:whole.index(directive)] + whole[first:last] + '}'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True,
                        help='production src/gtk/fontpicker.cpp')
    parser.add_argument('--cxx', required=True, help='selected native C++ compiler')
    parser.add_argument('--work-parent', type=Path, required=True,
                        help='existing writable parent for disposable build output')
    parser.add_argument('--cxx-flag', action='append', default=[],
                        help='compiler flag; repeat for each flag')
    args = parser.parse_args()
    source = args.source.read_text()
    production = {
        'PRODUCTION_HELPERS': between(source, 'struct FontDialogRequest', '} // namespace\n#else'),
        'PRODUCTION_DESTRUCTOR': between(source, 'wxFontButton::~wxFontButton()',
                                         '\nvoid wxFontButton::UpdateFont()'),
        'PRODUCTION_UPDATE': gtk4_method(
            source, 'void wxFontButton::UpdateFont()',
            '\nvoid wxFontButton::SetNativeFontInfo'),
        'PRODUCTION_SET_NATIVE': gtk4_method(
            source, 'void wxFontButton::SetNativeFontInfo',
            '\n#endif // wxUSE_FONTPICKERCTRL'),
    }
    harness = Path(__file__).with_name('fontpicker-gtk4-harness.cpp').read_text()
    for marker, body in production.items():
        harness = harness.replace('// ' + marker, body)
    if 'PRODUCTION_' in harness:
        raise RuntimeError('unexpanded production insertion marker')
    with tempfile.TemporaryDirectory(prefix='wx-fontpicker-gtk4-',
                                     dir=args.work_parent) as work:
        cpp = Path(work) / 'fontpicker-contract.cpp'
        exe = Path(work) / 'fontpicker-contract'
        cpp.write_text(harness)
        command = [args.cxx, '-D__WXGTK4__', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                   *args.cxx_flag, str(cpp), '-o', str(exe)]
        print('compile:', shlex.join(command), flush=True)
        subprocess.run(command, check=True)
        subprocess.run([str(exe)], check=True, timeout=20,
                       env={**os.environ, 'G_DEBUG': 'fatal-criticals'})
        print('fontpicker GTK4 lifetime contract: PASS', flush=True)


if __name__ == '__main__':
    main()
