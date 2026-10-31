#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted dependency revision check.
"""Check dependency patterns against conditional package revisions.

Some Ports packages set PKGREVISION only for the NetBSD cross build or only
for the native host build. A dependency pattern that names such a package
with an nb revision must be satisfiable by the revision of the same build:

* an exact pattern (NAME-VERSION) on such a package is an error, because
  any later revision bump leaves it behind, and the pkgsrc depends step then
  rebuilds the provider in place inside the consumer's build;
* NAME>=VERSIONnbN (or >) needs a revision of at least N in each build the
  pattern applies to: cross for a pattern inside a cross-only block, native
  for one inside a native-only block or in TOOL_DEPENDS, both otherwise.
  A build for which the provider sets PKG_FAIL_REASON is not compared.

The check is static. It reads the Makefiles and .mk files of the tree,
follows the provider's own includes of other Makefiles in the tree, and
evaluates the defined(VAR) conditions that a wrapper package such as
textproc/icu-devel sets before it includes the shared Makefile. The
revision is compared when the pattern names the version that the static
PKGNAME or DISTNAME of the provider gives; any other pattern is left to
scripts/check-export-depends.py, which evaluates the real PKGNAME.
"""
import argparse
import functools
import os
from pathlib import Path
import re
import sys

DEP_RE = re.compile(r'^(BUILDLINK_(?:API|ABI)_DEPENDS\.[\w.+-]+?|DEPENDS|BUILD_DEPENDS|'
                    r'TOOL_DEPENDS|TEST_DEPENDS)\s*[+?:!]?=\s*(.*)$')
FAIL_RE = re.compile(r'^PKG_FAIL_REASON\s*\+=')
REV_RE = re.compile(r'^PKGREVISION\s*[?:!]?=\s*([^#]*?)\s*(?:#.*)?$')
SET_RE = re.compile(r'^([A-Za-z_][\w.]*)\s*[?:!]?=\s*(\S.*)?$')
INC_RE = re.compile(r'^\.\s*include\s+"([^"$]+)"')
COND_RE = re.compile(r'^\.\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)$')
PATTERN_RE = re.compile(r'^([A-Za-z0-9_.+-]+?)(>=|>|-)([0-9][^:{}<>\[\]*?]*?)(?:nb(\d+))?$')
CROSS = 'USE_CROSS_COMPILE'


@functools.lru_cache(maxsize=None)
def logical_lines(path):
    """Return (line number, text) pairs with backslash continuations joined."""
    try:
        raw = path.read_text(encoding='utf-8', errors='replace').split('\n')
    except OSError:
        return ()
    lines, buf, start = [], '', 0
    for number, line in enumerate(raw, 1):
        if not buf:
            start = number
        if line.endswith('\\'):
            buf += line[:-1] + ' '
            continue
        lines.append((start, (buf + line).strip()))
        buf = ''
    return tuple(lines)


def context(stack):
    """Return cross, native or any for a stack of (condition, negated)."""
    for cond, negated in stack:
        if CROSS not in cond:
            continue
        positive = re.search(CROSS + r'[^}]*}\s*==\s*"yes"', cond) is not None
        negative = re.search(CROSS + r'[^}]*}\s*!=\s*"yes"', cond) is not None
        if positive and not negative:
            return 'native' if negated else 'cross'
        if negative and not positive and not negated:
            return 'native'
    return 'any'


DEFINED_RE = re.compile(r'\s*!?\s*defined\(([\w.]+)\)\s*')
EXPR_RE = re.compile(r'\$\{([\w.]+)((?::[^:}]*)*)\}')


