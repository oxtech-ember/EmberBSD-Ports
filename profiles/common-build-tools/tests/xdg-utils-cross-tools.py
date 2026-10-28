#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that cross xdg-utils scripts use NetBSD 11 base grep and sed."""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
KEYS = ('USE_CROSS_COMPILE', 'PKG_FAIL_REASON', 'USE_TOOLS', 'SUBST_SED.gsed')


def query(args, recipe):
    command = [args.bmake, 'MAKECONF=' + args.cross_makeconf]
    for key in KEYS:
        command += ['-v', key]
    env = dict(os.environ, MAKECONF=args.cross_makeconf)
    out = subprocess.run(command, cwd=recipe, env=env, check=True,
                         capture_output=True, text=True).stdout
    return dict(zip(KEYS, out.split('\n')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkgsrc', required=True, help='exported Ports pkgsrc tree')
    parser.add_argument('--cross-makeconf', required=True, help='NetBSD 11 cross mk.conf')
    parser.add_argument('--bmake', required=True)
    parser.add_argument('--patch', default='patch', help='patch program')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    pkgsrc = Path(args.pkgsrc).resolve(strict=True)
    repair = root / 'profiles/common-build-tools/patches/xdg-utils-cross-tools.patch'
    upstream = (root / 'upstream/pkgsrc/misc/xdg-utils/Makefile').read_text(encoding='utf-8')
    with tempfile.TemporaryDirectory() as temp:
        tree = Path(temp) / 'pkgsrc'
        (tree / 'misc').mkdir(parents=True)
        for item in pkgsrc.iterdir():
            if item.name != 'misc':
                (tree / item.name).symlink_to(item, target_is_directory=item.is_dir())
        for item in (pkgsrc / 'misc').iterdir():
            if item.name != 'xdg-utils':
                (tree / 'misc' / item.name).symlink_to(item, target_is_directory=True)
        recipe = tree / 'misc/xdg-utils'
        recipe.mkdir()
        for name in ('DESCR', 'PLIST', 'distinfo'):
            (recipe / name).symlink_to(root / 'upstream/pkgsrc/misc/xdg-utils' / name)
        (recipe / 'Makefile').write_text(upstream, encoding='utf-8')
        old = query(args, recipe)
        assert old['USE_CROSS_COMPILE'].lower() == 'yes', old
        # The unpatched recipe fails: pkgsrc refuses ggrep:run and gsed:run.
        assert 'ggrep:run not supported' in old['PKG_FAIL_REASON'], old
        subprocess.run([args.patch, '-s', '-p1', '-d', str(tree), '-i', str(repair)], check=True)
        new = query(args, recipe)
    assert not new['PKG_FAIL_REASON'].strip(), new['PKG_FAIL_REASON']
    tools = new['USE_TOOLS'].split()
    assert 'ggrep:run' not in tools and 'gsed:run' not in tools, tools
    # bash:run keeps its own shared rule; only the named tools change.
    assert 'bash:run' in tools, tools
    line = 'x=`echo "$1" | sed -r "s/a/b/" | grep -q c`\n'
    out = subprocess.run('sed ' + new['SUBST_SED.gsed'], shell=True, input=line,
                         check=True, capture_output=True, text=True).stdout
    assert out == 'x=`echo "$1" | /usr/bin/sed -r "s/a/b/" | /usr/bin/grep -q c`\n', out
    print('PASS: xdg-utils scripts run NetBSD 11 base grep and sed.')


if __name__ == '__main__':
    main()
