#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), ncurses case-only terminfo alias check.
"""Check the case-only terminfo aliases of the exported ncurses recipe.

The first check reads terminfo.src from the pinned distfile and computes the
aliases that differ from another name of the same entry only in letter case.
The result must equal TERMINFO_CASE_ALIASES.

The second check runs the normal post-install target on private copies of a
small stage. The copies show the result of tic on a case-sensitive and on a
case-insensitive file system. Both copies must give the same tree.
"""
import os
import subprocess
import sys
import tarfile
import tempfile

TERMINFO = 'usr/pkg/share/terminfo'


def fail(message):
    sys.exit('FAIL: ' + message)


def source_aliases(distfile):
    with tarfile.open(distfile) as archive:
        member = next((m for m in archive.getmembers()
                       if m.name.endswith('/misc/terminfo.src')), None)
        if member is None:
            fail('terminfo.src is not in the distfile.')
        text = archive.extractfile(member).read().decode('latin-1')
    found = set()
    for line in text.splitlines():
        if not line or line[0] in '#\t ' or '|' not in line and ',' not in line:
            continue
        names = line.split(',', 1)[0].split('|')
        if len(names) > 1:
            names = names[:-1]
        entry = names[0]
        for name in names:
            for other in names:
                # Hexadecimal leaf directories keep the first character, so
                # only names with the same first character can collide.
                if (name != other and name.lower() == other.lower()
                        and name < other and name[0] == other[0]):
                    leaf = '%02x' % ord(name[0])
                    found.add('%s/%s:%s/%s:%02x/%s' % (
                        leaf, name, leaf, other, ord(entry[0]), entry))
    return found


def run(argv, log):
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=dict(os.environ, LC_ALL='C'), text=True)
    log.write('$ %s\n%s' % (' '.join(argv), result.stdout))
    return result


def tree(root):
    out = {}
    for base, dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(base, name)
            stat = os.lstat(path)
            out[os.path.relpath(path, root)] = (stat.st_ino, open(path, 'rb').read())
    inodes = {}
    for rel, (ino, _) in sorted(out.items()):
        inodes.setdefault(ino, rel)
    return {rel: (inodes[ino], data) for rel, (ino, data) in out.items()}


def main():
    if len(sys.argv) != 5:
        sys.exit('Usage: ncurses-case-aliases.py PKGSRC MAKECONF NCURSES_DISTFILE NEW_WORK')
    pkgsrc, makeconf, distfile = (os.path.realpath(p) for p in sys.argv[1:4])
    work = os.path.abspath(sys.argv[4])
    if os.path.lexists(work):
        fail('Output already exists.')
    os.mkdir(work)
    bmake = os.environ.get('BMAKE', 'bmake')
    recipe = os.path.join(pkgsrc, 'devel/ncurses')
    log = open(os.path.join(work, 'commands.log'), 'w')

    expected = source_aliases(distfile)
    if not expected:
        fail('terminfo.src has no case-only aliases; check the parser.')
    base = [bmake, '-C', recipe, 'MAKECONF=' + makeconf, '_PKGSRC_BARRIER=yes']
    result = run(base + ['-V', '${TERMINFO_CASE_ALIASES}'], log)
    listed = set(result.stdout.split())
    if result.returncode != 0 or listed != expected:
        fail('TERMINFO_CASE_ALIASES %s differ from terminfo.src %s.'
             % (sorted(listed), sorted(expected)))

    probe = os.path.join(work, 'case-probe')
    open(probe, 'w').close()
    case_sensitive = not os.path.exists(probe.upper().replace(work.upper(), work))
    os.unlink(probe)
    results = {}
    for variant, mixed in (('sensitive', False), ('insensitive', False),
                           ('character', True)):
        obj = os.path.join(work, variant)
        src = os.path.join(obj, 'src')
        os.makedirs(os.path.join(src, 'include'))
        with open(os.path.join(src, 'include/ncurses_cfg.h'), 'w') as cfg:
            cfg.write('#define MIXEDCASE_FILENAMES 1\n' if mixed else '/* hex */\n')
        stage = os.path.join(obj, '.destdir', TERMINFO)
        for item in sorted(expected):
            upper, lower, entry = item.split(':')
            for path in (upper, lower, entry):
                os.makedirs(os.path.join(stage, os.path.dirname(path)), exist_ok=True)
            entry_path = os.path.join(stage, entry)
            if not os.path.exists(entry_path):
                with open(entry_path, 'wb') as handle:
                    handle.write(entry.encode() + b'\n')
            if variant == 'insensitive':
                # tic removed the lower-case link when it linked the other.
                os.link(entry_path, os.path.join(stage, upper))
            else:
                os.link(entry_path, os.path.join(stage, lower))
                if case_sensitive:
                    os.link(entry_path, os.path.join(stage, upper))
        make = base + ['WRKDIR=' + obj, 'WRKSRC=' + src,
                       'DESTDIR=' + os.path.join(obj, '.destdir'), 'PREFIX=/usr/pkg']
        if run(make + ['post-install'], log).returncode != 0:
            fail('post-install failed for %s; see commands.log.' % variant)
        results[variant] = tree(stage)

    for item in expected:
        upper, lower, entry = item.split(':')
        for variant in ('sensitive', 'insensitive'):
            got = results[variant]
            if upper in got or lower not in got or got[lower][0] != got[entry][0]:
                fail('%s: %s must be a link to %s and %s must not exist.'
                     % (variant, lower, entry, upper))
        if case_sensitive and (upper not in results['character']
                               or lower not in results['character']):
            fail('character layout: both spellings must stay.')
    if results['sensitive'] != results['insensitive']:
        fail('The stage depends on the build file system.')
    print('PASS: %d case-only aliases match terminfo.src; the stage does not '
          'depend on the build file system (work directory: case-%s).'
          % (len(expected), 'sensitive' if case_sensitive else 'insensitive'))


if __name__ == '__main__':
    main()
