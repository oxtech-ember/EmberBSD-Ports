#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise actual GTK4 Cairo context methods with native Cairo/Pango/GLib.

Only wx window/DC primitives and GDK surface/frame calls are mocked. Production
constructor, destructor, factories, initialization, save/restore and wxGtkObject
are used verbatim. This is a lifetime/routing check, not GUI rendering acceptance.
"""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


def definition(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth, end = 1, brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end] + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--wx-source', type=Path, required=True)
    parser.add_argument('--cxx', required=True)
    parser.add_argument('--pkg-config', required=True)
    parser.add_argument('--cxx-flag', action='append', default=[])
    parser.add_argument('--work-parent', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.read_text()
    names = ['wxCairoContext::wxCairoContext(wxGraphicsRenderer* renderer, GdkSurface* surface)',
             'wxCairoContext::wxCairoContext( wxGraphicsRenderer* renderer, wxWindow *window)',
             'wxCairoContext::wxCairoContext( wxGraphicsRenderer* renderer, cairo_t *context )',
             'wxCairoContext::~wxCairoContext()', 'void wxCairoContext::Init(',
             'void wxCairoContext::PushState()', 'void wxCairoContext::PopState()',
             'wxGraphicsContext * wxCairoRenderer::CreateContextFromNativeWindow(',
             'wxGraphicsContext * wxCairoRenderer::CreateMeasuringContext()']
    harness = Path(__file__).with_name('cairo-gtk4-harness.cpp').read_text()
    harness = harness.replace('// PRODUCTION_METHODS', '\n'.join(definition(source,n) for n in names))
    harness = harness.replace('// PRODUCTION_GTK_OBJECT',
        (args.wx_source/'include/wx/gtk/private/object.h').read_text())
    scoped = definition((args.wx_source/'include/wx/scopedptr.h').read_text(),
                        'template <class T>\nclass wxScopedPtr') + ';\n'
    harness = harness.replace('// PRODUCTION_SCOPED_PTR', scoped)
    flags = shlex.split(subprocess.check_output([args.pkg_config,'--cflags','--libs',
                                               'pangocairo','gobject-2.0'],text=True))
    with tempfile.TemporaryDirectory(prefix='wx-cairo-',dir=args.work_parent) as work:
        cpp,exe=Path(work)/'contract.cpp',Path(work)/'contract'
        cpp.write_text(harness)
        subprocess.run([args.cxx,'-std=c++17','-Wall','-Wextra','-Werror',*args.cxx_flag,
                        str(cpp),*flags,'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True,timeout=20,
                       env={**os.environ,'G_DEBUG':'fatal-criticals'})


if __name__ == '__main__':
    main()
