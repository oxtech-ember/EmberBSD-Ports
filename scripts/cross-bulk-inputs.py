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
  configure, compiler, toolchain-context and source variables), as bmake
  printed them; PATH without directories in the work directory;
* the toolchain: for CC, CXX, CPP, FC, NATIVE_CC, LD, AS, AR, NM, RANLIB,
  OBJCOPY and STRIP, the resolved program, its SHA256 and its --version
  answer. With the cross tools context path (which names the context hash),
  a replaced or rebuilt toolchain gives another digest.

Only the bare number of a single-line assignment to PKGREVISION, or to an
integer variable that gives its value (PKGREVISION= ${MESA_PORT_REVISION}),
is replaced by a fixed token. The rest of that line stays: a comment on the
revision line or next to it, a conditional around the revision, or an
evaluated value that embeds the revision gives another digest, so the
package is compiled again. A revision assignment continued over several
lines (PKGREVISION=\ and the number on the next line) stays whole: any
change of it compiles the package again.

The revision, its helpers, PKGVERSION and PKGNAME may reach package metadata
in the recipe makefiles: dependency patterns (DEPENDS, TOOL_DEPENDS,
BUILDLINK_ABI_DEPENDS.*, ...), CONFLICTS, PKGNAME, failure reasons, conditionals that
set only those, and recipe variables that only feed them and that pkgsrc/mk
does not name (MESA_GENERATORS_VERSION). Dependency patterns are not compile
inputs here: cross-bulk compares the dependency lists of a kept work
directory separately and stops when they changed. Any other use of these
values (a build variable, a target command, another conditional, or a bare
name in SUBST_VARS) can reach the build: then the helpers stay in the digest and the full PKGNAME is bound
into it. Files under the work directory (pkgsrc's generated makevars) are
skipped. The versions of installed dependencies are not inputs.

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
import shutil
import subprocess
import sys

SCHEMA = 'cross-bulk-inputs-v1'
TOKEN = '@PKGSRCDIR@'
TREES = ('PATCHDIR', 'FILESDIR')
ASSIGN = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_.+-]*?)\s*([?:!+]?=)(.*)$')
REFERENCE = re.compile(r'\$[{(]([A-Za-z_][A-Za-z0-9_.]*)[:})]')
INTEGER = re.compile(r'^\s*[0-9]+\s*(?:#.*)?$')
MAKEFILE_NAME = re.compile(r'^(?:Makefile.*|.*\.mk)$')
# Package metadata that a revision may reach without reaching the build.
NEUTRAL = frozenset(('PKGREVISION', 'PKGNAME', 'DEPENDS', 'BUILD_DEPENDS', 'TOOL_DEPENDS',
                     'BOOTSTRAP_DEPENDS', 'TEST_DEPENDS', 'CONFLICTS', 'SUPERSEDES',
                     'PKG_FAIL_REASON', 'PKG_SKIP_REASON'))
NEUTRAL_PREFIXES = ('BUILDLINK_API_DEPENDS.', 'BUILDLINK_ABI_DEPENDS.')
# A single-line assignment of a bare number, with an optional comment.
REVISION_NUMBER = re.compile(r'^(\s*([A-Za-z_][A-Za-z0-9_.+-]*?)\s*[?:!+]?=\s*)([0-9]+)(\s*(?:#.*)?)$')
# pkgsrc substitutes the values of the variables that these lists name.
NAME_LISTS = re.compile(r'^SUBST_VARS(?:\..*)?$')
# Compiler variables whose programs identify the toolchain.
TOOL_VARIABLES = ('CC', 'CXX', 'CPP', 'FC', 'NATIVE_CC', 'LD', 'AS', 'AR', 'NM', 'RANLIB',
                  'OBJCOPY', 'STRIP')


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


def strip_comment(line):
    """The text of a logical make line before its first unescaped #."""
    out, i = [], 0
    while i < len(line):
        c = line[i]
        if c == '\\' and i + 1 < len(line):
            out.append(line[i:i + 2])
            i += 2
            continue
        if c == '#':
            break
        out.append(c)
        i += 1
    return ''.join(out)