def expand(text, values, depth=0):
    """Expand ${VAR} and ${VAR:S/old/new/} from static values, or None."""
    if text is None or depth > 8:
        return None
    def one(m):
        value = expand(values.get(m.group(1)), values, depth + 1)
        if value is None:
            raise KeyError(m.group(1))
        for mod in filter(None, m.group(2).split(':')):
            if len(mod) < 4 or mod[0] != 'S':
                raise KeyError(mod)
            delim = mod[1]
            parts = mod[2:].split(delim)
            if len(parts) < 2:
                raise KeyError(mod)
            old, new = parts[0], parts[1]
            anchor_start, anchor_end = old.startswith('^'), old.endswith('$')
            old = old.strip('^$')
            if anchor_start and value.startswith(old):
                value = new + value[len(old):]
            elif anchor_end and value.endswith(old):
                value = value[:len(value) - len(old)] + new
            elif not anchor_start and not anchor_end:
                value = value.replace(old, new, 1)
        return value
    try:
        result = EXPR_RE.sub(one, text)
    except KeyError:
        return None
    return None if '$' in result else result


def version_of(values):
    name = expand(values.get('PKGNAME') or values.get('DISTNAME'), values)
    if not name:
        return None
    m = re.match(r'^.+?-([0-9][^-]*)$', name)
    return m.group(1) if m else None


def defined_state(stack, defines):
    """False when a defined(VAR) condition of the stack is known false."""
    for cond, negated in stack:
        m = re.fullmatch(r'\s*!?\s*defined\(([\w.]+)\)\s*', cond)
        if not m:
            continue
        value = m.group(1) in defines
        if cond.strip().startswith('!'):
            value = not value
        if negated:
            value = not value
        if not value:
            return False
    return True


class Tree:
    def __init__(self, roots):
        self.roots = [Path(r) for r in roots]
        self.dirs = {}
        for root in self.roots:
            for category in sorted(root.iterdir()) if root.is_dir() else ():
                if not category.is_dir() or category.name.startswith('.'):
                    continue
                for package in sorted(category.iterdir()):
                    if (package / 'Makefile').is_file():
                        rel = package.relative_to(root).as_posix()
                        self.dirs.setdefault(rel, package)

    def resolve(self, rel):
        for root in self.roots:
            path = root / rel
            if path.is_file():
                return path
        return None

    def revisions(self, rel):
        """Return the PKGREVISION of the cross and of the native build.

        The 'version' key has the package version when the static values of
        PKGNAME or DISTNAME give it, and 'fails' the builds that set
        PKG_FAIL_REASON for the whole package.
        """
        found = []
        defines = set()
        values = {}
        seen = set()

        def walk(path, stack):
            if path in seen:
                return
            seen.add(path)
            for _, line in logical_lines(path):
                m = COND_RE.match(line)
                if m:
                    word, rest = m.group(1), m.group(2).strip()
                    if word in ('if', 'ifdef', 'ifndef'):
                        if word == 'ifdef':
                            rest = 'defined(%s)' % rest
                        elif word == 'ifndef':
                            rest = '!defined(%s)' % rest
                        stack.append((rest, False))
                    elif word == 'elif' and stack:
                        stack[-1] = ('', False)
                    elif word == 'else' and stack:
                        stack[-1] = (stack[-1][0], True)
                    elif word == 'endif' and stack:
                        stack.pop()
                    continue
                if not defined_state(stack, defines):
                    continue
                m = REV_RE.match(line)
                if m:
                    found.append((context(stack), m.group(1)))
                    continue
                if (FAIL_RE.match(line) and context(stack) != 'any' and
                        sum(1 for c, _ in stack if not DEFINED_RE.fullmatch(c)) == 1):
                    found.append((context(stack), None))
                    continue
                m = INC_RE.match(line)
                if m:
                    name = m.group(1)
                    if name.startswith('../../'):
                        target = None if name.startswith('../../mk/') else \
                            self.resolve(name[len('../../'):])
                    else:
                        target = path.parent / name
                    if target is not None and target.is_file() and not \
                            target.name.endswith(('buildlink3.mk', 'builtin.mk', 'options.mk')):
                        walk(target, list(stack))
                    continue
                m = SET_RE.match(line)
                if m and not stack:
                    defines.add(m.group(1))
                    if m.group(1) in ('DISTNAME', 'PKGNAME', 'PKGNAME_BASE') or \
                            m.group(1) not in values:
                        values[m.group(1)] = (m.group(2) or '').split('#')[0].strip()

        walk(self.dirs[rel] / 'Makefile', [])
        # A later assignment overrides an earlier one in the same build.
        result = {'version': version_of(values), 'fails': set(), 'conditional': False}
        if any(r is not None and not (expand(r, values) or '').isdigit() for _, r in found):
            # A computed revision is left to scripts/check-export-depends.py.
            result['version'] = None
        for build in ('cross', 'native'):
            result[build] = 0
        for ctx, revision in found:
            if revision is None:
                result['fails'].add(ctx)
                continue
            if ctx != 'any':
                result['conditional'] = True
            for build in (('cross', 'native') if ctx == 'any' else (ctx,)):
                result[build] = int(expand(revision, values) or 0)
        return result


