#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Track the packaged Qt runtime plugin fix.
"""Check Qtbase package revisions and the target runtime dependency contract."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
recipe = (root / 'pkgsrc/x11/qt6-qtbase/Makefile').read_text()
runtime_buildlink = (root / 'pkgsrc/x11/qt6-qtbase/buildlink3.mk').read_text()
devel_buildlink = (root / 'pkgsrc/x11/qt6-qtbase-devel/buildlink3.mk').read_text()
host_tools = (root / 'pkgsrc/x11/qt6-qtbase/host-tools.mk').read_text()
runtime_plist = (root / 'pkgsrc/x11/qt6-qtbase/PLIST.runtime').read_text()


def require(condition, message):
    if not condition:
        raise SystemExit('FAIL: ' + message)


require(re.search(r'^PKGREVISION=\s*18\s*$', recipe, re.M),
        'the native Qtbase package must carry runtime plugin revision 18')
require(re.search(r'^PKGREVISION=\s*9\s*$', recipe, re.M)
        and re.search(r'PKGREVISION\}\s*!=\s*"?9"?', recipe),
        'the cross runtime package and its recipe guard must use revision 9')
require(re.search(r'^PKGREVISION=\s*11\s*$', recipe, re.M)
        and re.search(r'PKGREVISION\}\s*!=\s*11', recipe),
        'the cross SDK package and its recipe guard must use revision 11')
require('qt6-qtbase-${QTVERSION}nb9:../../x11/qt6-qtbase' in recipe
        and 'qt6-qtbase<${QTVERSION}nb9' in recipe,
        'the SDK package must depend on and conflict against runtime revision 9')
require(runtime_buildlink.count('qt6-qtbase>=6.12.0nb9') == 2,
        'cross runtime consumers must require runtime revision 9')
require(devel_buildlink.count('qt6-qtbase-devel>=6.12.0nb11') == 2,
        'cross SDK consumers must require SDK revision 11')
require('qt6-qtbase>=6.12.0nb18:../../x11/qt6-qtbase' in host_tools,
        'native host tools must depend on the bumped package revision')
require('${PLIST.bsdfb}qt6/plugins/platforms/libqbsdfb.so' in runtime_plist,
        'the revised cross runtime package must contain the BsdFB plugin')

print('PASS: Qtbase runtime, SDK, and host-tools revisions match their package contract')
