#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Stored per-platform Perl cross config.sh.
"""Convert a target-measured Configure config.sh to a stored template and back.

capture: replace build-specific paths with @NAME@ placeholders, drop the
build host's identity and the probe target's address, and refuse output that
still names a build-host path. fill: substitute the current build's paths.
"""
import argparse
import re
import sys
from pathlib import Path

# Build-specific inputs, in the order the recipe passes them.
NAMES = ('WRKSRC', 'WRKDIR', 'SYSROOT', 'TOOLDIR', 'TOOLBASE',
         'HOST_MINIPERL', 'HOST_GENERATE', 'CROSS_BUILD_PERL')
# Configure answers that describe the build host or the probe connection.
NEUTRAL = {
    'cf_by': 'pkgsrc', 'cf_email': 'root@localhost', 'cf_time': '',
    'perladmin': 'root@localhost', 'myhostname': 'localhost',
    'mydomain': '.localdomain', 'myuname': 'netbsd',
    'targethost': '', 'targetuser': '', 'targetdir': '', 'targetport': '',
}
# Probe runners are never used after Configure; make any use fail.
NO_TARGET = '@WRKSRC@/Cross/no-target'
RUNNERS = ('run', 'to', 'from', 'targetmkdir')
TARGET_PATHS = ('/usr/', '/lib/', '/bin/', '/etc/', '/var/', '/dev/', '/libexec/')
PLACEHOLDER = re.compile(r'@([A-Z][A-Z_]*)@')
ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)='(.*)'$")


def values(pairs):
    result = {}
    for pair in pairs:
        name, sep, value = pair.partition('=')
        if not sep or name not in NAMES or not value.startswith('/') or value == '/':
            raise SystemExit(f'invalid --set {pair!r}; use NAME=/absolute/path with NAME in {NAMES}')
        result[name] = value.rstrip('/')
    missing = set(NAMES) - set(result)
    if missing:
        raise SystemExit('missing --set for ' + ' '.join(sorted(missing)))
    return result


def capture(text, paths, identity):
    lines = []
    for number, line in enumerate(text.splitlines()):
        if number == 1:
            lines.append('# pkgsrc recipe: ' + identity)
        if line.startswith('# pkgsrc recipe: '):
            continue
        if line.startswith('# Configuration time') or line.startswith('# Target system'):
            continue
        match = ASSIGNMENT.match(line)
        if match and match.group(1) in NEUTRAL:
            line = f"{match.group(1)}='{NEUTRAL[match.group(1)]}'"
        elif match and match.group(1) in RUNNERS:
            line = f"{match.group(1)}='{NO_TARGET}'"
        elif match and re.fullmatch(r'config_arg\d+', match.group(1)) and re.match(
                r"-Dtarget(host|user|dir|port)=", match.group(2)):
            line = f"{match.group(1)}='{match.group(2).split('=')[0]}='"
        lines.append(line)
    out = '\n'.join(lines) + '\n'
    # The probe host name and private directory must not survive anywhere.
    for key in ('targethost', 'targetdir'):
        found = re.search(rf"^{key}='(.+)'$", text, re.M)
        if found:
            out = out.replace(found.group(1), '')
    out = re.sub(r"(-Dtarget(?:host|user|dir|port)=)[^\s']*", r'\1', out)
    for name in sorted(paths, key=lambda n: len(paths[n]), reverse=True):
        out = out.replace(paths[name], '@' + name + '@')
    return out


def leaks(text):
    """Absolute paths that are neither placeholders nor target paths."""
    found = set()
    for match in re.finditer(r"(?<![@\w.-])(/[A-Za-z0-9_.+-][^\s'\"]*)", text):
        path = match.group(1)
        if not path.startswith(TARGET_PATHS) and path not in ('/usr', '/lib', '/bin', '/tmp', '/afs'):
            found.add(path)
    return sorted(found)


def fill(text, paths):
    def substitute(match):
        if match.group(1) not in paths:
            raise SystemExit(f'unknown placeholder @{match.group(1)}@ in stored config.sh')
        return paths[match.group(1)]
    return PLACEHOLDER.sub(substitute, text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('capture', 'fill', 'check'))
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('--set', action='append', default=[], metavar='NAME=PATH')
    parser.add_argument('--identity', help='recipe and options recorded by capture')
    args = parser.parse_args()
    text = args.input.read_text()
    if args.mode == 'check':
        bad = leaks(text)
        for key, value in NEUTRAL.items():
            line = re.search(rf"^{key}='(.*)'$", text, re.M)
            if line and line.group(1) != value:
                bad.append(f'{key} is not neutral')
        if bad:
            raise SystemExit('stored config.sh is not normalized: ' + ', '.join(bad))
        return 0
    if args.output is None or args.output.exists():
        raise SystemExit('a new output path is required')
    paths = values(args.set)
    if args.mode == 'capture' and not args.identity:
        raise SystemExit('capture requires --identity')
    result = capture(text, paths, args.identity) if args.mode == 'capture' else fill(text, paths)
    if args.mode == 'capture' and leaks(result):
        raise SystemExit('build-host paths remain after capture: ' + ', '.join(leaks(result)))
    args.output.write_text(result)
    return 0


if __name__ == '__main__':
    sys.exit(main())
