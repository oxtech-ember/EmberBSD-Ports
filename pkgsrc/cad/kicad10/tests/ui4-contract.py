#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extract actual KiCad GTK4 platform methods into a narrow runtime fixture."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.read_text()
    methods = []
    for declaration in (
        'void KIPLATFORM::UI::GetInfoBarColours(',
        'void KIPLATFORM::UI::LargeChoiceBoxHack(',
        'void KIPLATFORM::UI::EllipsizeChoiceBox(',
        'double KIPLATFORM::UI::GetPixelScaleFactor(',
        'bool KIPLATFORM::UI::AllowIconsInMenus(',
    ):
        start = source.index(declaration)
        end = source.index('\n}', start) + 2
        methods.append(source[start:end])
    template = Path(__file__).with_name('ui4-contract.cpp.in').read_text()
    args.output.write_text(template.replace('@METHODS@', '\n\n'.join(methods)))


if __name__ == '__main__':
    main()