def patterns(tree):
    """Yield (file, line, context, pattern, pkgpath hint) of every pattern."""
    for root in tree.roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if not d.startswith('.') and d not in ('work', 'CVS')]
            for name in sorted(filenames):
                if not (name == 'Makefile' or name.endswith('.mk') or
                        name.startswith('Makefile.')):
                    continue
                path = Path(dirpath) / name
                stack = []
                for number, line in logical_lines(path):
                    m = COND_RE.match(line)
                    if m:
                        word, rest = m.group(1), m.group(2).strip()
                        if word in ('if', 'ifdef', 'ifndef'):
                            stack.append((rest, False))
                        elif word == 'elif' and stack:
                            stack[-1] = (rest, False)
                        elif word == 'else' and stack:
                            stack[-1] = (stack[-1][0], True)
                        elif word == 'endif' and stack:
                            stack.pop()
                        continue
                    m = DEP_RE.match(line)
                    if not m:
                        continue
                    # pkgsrc builds a TOOL_DEPENDS provider for the build host.
                    kind = 'native' if m.group(1) == 'TOOL_DEPENDS' else context(stack)
                    for word in m.group(2).split('#')[0].split():
                        pattern, _, where = word.partition(':')
                        hint = where[len('../../'):] if where.startswith('../../') else None
                        yield path, number, kind, pattern, hint


def check(tree):
    by_name = {}
    for rel in tree.dirs:
        by_name.setdefault(rel.rsplit('/', 1)[1], []).append(rel)
    cache = {}
    findings = []
    for path, number, ctx, pattern, hint in patterns(tree):
        m = PATTERN_RE.match(pattern)
        if not m:
            continue
        name, op, version, nb = m.groups()
        rel = hint if hint in tree.dirs else None
        if rel is None:
            candidates = by_name.get(name, [])
            if len(candidates) != 1:
                continue
            rel = candidates[0]
        if rel not in cache:
            cache[rel] = tree.revisions(rel)
        revisions = cache[rel]
        fails = revisions['fails']
        conditional = revisions['conditional'] or bool(fails)
        where = '%s:%d' % (path, number)
        if op == '-' and conditional:
            findings.append('%s: exact pattern %s on %s, which sets a '
                            'conditional PKGREVISION; use >=' % (where, pattern, rel))
            continue
        if nb is None or revisions.get('version') != version:
            continue
        for build in (('cross', 'native') if ctx == 'any' else (ctx,)):
            if build in fails:
                continue
            have = revisions[build]
            if int(nb) > have:
                findings.append('%s: %s needs nb%s but the %s build of %s has '
                                'PKGREVISION %s' % (where, pattern, nb, build, rel, have))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('tree', nargs='+', type=Path,
                        help='pkgsrc trees, the first one overriding the next')
    args = parser.parse_args(argv)
    findings = check(Tree(args.tree))
    for finding in findings:
        print(finding)
    if findings:
        print('FAIL: %d dependency revision findings' % len(findings), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
