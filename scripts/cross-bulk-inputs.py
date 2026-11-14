#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Print the build-input digest of one evaluated pkgsrc package.

cross-bulk records this digest in a work directory after a successful build
there, and compares it when only the package revision (nbN) changes. Equal
digests mean that the recipe inputs that the compiled objects came from are
unchanged, so the build repackages the existing objects with the new package
metadata instead of compiling them again.

The digest covers, after the selected pkgsrc root is replaced by a fixed
token:

* the content of every makefile that the parse read (recipe, shared recipe
  fragments, buildlink3.mk files of dependencies, pkgsrc infrastructure and
  MAKECONF), every regular file in the recipe directory, the distinfo file
  and every file under PATCHDIR, FILESDIR and LOCALPATCHES;
* the evaluated values of the variables that the caller selects (options,
  configure, compiler and source variables), as bmake printed them.

Only the logical lines that assign PKGREVISION, and integer assignments of
variables that serve solely as its value (PKGREVISION= ${MESA_PORT_REVISION}),
are left out. Any other change, including a comment, a conditional around
the revision or an evaluated value that embeds the revision, gives another
digest, so the package is compiled again. A recipe that names PKGREVISION,
PKGVERSION or PKGNAME anywhere else binds the full PKGNAME into the digest.
Files under the work directory (pkgsrc's generated makevars) are skipped.

Usage: cross-bulk-inputs.py --pkgsrc DIR --wrkdir DIR --names 'NAME ...'
The values follow on standard input, one line per name, in the same order.
The names must include .CURDIR, .MAKE.MAKEFILES and PKGNAME. Any error
prints nothing and exits 1; the caller then keeps the conservative path.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

SCHEMA = 'cross-bulk-inputs-v1'
TOKEN = '@PKGSRCDIR@'
TREES = ('PATCHDIR', 'FILESDIR')
ASSIGN = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_.+-]*)\s*([?:!+]?=)(.*)$')
REFERENCE = re.compile(r'\$[{(]([A-Za-z_][A-Za-z0-9_.]*)[:})]')
SENSITIVE = re.compile(r'\$[{(](?:PKGREVISION|PKGVERSION|PKGNAME)[:})]')
INTEGER = re.compile(r'^\s*[0-9]+\s*(?:#.*)?$')
MAKEFILE_NAME = re.compile(r'^(?:Makefile.*|.*\.mk)$')


class InputError(ValueError):
    """The inputs cannot be identified reliably."""


def logical_lines(text):
    """Split text into logical make lines; keep the raw text of each."""
    lines, buf = [], []
    for raw in text.split('\n'):
        buf.append(raw)
        if raw.endswith('\\'):
            continue
        lines.append('\n'.join(buf))
        buf = []
    if buf:
        lines.append('\n'.join(buf))
    return lines


def joined(line):
    return ' '.join(part[:-1] if part.endswith('\\') else part for part in line.split('\n'))


def revision_variables(texts):
    """Names whose assignments only feed PKGREVISION in the parsed makefiles."""
    names = {'PKGREVISION'}
    assignments = {}
    references = {}
    for text in texts.values():
        for line in logical_lines(text):
            flat = joined(line)
            match = ASSIGN.match(flat)
            if match and not flat.lstrip().startswith('#'):
                name, value = match.group(1), match.group(3).split('#', 1)[0]
                assignments.setdefault(name, []).append(value)
                for ref in REFERENCE.findall(value):
                    references.setdefault(ref, []).append(name)
            else:
                for ref in REFERENCE.findall(flat.split('#', 1)[0]):
                    references.setdefault(ref, []).append(None)
    changed = True
    while changed:
        changed = False
        for name in list(names):
            for value in assignments.get(name, ()):
                for ref in REFERENCE.findall(value):
                    if ref in names:
                        continue
                    values = assignments.get(ref, [])
                    users = references.get(ref, [])
                    # Strip a helper only when every assignment is a plain
                    # integer and every use is a revision assignment.
                    if (values and all(INTEGER.match(v) for v in values) and
                            all(user in names or user == name for user in users)):
                        names.add(ref)
                        changed = True
    return names


def normalized(text, names):
    kept = []
    for line in logical_lines(text):
        flat = joined(line)
        match = ASSIGN.match(flat)
        if match and match.group(1) in names and not flat.lstrip().startswith('#'):
            continue
        kept.append(line)
    return '\n'.join(kept)


def inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def digest_inputs(pkgsrc, wrkdir, values):
    for required in ('.CURDIR', '.MAKE.MAKEFILES', 'PKGNAME'):
        if required not in values:
            raise InputError('missing variable ' + required)
    pkgsrc = Path(pkgsrc).resolve(strict=True)
    work = Path(wrkdir).resolve() if wrkdir else None
    curdir = Path(values['.CURDIR']).resolve(strict=True)
    if not inside(curdir, pkgsrc):
        raise InputError('recipe outside the selected pkgsrc root')
    files = {}
    makefiles = set()

    def add(path, makefile=False):
        path = Path(path)
        if not path.is_absolute():
            path = curdir / path
        if path.is_symlink() and path.is_dir():
            raise InputError('directory symlink in package inputs')
        resolved = path.resolve()
        if work is not None and inside(resolved, work):
            return
        if not resolved.is_file():
            files.setdefault(str(path), None)
            return
        files[str(resolved)] = resolved
        if makefile:
            makefiles.add(str(resolved))

    makefile_list = values['.MAKE.MAKEFILES'].split()
    if not makefile_list:
        raise InputError('bmake did not report loaded makefiles')
    for value in makefile_list:
        add(value, makefile=True)
    for path in sorted(curdir.iterdir()):
        if path.is_file():
            add(path, makefile=bool(MAKEFILE_NAME.match(path.name)))
    if values.get('DISTINFO_FILE'):
        add(values['DISTINFO_FILE'])
    trees = [values.get(name, '') for name in TREES]
    local = values.get('LOCALPATCHES', '')
    if local and values.get('PKGPATH'):
        trees.append(str(Path(local) / values['PKGPATH']))
    for value in trees:
        if not value:
            continue
        tree = Path(value) if Path(value).is_absolute() else curdir / value
        if tree.is_dir():
            for path in sorted(tree.rglob('*')):
                if path.is_symlink() and path.is_dir():
                    raise InputError('directory symlink in package inputs')
                if path.is_file():
                    add(path)
    texts = {}
    for name in sorted(makefiles):
        texts[name] = Path(name).read_bytes().decode('utf-8', 'surrogateescape')
    names = revision_variables(texts)
    sensitive = False
    records = []
    for name in sorted(files):
        path = files[name]
        key = name
        resolved = Path(name)
        if inside(resolved, pkgsrc):
            key = 'pkgsrc/' + resolved.relative_to(pkgsrc).as_posix()
        if path is None:
            records.append([key, 'missing'])
            continue
        if name in texts:
            text = normalized(texts[name], names)
            # Infrastructure names PKGNAME for packaging; a recipe or
            # configuration that names it may compile the revision in.
            # Comments count too: an escaped \# is not a comment.
            if not key.startswith('pkgsrc/mk/'):
                sensitive = sensitive or bool(SENSITIVE.search(text))
            data = text.encode('utf-8', 'surrogateescape')
        else:
            data = path.read_bytes()
        if not inside(resolved, pkgsrc):
            key = 'external:' + hashlib.sha256(name.encode()).hexdigest()[:16]
        records.append([key, hashlib.sha256(data).hexdigest()])
    root = str(pkgsrc)
    variables = {}
    for name, value in values.items():
        if name in ('.MAKE.MAKEFILES', 'PKGNAME'):
            continue
        variables[name] = value.replace(root, TOKEN)
    document = {'schema': SCHEMA, 'files': records, 'variables': variables,
                'revision_variables': sorted(names)}
    if sensitive:
        document['package'] = values['PKGNAME']
    data = json.dumps(document, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(data).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('--pkgsrc', required=True)
    parser.add_argument('--wrkdir', default='')
    parser.add_argument('--names', required=True)
    args = parser.parse_args(argv)
    names = args.names.split()
    lines = sys.stdin.read().split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    try:
        if len(names) != len(set(names)) or len(lines) != len(names):
            raise InputError('one value line per variable name is required')
        print(digest_inputs(args.pkgsrc, args.wrkdir, dict(zip(names, lines))))
    except (OSError, UnicodeError, InputError) as error:
        print('cross-bulk-inputs: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