def parsed(texts):
    """Each makefile as a list of (kind, name, text) logical lines.

    kind is 'assign' (name is the variable), 'directive' (name is the
    directive word) or 'other' (shell commands, targets, includes)."""
    result = {}
    for file, text in texts.items():
        lines = []
        for line in logical_lines(text):
            flat = strip_comment(joined(line)).strip()
            if not flat:
                continue
            if flat.startswith('.'):
                word = flat[1:].lstrip().split(None, 1)
                lines.append(('directive', word[0] if word else '', flat))
                continue
            match = ASSIGN.match(flat)
            if match and not line.startswith('\t'):
                lines.append(('assign', match.group(1), match.group(3)))
            else:
                lines.append(('other', '', flat))
        result[file] = lines
    return result


def revision_variables(lines):
    """PKGREVISION and the integer variables that give its value."""
    names = {'PKGREVISION'}
    assignments = {}
    for entries in lines.values():
        for kind, name, value in entries:
            if kind == 'assign':
                assignments.setdefault(name, []).append(value)
    changed = True
    while changed:
        changed = False
        for name in list(names):
            for value in assignments.get(name, ()):
                for ref in REFERENCE.findall(value):
                    values = assignments.get(ref, [])
                    if ref not in names and values and all(INTEGER.match(v) for v in values):
                        names.add(ref)
                        changed = True
    return names


def neutral_name(name):
    return name in NEUTRAL or name.startswith(NEUTRAL_PREFIXES)


def neutral_block(entries, index):
    """Whether the conditional that starts at entries[index] only sets
    package metadata: dependency patterns, revisions or failure reasons."""
    depth = 0
    for kind, name, _ in entries[index:]:
        if kind == 'directive':
            if name.startswith('if'):
                depth += 1
            elif name == 'endif':
                depth -= 1
                if depth == 0:
                    return True
            elif name not in ('else', 'elif', 'elifdef', 'elifndef', 'elifmake', 'elifnmake'):
                return False
        elif kind == 'assign':
            if not neutral_name(name):
                return False
        else:
            return False
    return False


def revision_sensitive(lines, recipe_files, names, mk_text):
    """Whether the revision can reach the build through a recipe makefile.

    The revision, PKGVERSION, PKGNAME and the revision helpers are tainted.
    A tainted value may only reach package metadata: dependency patterns,
    PKGNAME, PKGREVISION, failure reasons, and conditionals that set only
    those. A variable that a recipe assigns from a tainted value carries the
    taint when the infrastructure (mk/) does not name it and the recipe
    makefiles use it; every other use can reach the build. A tainted name as
    a bare word in SUBST_VARS reaches the build: subst.mk substitutes the
    value of each variable that the list names."""
    taint = set(names) | {'PKGVERSION', 'PKGNAME'}
    used = set()
    for file in recipe_files:
        for kind, name, text in lines[file]:
            used.update(REFERENCE.findall(text))
    changed = True
    while changed:
        changed = False
        for file in recipe_files:
            entries = lines[file]
            for index, (kind, name, text) in enumerate(entries):
                if kind == 'assign' and NAME_LISTS.match(name) and set(text.split()) & taint:
                    # subst.mk substitutes the value of each named variable.
                    return True
                refs = set(REFERENCE.findall(text)) & taint
                if not refs:
                    continue
                if kind == 'assign':
                    if name in taint or neutral_name(name):
                        continue
                    if name in used and not re.search(r'\b' + re.escape(name) + r'\b', mk_text):
                        taint.add(name)
                        changed = True
                        continue
                    return True
                if kind == 'directive' and name.startswith(('if', 'elif')) and neutral_block(entries, index):
                    continue
                return True
    return False


