#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that commits do not silently drop entries from pkgsrc/export.conf.

A commit may remove an export.conf entry only together with its source: the
file the entry names is deleted, or the same entry is written again (moved)
in that commit. An entry that disappears while its source stays in the tree
is a truncation, such as a staging tool that lost the lines after the place
where it inserted new ones. Every commit in BASE..HEAD is checked on its own,
so each commit stays exportable and bisectable.
"""
import argparse
import re
import subprocess
import sys

sys.dont_write_bytecode = True
CONF = 'pkgsrc/export.conf'


def git(root, *args):
    return subprocess.run(('git', '-C', root) + args, check=True, capture_output=True,
                          text=True).stdout


def entries(root, rev):
    try:
        text = git(root, 'show', '%s:%s' % (rev, CONF))
    except subprocess.CalledProcessError:
        return []
    result = []
    for raw in text.split('\n'):
        fields = re.split(r'\t+', raw.strip('\t'))
        if fields[0] and not fields[0].startswith('#') and len(fields) > 1:
            result.append(tuple(fields))
    return result


def exists(root, rev, path):
    return subprocess.run(('git', '-C', root, 'cat-file', '-e', '%s:%s' % (rev, path)),
                          capture_output=True).returncode == 0


def check_commit(root, rev, errors):
    parents = git(root, 'rev-list', '--parents', '-n', '1', rev).split()[1:]
    if len(parents) != 1:
        return
    before, after = entries(root, parents[0]), entries(root, rev)
    kept = set(after)
    lost = [e for e in before if e not in kept and exists(root, rev, e[1])]
    for entry in lost:
        errors.append('%s drops "%s" from %s, but %s is still in the tree'
                      % (rev[:12], ' '.join(entry), CONF, entry[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', default='.', help='Ports checkout (default: .)')
    parser.add_argument('base', help='check the commits after this one, e.g. origin/main')
    parser.add_argument('head', nargs='?', default='HEAD')
    args = parser.parse_args()
    revs = git(args.root, 'rev-list', '--reverse', '%s..%s' % (args.base, args.head),
               '--', CONF).split()
    errors = []
    for rev in revs:
        check_commit(args.root, rev, errors)
    for error in errors:
        print('FAIL: ' + error)
    if errors:
        print('FAIL: %d export.conf entries dropped in %s..%s' % (len(errors), args.base, args.head))
        return 1
    print('PASS: %d commits keep every export.conf entry (%s..%s)' % (len(revs), args.base, args.head))
    return 0


if __name__ == '__main__':
    sys.exit(main())
