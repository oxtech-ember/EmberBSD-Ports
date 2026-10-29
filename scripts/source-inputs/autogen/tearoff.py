# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Assemble the AutoGen libopts tearoff from a patched AutoGen source tree.

This follows autoopts/mk-tpl-config.sh (collect_src) and
pkg/libopts/mklibsrc.sh from the selected AutoGen release. Neither step runs
AutoGen or Guile: libopts.c is a generated list of includes and the tearoff
copies distributed sources, licenses and m4 files. The columns(1) layout used
for EXTRA_DIST is reproduced for the fixed options mklibsrc.sh selects.
"""
from pathlib import Path
import re

_INCLUDE = re.compile(r'^#include\s+"([^"]+)"\s*$', re.M)


def _make_list(text, name):
    """Return the words of one Automake variable with simple $(VAR) expansion."""
    values = {}
    joined = re.sub(r'\\\n', ' ', text)
    for line in joined.splitlines():
        match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line.strip())
        if match:
            values.setdefault(match.group(1), []).append(match.group(2).split())

    def expand(key, seen=()):
        if key not in values or key in seen or len(values[key]) != 1:
            raise ValueError('AutoGen autoopts/Makefile.am lacks a unique ' + key)
        words = []
        for word in values[key][0]:
            ref = re.fullmatch(r'\$\(([A-Za-z_][A-Za-z0-9_]*)\)', word)
            words.extend(expand(ref.group(1), seen + (key,)) if ref else [word])
        return words
    return expand(name)


def _version(root):
    text = (root / 'VERSION').read_text(encoding='utf-8')
    found = {}
    for key in ('AO_CURRENT', 'AO_REVISION', 'AO_AGE'):
        values = re.findall(r'^' + key + r'=([0-9]+)$', text, re.M)
        if len(values) != 1:
            raise ValueError('AutoGen VERSION lacks a unique ' + key)
        found[key] = values[0]
    return found['AO_CURRENT'], found['AO_REVISION'], found['AO_AGE']


def libopts_c(root):
    """Return collect_src output for HDRS followed by CSRC."""
    root = Path(root)
    current, revision, age = _version(root)
    makefile = (root / 'autoopts/Makefile.am').read_text(encoding='utf-8')
    files = _make_list(makefile, 'HDRS') + _make_list(makefile, 'CSRC')
    lines = ['#define  AUTOOPTS_INTERNAL 1', '#include "autoopts/project.h"', '',
             '#include "ao-strs.h"', 'static char const ao_ver_string[] =',
             '    "%s:%s:%s\\n";' % (current, revision, age)]
    lines.extend('#include "%s"' % name for name in files if name != 'project.h')
    return '\n'.join(lines) + '\n'


def columns(entries, *, width=79, indent=4, line_sep='  \\'):
    """Reproduce `columns -I<indent> --spread=1 --line-sep=<sep>` row output."""
    width -= indent + len(line_sep)
    widest = max(len(entry) + 1 for entry in entries)
    width = max(width, 16, widest)
    count = width // widest
    size = 0
    if count > 1:
        spread = width - widest
        size = spread // (count - 1)
        if size < widest:
            count = spread // widest + 1
            size = spread // (count - 1) if count > 1 else width
    if widest < size:
        size = widest
    pad = ' ' * indent
    out, row = [], []
    for index, entry in enumerate(entries):
        if index == len(entries) - 1:
            row.append(entry)
            out.append(pad + ''.join(row))
            break
        if len(row) + 1 < count:
            row.append(entry.ljust(size))
        else:
            row.append(entry + line_sep)
            out.append(pad + ''.join(row))
            row = []
    return '\n'.join(out) + '\n'


def assemble(root, destination):
    """Create the libopts-<version> tearoff directory below destination.

    Returns the created directory. File modes are fixed (0644 files, 0755
    directories) so the payload digest does not depend on the umask.
    """
    root = Path(root)
    current, revision, age = _version(root)
    tag = 'libopts-%s.%s.%s' % (current, revision, age)
    target = Path(destination) / tag
    target.mkdir(mode=0o755)
    for sub in ('compat', 'autoopts', 'm4'):
        (target / sub).mkdir(mode=0o755)
    written = {}

    def put(name, data):
        if name in written:
            if written[name] != data:
                raise ValueError('conflicting libopts tearoff member ' + name)
            return
        path = target / name
        path.write_bytes(data)
        path.chmod(0o644)
        written[name] = data

    generated = libopts_c(root).encode('utf-8')
    put('libopts.c', generated)
    names = ['gettext.h', 'parse-duration.c', 'parse-duration.h',
             'stdnoreturn.in.h', '_Noreturn.h']
    names += [m for m in _INCLUDE.findall(generated.decode('utf-8'))]
    # mklibsrc.sh copies verify.h only where a release ships it.
    optional = {'verify.h'}
    for name in names + ['intprops.h', 'verify.h']:
        if name in written:
            continue
        for candidate in (root / 'autoopts' / name, root / name):
            if candidate.is_file() and not candidate.is_symlink():
                put(name, candidate.read_bytes())
                break
        else:
            if name not in optional:
                raise ValueError('AutoGen source lacks libopts member ' + name)
    for path in sorted((root / 'pkg/libopts').glob('COPYING.*')):
        put(path.name, path.read_bytes())
    # mklibsrc.sh also names config/snippet/_Noreturn.h; releases without it
    # ship the tearoff without compat/_Noreturn.h.
    for name in ('windows-config.h', 'compat.h', 'pathfind.c', 'snprintf.c', 'strdup.c', 'strchr.c'):
        put('compat/' + name, (root / 'compat' / name).read_bytes())
    snippet = root / 'config/snippet/_Noreturn.h'
    if snippet.is_file():
        put('compat/_Noreturn.h', snippet.read_bytes())
    m4 = sorted(root.joinpath('config').glob('libopts*.m4')) + sorted(root.joinpath('config').glob('stdnoret*.m4'))
    for path in m4:
        data = path.read_bytes()
        if path.name == 'libopts.m4':
            data += (root / 'pkg/libopts/libopts-add.m4').read_bytes()
        put('m4/' + path.name, data)
    if 'm4/libopts.m4' not in written:
        raise ValueError('AutoGen source lacks config/libopts.m4')
    readme = (root / 'pkg/libopts/README').read_bytes().replace(b'${tag}', tag.encode('ascii'))
    put('README', readme)
    put('MakeDefs.inc', b'')
    stdnoreturn = [line for line in (root / 'pkg/libopts/stdnoreturn.mk').read_text(encoding='utf-8').splitlines()
                   if line and not line.startswith('#')]
    stdnoreturn = [line.replace('top_srcdir', 'srcdir', 1) for line in stdnoreturn]
    noreturn = root / 'pkg/libopts/_Noreturn'
    extra = []
    if noreturn.is_file():
        lines = noreturn.read_text(encoding='utf-8').splitlines()
        start = next((i for i, line in enumerate(lines) if line.startswith('Makefile.am:')), None)
        if start is not None:
            for line in lines[start + 1:]:
                if re.match(r'^[A-Z][a-z0-9-]*:', line):
                    break
                extra.append(line)
    members = sorted([name for name in written if name not in ('libopts.c',)] , key=lambda s: s.encode())
    head = ['## LIBOPTS Makefile', 'MAINTAINERCLEANFILES    = Makefile.in',
            'if INSTALL_LIBOPTS', 'lib_LTLIBRARIES         = libopts.la', 'else',
            'noinst_LTLIBRARIES      = libopts.la', 'endif',
            'libopts_la_SOURCES      = libopts.c',
            'libopts_la_CPPFLAGS     = -I$(srcdir)',
            'libopts_la_LDFLAGS      = -version-info  %s:%s:%s' % (current, revision, age),
            'EXTRA_DIST\t\t=', 'BUILT_SOURCES\t\t=', 'MOSTLYCLEANFILES\t=', '',
            'libopts.c:\t\t$(BUILT_SOURCES)',
            '@: do-nothing rule to avoid default SCCS get', '']
    text = '\n'.join(head) + '\n'
    text += '\n# Makefile fragment from gnulib-s stdnoreturn module:\n#\n'
    text += ''.join(line + '\n' for line in stdnoreturn + extra)
    text += '\nEXTRA_DIST += \\\n' + columns(members)
    put('Makefile.am', text.encode('utf-8'))
    return target
