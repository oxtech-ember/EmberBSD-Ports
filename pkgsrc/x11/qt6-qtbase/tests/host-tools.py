#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the native Qt host-tools packages: dependencies and installed tools."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
# Cross Qt builds need only these native tools; the GUI stack must not be built for them.
RECIPES = {
    'x11/qt6-qtbase': ('PKG_OPTIONS.qt6-qtbase=host-tools -dbus',
                       ('qt6/bin/qtpaths', 'qt6/libexec/moc', 'qt6/libexec/rcc', 'qt6/libexec/uic',
                        'qt6/lib/cmake/Qt6CoreTools/Qt6CoreToolsConfig.cmake',
                        'qt6/lib/cmake/Qt6GuiTools/Qt6GuiToolsConfig.cmake',
                        'qt6/lib/cmake/Qt6WidgetsTools/Qt6WidgetsToolsConfig.cmake')),
    'devel/qt6-qttools': ('PKG_OPTIONS.qt6-qttools=host-tools',
                          ('qt6/bin/lrelease', 'qt6/bin/lconvert', 'qt6/libexec/qtattributionsscanner',
                           'qt6/lib/cmake/Qt6LinguistTools/Qt6LinguistToolsConfig.cmake',
                           'qt6/lib/cmake/Qt6ToolsTools/Qt6ToolsToolsConfig.cmake')),
}
REFUSED = ('freetype2', 'harfbuzz', 'fontconfig', 'libX11', 'libxcb', 'openssl', 'icu', 'glib2',
           'wayland', 'MesaLib', 'qt6-qtdeclarative', 'litehtml', 'libjpeg', 'png', 'sqlite3')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', type=Path, required=True,
                        help='native Ports make wrapper: MAKE PKGPATH [VAR=value] -v VARIABLE')
    parser.add_argument('--prefix', type=Path, help='also check the tools installed in this prefix')
    parser.add_argument('--cross', nargs=3, type=Path, metavar=('MAKE', 'MAKECONF', 'PKGSRC'),
                        help='also check that the cross recipes still evaluate without the option')
    args = parser.parse_args()
    for pkgpath in RECIPES if args.cross else ():
        make, makeconf, pkgsrc = args.cross
        result = subprocess.run([str(make), '-v', 'PKG_FAIL_REASON'], cwd=pkgsrc / pkgpath,
                                env=dict(os.environ, MAKECONF=str(makeconf)), capture_output=True, text=True)
        if result.returncode != 0 or result.stdout.strip():
            print('FAIL: cross ' + pkgpath + ': ' + (result.stdout + result.stderr).strip()[:300])
            return 1
    for pkgpath, (option, files) in RECIPES.items():
        result = subprocess.run([str(args.make), pkgpath, option, '-v', 'PKG_FAIL_REASON',
                                 '-v', 'PLIST_SRC', '-v', 'DEPENDS', '-v', 'BUILD_DEPENDS'],
                                capture_output=True, text=True)
        values = result.stdout.splitlines()
        if result.returncode != 0 or len(values) != 4:
            print('FAIL: ' + pkgpath + ' does not evaluate with ' + option + ': ' + result.stderr.strip()[:300])
            return 1
        failure, plist, *depends = values
        names = [word.split(':', 1)[0] for word in ' '.join(depends).split()]
        found = sorted({name for name in REFUSED for word in names
                        if word.startswith((name + '>', name + '-[', name + '>=', name + '-'))})
        if failure.strip() or not plist.strip().endswith('/PLIST.host-tools') or found:
            print('FAIL: ' + pkgpath + ' host-tools: ' + failure + ' | ' + plist + ' | ' + ' '.join(found))
            return 1
        if args.prefix:
            missing = [name for name in files if not (args.prefix / name).is_file()]
            if missing:
                print('FAIL: ' + pkgpath + ' did not install ' + ' '.join(missing))
                return 1
    print('PASS: Qt host-tools packages build only the native tools')
    return 0


if __name__ == '__main__':
    sys.exit(main())
