# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Stored GI introspection dumps: replay without a target, capture from one.

g-ir-scanner runs GI_CROSS_LAUNCHER PROGRAM --introspect-dump=TYPES,OUT. The
dump depends on the target, the recipe, the package release and the type list
that the scanner wrote to TYPES. A stored dump records these in an identity
header and replay refuses any difference. Capture runs the live target query
and stores the normalized dump; it never names the target host.

Environment (set by devel/gobject-introspection/cross.mk):
  EMBERBSD_GI_DUMP_MODE      live (default here), replay or capture
  EMBERBSD_GI_DUMP_PLATFORM  e.g. NetBSD-11.0-aarch64
  EMBERBSD_GI_DUMP_RECIPE    PKGPATH, e.g. x11/gtk3
  EMBERBSD_GI_DUMP_PACKAGE   PKGNAME without PKGREVISION
  EMBERBSD_GI_DUMP_DIR       replay: the recipe's files/gi-dump/PLATFORM
  EMBERBSD_GI_DUMP_CAPTURE_DIR  capture: an existing absolute directory
"""
import hashlib
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ElementTree

FORMAT = 'EmberBSD GI dump 1'
FIELDS = ('platform', 'recipe', 'package', 'program', 'types-sha256', 'dump-sha256')
MODES = ('live', 'replay', 'capture')
LIMIT = 16 * 1024 * 1024
PATTERNS = {
    'platform': r'[A-Za-z0-9]+-[0-9][0-9A-Za-z._]*-[a-z0-9_]+',
    'recipe': r'[a-z0-9][a-z0-9_-]*/[A-Za-z0-9][A-Za-z0-9_.+-]*',
    'package': r'[A-Za-z0-9][A-Za-z0-9_.+-]*-[0-9][A-Za-z0-9_.+]*',
    'program': r'[A-Za-z0-9][A-Za-z0-9_.+-]{0,127}',
    'types-sha256': r'[0-9a-f]{64}',
    'dump-sha256': r'[0-9a-f]{64}',
}


class DumpError(Exception):
    """A stored dump is missing, malformed or belongs to other inputs."""


def require(condition, message):
    if not condition:
        raise DumpError(message)


def mode():
    selected = os.environ.get('EMBERBSD_GI_DUMP_MODE', 'live')
    require(selected in MODES, 'EMBERBSD_GI_DUMP_MODE must be live, replay or capture')
    return selected


def dump_arguments(arguments):
    """Return (program, types, output) for a dump query, or None."""
    if len(arguments) != 2 or not arguments[1].startswith('--introspect-dump='):
        return None
    paths = arguments[1].removeprefix('--introspect-dump=').split(',', 1)
    require(len(paths) == 2 and all(os.path.isabs(path) for path in paths), 'invalid dump paths')
    return arguments[0], paths[0], paths[1]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_limited(path):
    with open(path, 'rb') as stream:
        data = stream.read(LIMIT + 1)
    require(len(data) <= LIMIT, f'{path} exceeds 16 MiB')
    return data


def normalize(data):
    """UTF-8, LF line ends, no trailing blanks, one final newline, valid <dump>."""
    try:
        text = data.decode('utf-8', 'strict')
    except UnicodeDecodeError as error:
        raise DumpError('dump is not UTF-8') from error
    lines = [line.rstrip() for line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    while lines and not lines[-1]:
        lines.pop()
    body = ('\n'.join(lines) + '\n').encode('utf-8')
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as error:
        raise DumpError('dump is not well-formed XML') from error
    require(root.tag == 'dump', 'dump root element is not <dump>')
    return body


def identity(program, types):
    values = {
        'platform': os.environ.get('EMBERBSD_GI_DUMP_PLATFORM', ''),
        'recipe': os.environ.get('EMBERBSD_GI_DUMP_RECIPE', ''),
        'package': os.environ.get('EMBERBSD_GI_DUMP_PACKAGE', ''),
        'program': os.path.basename(program),
        'types-sha256': sha256(read_limited(types)),
    }
    for name, value in values.items():
        require(re.fullmatch(PATTERNS[name], value), f'invalid GI dump {name}: {value!r}')
    return values


def render(values, body):
    header = ['<!-- ' + FORMAT] + [f'{name}: {values[name]}' for name in FIELDS] + ['-->']
    return ('\n'.join(header) + '\n').encode('ascii') + body


def parse(data):
    """Split a stored dump into its header fields and body."""
    lines = data.split(b'\n')
    count = len(FIELDS) + 2
    require(len(lines) > count and lines[0] == ('<!-- ' + FORMAT).encode('ascii')
            and lines[count - 1] == b'-->', 'stored dump has no EmberBSD GI dump 1 header')
    values = {}
    for name, line in zip(FIELDS, lines[1:count - 1]):
        prefix = (name + ': ').encode('ascii')
        require(line.startswith(prefix), f'stored dump header lacks {name}')
        value = line[len(prefix):].decode('ascii', 'strict')
        require(re.fullmatch(PATTERNS[name], value), f'stored dump has an invalid {name}')
        values[name] = value
    body = b'\n'.join(lines[count:])
    require(sha256(body) == values['dump-sha256'], 'stored dump body differs from its dump-sha256')
    require(normalize(body) == body, 'stored dump body is not normalized')
    return values, body


def write_new(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)


def stored_path(directory, program):
    require(os.path.isabs(directory), 'GI dump directory must be absolute')
    return Path(directory) / (os.path.basename(program) + '.xml')


def replay(arguments):
    """Write the stored dump for this query, refusing any identity difference."""
    parsed = dump_arguments(arguments)
    require(parsed is not None, 'replay supports only PROGRAM --introspect-dump=TYPES,OUTPUT')
    program, types, output = parsed
    expected = identity(program, types)
    path = stored_path(os.environ.get('EMBERBSD_GI_DUMP_DIR', ''), program)
    require(path.is_file(), f'no stored GI dump {path}; capture it from an EmberBSD target '
            '(profiles/common-graphics/cross/gi-dumps.md)')
    values, body = parse(read_limited(path))
    for name in FIELDS[:-1]:
        require(values[name] == expected[name],
                f'stored GI dump {path.name} {name} is {values[name]}, this build needs {expected[name]}; '
                'capture it again')
    require(not os.path.lexists(output), 'dump output already exists')
    write_new(output, body)
    return 0


def capture(arguments):
    """Store the dump that the live query just wrote, with its identity."""
    program, types, output = dump_arguments(arguments)
    values = identity(program, types)
    body = normalize(read_limited(output))
    values['dump-sha256'] = sha256(body)
    directory = os.environ.get('EMBERBSD_GI_DUMP_CAPTURE_DIR', '')
    require(os.path.isabs(directory) and os.path.isdir(directory),
            'EMBERBSD_GI_DUMP_CAPTURE_DIR must name an existing absolute directory')
    target = Path(directory) / values['platform'] / values['recipe'].replace('/', '_')
    target.mkdir(parents=True, exist_ok=True)
    path = stored_path(str(target), program)
    require(not os.path.lexists(path), f'captured dump already exists: {path}')
    write_new(path, render(values, body))
    return 0
