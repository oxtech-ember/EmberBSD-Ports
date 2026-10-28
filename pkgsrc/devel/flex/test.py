#!/usr/bin/env python3
"""Check that cross flex uses gm4 at build time and base m4 at run time."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True


def query(args, recipe, names):
    command = [args.bmake, 'MAKECONF=' + args.makeconf]
    for name in names:
        command += ['-v', name]
    env = dict(os.environ, MAKECONF=args.makeconf)
    out = subprocess.run(command, cwd=recipe, env=env, check=True,
                         capture_output=True, text=True).stdout
    return dict(zip(names, out.split('\n')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True, help='bmake with the host mk files')
    parser.add_argument('--makeconf', required=True, help='aarch64 NetBSD 11 cross MAKECONF')
    parser.add_argument('--recipe', required=True, help='exported devel/flex')
    args = parser.parse_args()
    recipe = Path(args.recipe).resolve(strict=True)
    names = ['USE_CROSS_COMPILE', 'PKG_FAIL_REASON', 'USE_TOOLS', 'MAKE_ENV',
             'TOOLS_PATH.gm4', 'SUBST_FILES.m4path', 'SUBST_SED.m4path']
    v = query(args, recipe, names)
    assert v['USE_CROSS_COMPILE'].lower() == 'yes', v['USE_CROSS_COMPILE']
    # The old recipe failed here: gm4:run is refused in cross builds.
    assert 'gm4:run' not in v['USE_TOOLS'].split(), v['USE_TOOLS']
    assert 'gm4' in v['USE_TOOLS'].split(), v['USE_TOOLS']
    assert not v['PKG_FAIL_REASON'].strip(), v['PKG_FAIL_REASON']
    # The build-time stage1flex reads M4 from the environment.
    assert 'M4=' + v['TOOLS_PATH.gm4'] in v['MAKE_ENV'].split(), v['MAKE_ENV']
    assert v['SUBST_FILES.m4path'].strip() == 'src/config.h', v['SUBST_FILES.m4path']
    host = '#define M4 "%s"\n' % v['TOOLS_PATH.gm4']
    out = subprocess.run('sed ' + v['SUBST_SED.m4path'], shell=True, input=host,
                         check=True, capture_output=True, text=True).stdout
    assert out == '#define M4 "/usr/bin/m4"\n', out
    print('PASS: gm4 is a build tool; the target flex records /usr/bin/m4.')


if __name__ == '__main__':
    main()
