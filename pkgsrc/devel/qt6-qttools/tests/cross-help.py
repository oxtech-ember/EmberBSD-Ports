#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that cross qttools does not need the host qhelpgenerator.

A cross Qt build imports every TOOLS_TARGET Tools tool from the host
Qt6ToolsTools package. QtToolHelpers.cmake stops the configure with
"Failed to find the host tool Qt6::qhelpgenerator" when the host package
does not have it. The host Qt has tools only, so the cross recipe must
not add src/assistant/qhelpgenerator, and the PLIST must not list it.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HELP = re.compile(r'(QtHelp|Qt6Help|libQt6Help|Help\.json|qhelpgenerator|bin/assistant|'
                  r'qt6help_metatypes|qt_lib_help|plugins/help/)')


def host_has_qhelpgenerator(host_qt):
    files = sorted((host_qt / 'lib/cmake/Qt6ToolsTools').glob('Qt6ToolsToolsTargets*.cmake'))
    if not files:
        raise SystemExit('FAIL: no Qt6ToolsTools package in ' + str(host_qt))
    return any('qhelpgenerator' in f.read_text() for f in files)


def adds_qhelpgenerator(source, arguments):
    """Follow src/assistant/CMakeLists.txt with the recipe's FEATURE values."""
    text = (source / 'src/assistant/CMakeLists.txt').read_text()
    guard = text.find('if(NOT QT_FEATURE_assistant)\n    return()')
    tool = text.find('add_subdirectory(qhelpgenerator)')
    lite = text.find('if(NOT QT_FEATURE_fullqthelp)')
    if min(guard, tool, lite) < 0 or not lite < guard < tool:
        raise SystemExit('FAIL: upstream src/assistant/CMakeLists.txt changed')
    features = dict(re.findall(r'-DFEATURE_(assistant|fullqthelp)(?::BOOL)?=(\w+)', arguments))
    if features.get('fullqthelp', 'ON').upper() != 'ON':
        return False, 'the reduced QtHelp library is built'
    return features.get('assistant', 'ON').upper() != 'OFF', None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cross', nargs=3, type=Path, required=True, metavar=('MAKE', 'MAKECONF', 'PKGSRC'),
                        help='cross bmake wrapper, cross MAKECONF and the exported pkgsrc tree')
    parser.add_argument('--host-qt', type=Path, required=True, help='host Qt prefix, for example PREFIX/qt6')
    parser.add_argument('--source', type=Path, required=True, help='extracted qttools source')
    args = parser.parse_args()
    make, makeconf, pkgsrc = args.cross
    recipe = pkgsrc / 'devel/qt6-qttools'
    result = subprocess.run([str(make), '-v', 'PKG_FAIL_REASON', '-v', 'CMAKE_CONFIGURE_ARGS', '-v', 'PLIST.help'],
                            cwd=recipe, env=dict(os.environ, MAKECONF=str(makeconf)),
                            capture_output=True, text=True)
    values = result.stdout.splitlines()
    if result.returncode != 0 or len(values) != 3 or values[0].strip():
        print('FAIL: cross devel/qt6-qttools does not evaluate: ' + (result.stdout + result.stderr).strip()[:300])
        return 1
    _, arguments, plist_help = values
    if not host_has_qhelpgenerator(args.host_qt):
        adds, problem = adds_qhelpgenerator(args.source, arguments)
        if problem:
            print('FAIL: cross qttools: ' + problem)
            return 1
        if adds:
            print('FAIL: cross configure stops: Failed to find the host tool Qt6::qhelpgenerator')
            return 1
    unguarded = [line for line in (recipe / 'PLIST').read_text().splitlines()
                 if HELP.search(line) and not line.startswith('${PLIST.help}')]
    if plist_help.strip() or unguarded:
        print('FAIL: cross PLIST lists Assistant or QtHelp: ' + ' '.join(unguarded[:3]) + ' PLIST.help=' + plist_help)
        return 1
    print('PASS: cross qttools builds without Assistant, QtHelp and the host qhelpgenerator')
    return 0


if __name__ == '__main__':
    sys.exit(main())