def normalized(text, names):
    """The text with the bare number of each revision assignment replaced.

    Only an integer value on a single-line assignment to a name in names is
    replaced; the rest of the line, including an end-of-line comment, stays,
    so that a comment that names a rebuild reason changes the digest."""
    kept = []
    for line in logical_lines(text):
        match = REVISION_NUMBER.match(line)
        if match and match.group(2) in names and '\n' not in line:
            line = match.group(1) + '@REVISION@' + match.group(4)
        kept.append(line)
    return '\n'.join(kept)


def inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def tool_identities(values, work, root):
    """The identity of each compiler that the build uses: its resolved path,
    the SHA256 of the program and its --version answer. A rebuilt or
    replaced toolchain at the same path gives another digest."""
    directories = [entry for entry in values.get('PATH', '').split(':')
                   if entry and not (work is not None and inside(Path(entry).resolve(), work))]
    # pkgsrc puts the cross tools context, not its bin directory, in PATH.
    if values.get('EMBERBSD_CROSS_TOOLS'):
        directories.append(os.path.join(values['EMBERBSD_CROSS_TOOLS'], 'bin'))
    tools = {}
    for name in TOOL_VARIABLES:
        words = values.get(name, '').split()
        if not words:
            continue
        program = words[0]
        found = program if os.path.isabs(program) else shutil.which(program, path=os.pathsep.join(directories))
        if not found or not os.path.isfile(found):
            tools[name] = ['missing', program]
            continue
        real = os.path.realpath(found)
        digest = hashlib.sha256()
        with open(real, 'rb') as stream:
            for block in iter(lambda: stream.read(1 << 20), b''):
                digest.update(block)
        try:
            answer = subprocess.run([found, '--version'], stdin=subprocess.DEVNULL, capture_output=True,
                                    timeout=60).stdout.decode('utf-8', 'replace')
        except (OSError, subprocess.SubprocessError):
            answer = ''
        tools[name] = [real.replace(root, TOKEN), digest.hexdigest(), answer.replace(root, TOKEN)]
    return tools


def digest_inputs(pkgsrc, wrkdir, values):
    for required in ('.CURDIR', '.MAKE.MAKEFILES', 'PKGNAME'):
        if required not in values:
            raise InputError('missing variable ' + required)
    given = os.path.abspath(pkgsrc)
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

    def key_of(name):
        resolved = Path(name)
        if inside(resolved, pkgsrc):
            return 'pkgsrc/' + resolved.relative_to(pkgsrc).as_posix()
        return 'external:' + hashlib.sha256(name.encode()).hexdigest()[:16]

    lines = parsed(texts)
    names = revision_variables(lines)
    infrastructure = [name for name in texts if key_of(name).startswith('pkgsrc/mk/')]
    mk_text = '\n'.join(texts[name] for name in infrastructure)
    recipe_files = [name for name in texts if name not in infrastructure]
    sensitive = revision_sensitive(lines, recipe_files, names, mk_text)
    # When the revision reaches the build, the helpers stay in the text and
    # the package name is part of the digest.
    stripped = names if not sensitive else {'PKGREVISION'}
    records = []
    for name in sorted(files):
        path = files[name]
        key = key_of(name)
        if path is None:
            records.append([key, 'missing'])
            continue
        if name in texts:
            data = normalized(texts[name], stripped).encode('utf-8', 'surrogateescape')
        else:
            data = path.read_bytes()
        records.append([key, hashlib.sha256(data).hexdigest()])
    root = str(pkgsrc)
    variables = {}
    for name, value in values.items():
        if name in ('.MAKE.MAKEFILES', 'PKGNAME'):
            continue
        if name == 'PATH':
            value = ':'.join(entry for entry in value.split(':')
                             if not (work is not None and entry and inside(Path(entry).resolve(), work)))
        # The given root may name the resolved one through a symbolic link
        # (/var and /private/var on macOS).
        variables[name] = value.replace(root, TOKEN).replace(given, TOKEN)
    document = {'schema': SCHEMA, 'files': records, 'variables': variables,
                'revision_variables': sorted(stripped),
                'tools': tool_identities(values, work, root)}
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
