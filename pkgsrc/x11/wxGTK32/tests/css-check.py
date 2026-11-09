#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Generate a real GTK4 parser fixture from wxWidgets' actual CSS generator."""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True,
                        help='Prepared src/gtk/window.cpp to exercise')
    parser.add_argument('--wx-source', type=Path, required=True,
                        help='Prepared wx source root supplying private helpers')
    parser.add_argument('--output', type=Path, required=True,
                        help='Generated standalone C++ fixture')
    args = parser.parse_args()

    source = args.source.read_text()
    method = source.index('void wxWindowGTK::GTKApplyWidgetStyle')
    start = source.index('        GString* css =', method)
    end = source.index('        if (m_styleProvider == NULL', start)
    generator = source[start:end]

    owner = (args.wx_source / 'include/wx/gtk/private/string.h').read_text()
    start = owner.index('class wxGtkString')
    owner = owner[start:owner.index('\n};', start) + 3]

    helper = (args.wx_source / 'include/wx/gtk/private/gtk3-compat.h').read_text()
    start = helper.index('#if defined(__WXGTK4__) ||')
    end = helper.rindex('#endif // _WX_GTK_PRIVATE_COMPAT3_H_')
    helper = helper[start:end]

    template = Path(__file__).with_name('gtk4-style-css.cpp.in').read_text()
    text = template.replace('@STRING_OWNER@', owner)
    text = text.replace('@VERSION_HELPER@', helper)
    text = text.replace('@GENERATOR@', generator)
    args.output.write_text(
        '#include <initializer_list>\n#define __WXGTK4__ 1\n' + text
    )


if __name__ == '__main__':
    main()
