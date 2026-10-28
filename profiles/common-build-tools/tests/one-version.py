#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that a prepared pkgsrc export keeps one version of everything.

Ports patches programs onto the newest libraries and tools; it never keeps a
second version. The check fails when, in the export,

  * a package family has more than one version (lang/foo + lang/foo2),
  * a version knob (PYTHON_VERSIONS_ACCEPTED and the like) offers more than
    the kept version, or a recipe pins a version that is not exported,
  * a default selection (RUBY_VERSION_DEFAULT, NODE_VERSION_DEFAULT, the
    default JVM and the like) names a version that is removed from the
    export or is not the newest exported one,
  * a recipe refers to a package directory that is not exported,
  * a package directory is a second local copy of another one, or
  * two exported packages install the same shared library.

The only exception for versions is GCC: lang/gcc16* stays as the per-platform
override next to Clang. Names that merely end in digits but are different
programs are listed in DISTINCT with the reason.
"""
import argparse
import collections
import fnmatch
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
CHECKS = ('families', 'knobs', 'defaults', 'recipes', 'copies', 'libraries')
SKIP_TOP = {'mk', 'doc', 'bootstrap', 'licenses', 'regress', 'distfiles', 'packages', 'CVS'}

# The per-platform compiler override: GCC 16 next to Clang. Nothing else.
COMPILER_OVERRIDE = ('lang/gcc16*',)

# Heuristic family stems that are different programs, data sets or ABIs, not
# versions of one program. CAT/STEM with '#' for the digit run.
DISTINCT = {}

# Version knobs: file in the export, variable, and the kept value(s) source.
KNOBS = (
    ('lang/python/pyversion.mk', 'PYTHON_VERSIONS_ACCEPTED', 'PYTHON_VERSION_DEFAULT'),
    ('lang/lua/luaversion.mk', 'LUA_VERSIONS_ACCEPTED', 'LUA_VERSION_DEFAULT'),
    ('lang/php/phpversion.mk', 'PHP_VERSIONS_ACCEPTED', 'PHP_VERSION_DEFAULT'),
    ('mk/pgsql.buildlink3.mk', 'PGSQL_VERSIONS_ACCEPTED', 'PGSQL_VERSION_DEFAULT'),
    ('mk/mysql.buildlink3.mk', 'MYSQL_VERSIONS_ACCEPTED', 'MYSQL_VERSION_DEFAULT'),
    ('lang/ruby/rubyversion.mk', 'RUBY_VERSIONS_ACCEPTED', 'RUBY_VERSION_DEFAULT'),
    ('lang/ruby/rubyversion.mk', 'RUBY_VERSIONS_SUPPORTED', 'RUBY_VERSION_DEFAULT'),
)
# Recipe-level pins: VAR -> knob file whose kept value they must allow.
PINS = {
    'PYTHON_VERSIONS_ACCEPTED': 'PYTHON', 'PYTHON_VERSIONS_INCOMPATIBLE': 'PYTHON',
    'LUA_VERSIONS_ACCEPTED': 'LUA', 'LUA_VERSIONS_INCOMPATIBLE': 'LUA',
    'PHP_VERSIONS_ACCEPTED': 'PHP', 'PHP_VERSIONS_INCOMPATIBLE': 'PHP',
    'PGSQL_VERSIONS_ACCEPTED': 'PGSQL', 'PGSQL_VERSIONS_INCOMPATIBLE': 'PGSQL',
    'RUBY_VERSIONS_ACCEPTED': 'RUBY', 'RUBY_VERSIONS_INCOMPATIBLE': 'RUBY',
}

STEM = re.compile(r'^(.*?[A-Za-z+])(\d+)((?:[-_][A-Za-z][A-Za-z0-9_+-]*)?)$')
REF = re.compile(r'(?:\.include\s+"|:)\.\./\.\./([A-Za-z0-9_.+-]+/[A-Za-z0-9_.+-]+)')
ASSIGN = re.compile(r'^\s*([A-Z0-9_]+)\s*[?+:!]?=\s*(.*?)\s*(?:#.*)?$')
SHLIB = re.compile(r'^(?:\$\{PLIST\.[^}]*\})?lib/(lib[A-Za-z0-9_+.-]+?)\.so(?:\.\d+)*$')


def packages(export):
    found = []
    for cat in sorted(os.listdir(export)):
        path = export / cat
        if cat in SKIP_TOP or cat.startswith('.') or not path.is_dir():
            continue
        for name in sorted(os.listdir(path)):
            if (path / name / 'Makefile').is_file():
                found.append(cat + '/' + name)
    return found


def logical_lines(path):
    """Lines of a make fragment with backslash continuations joined."""
    return re.sub(r'\\\n', ' ', path.read_text(errors='replace')).splitlines()


def make_words(path, var):
    """Unconditional top-level value of VAR in a make fragment, or None."""
    value = None
    depth = 0
    for line in logical_lines(path):
        stripped = line.strip()
        if stripped.startswith('.') and re.match(r'\.\s*if', stripped):
            depth += 1
        elif stripped.startswith('.') and re.match(r'\.\s*endif', stripped):
            depth -= 1
        match = ASSIGN.match(line)
        if match and match.group(1) == var.rstrip('?') and value is None and \
                (not var.endswith('?') or re.match(r'^\s*[A-Z0-9_]+\s*\?=', line)):
            value = match.group(2).split()
    return value


def make_values(path, var, seen=()):
    """Every value assigned to VAR in a make fragment, conditional or not.

    A plain ${OTHER} word is replaced by the values of OTHER in the same file.
    """
    values = []
    for line in logical_lines(path):
        match = ASSIGN.match(line)
        if match and match.group(1) == var:
            for word in match.group(2).split():
                other = re.fullmatch(r'\$\{([A-Z0-9_]+)\}', word)
                if other and other.group(1) not in seen:
                    values.extend(make_values(path, other.group(1), seen + (var,)))
                elif not word.startswith('$'):
                    values.append(word)
    return values


# Default selections: knob file, default variable, accepted variable, and the
# PKGPATH of a value. The default must be exported, not removed by a family,
# and the newest exported accepted version.
DEFAULTS = (
    ('lang/python/pyversion.mk', 'PYTHON_VERSION_DEFAULT', 'PYTHON_VERSIONS_ACCEPTED', 'lang/python{}'),
    ('lang/lua/luaversion.mk', 'LUA_VERSION_DEFAULT', 'LUA_VERSIONS_ACCEPTED', 'lang/lua{}'),
    ('lang/php/phpversion.mk', 'PHP_VERSION_DEFAULT', 'PHP_VERSIONS_ACCEPTED', 'lang/php{}'),
    ('mk/pgsql.buildlink3.mk', 'PGSQL_VERSION_DEFAULT', 'PGSQL_VERSIONS_ACCEPTED',
     'databases/postgresql{}-client'),
    ('mk/mysql.buildlink3.mk', 'MYSQL_VERSION_DEFAULT', 'MYSQL_VERSIONS_ACCEPTED', 'databases/{}-client'),
    ('lang/ruby/rubyversion.mk', 'RUBY_VERSION_DEFAULT', 'RUBY_VERSIONS_ACCEPTED', 'lang/ruby{}'),
    ('lang/nodejs/nodeversion.mk', 'NODE_VERSION_DEFAULT', 'NODE_VERSIONS_ACCEPTED', 'lang/nodejs{}'),
    ('lang/go/version.mk', 'GO_VERSION_DEFAULT', None, 'lang/go{}'),
    ('mk/bdb.buildlink3.mk', 'BDB_DEFAULT', 'BDB_ACCEPTED', 'databases/{}'),
    ('mk/java-vm.mk', 'PKG_JVM_DEFAULT', '_PKG_JVM_DEFAULT', 'lang/{}'),
)


def version_key(value):
    return [int(n) for n in re.findall(r'\d+', value)] or [0]


def check_defaults(export, settings, families, errors):
    names = set(packages(export))

    def pkgpath(template, value):
        if template == 'databases/{}-client' and value[:1].isdigit():
            value = 'mysql' + value
        path = template.format(value)
        if path not in names and template == 'lang/nodejs{}' and value:
            # The newest Node.js is the unversioned lang/nodejs.
            versioned = [v for v in make_values(export / 'lang/nodejs/nodeversion.mk',
                                               'NODE_VERSIONS_ACCEPTED')]
            if value == max(versioned, key=version_key, default=None):
                path = 'lang/nodejs'
        return path

    for rel, var, accepted_var, template in DEFAULTS:
        path = export / rel
        if not path.is_file():
            continue
        if var in settings:
            chosen = settings[var]
        elif var == 'PKG_JVM_DEFAULT':
            # Unset here: java-vm.mk picks a JVM per platform.
            # "none" marks a platform without any JVM.
            chosen = [v for v in make_values(path, '_PKG_JVM_DEFAULT') if v.strip('"') != 'none']
        else:
            chosen = make_words(path, var + '?') or make_words(path, var) or make_values(path, var)[:1]
        accepted = make_values(path, accepted_var) if accepted_var and accepted_var != '_PKG_JVM_DEFAULT' else []
        exported = [v for v in accepted if pkgpath(template, v) in names]
        newest = max(exported, key=version_key) if exported else None
        if not chosen:
            errors.append('default %s in %s is not set' % (var, rel))
        for value in chosen:
            target = pkgpath(template, value)
            removed = [f for f, k in families
                       if fnmatch.fnmatchcase(target, f) and not fnmatch.fnmatchcase(target, k)]
            if target not in names or removed:
                errors.append('default %s=%s in %s selects %s, which the export removes'
                              % (var, value, rel, target))
            elif newest and value != newest:
                errors.append('default %s=%s in %s is not the newest exported version %s'
                              % (var, value, rel, newest))


def versions_settings():
    settings = {}
    families = []
    for line in (ROOT / 'pkgsrc/versions.mk').read_text().splitlines():
        match = ASSIGN.match(line)
        if not match:
            continue
        if match.group(1) == 'EMBERBSD_VERSION_FAMILIES':
            family, kept = match.group(2).split('=', 1)
            families.append((family, kept))
        else:
            settings[match.group(1)] = match.group(2).split()
    return settings, families


def check_families(export, pkgs, families, errors):
    names = set(pkgs)
    groups = collections.defaultdict(set)
    for pkg in pkgs:
        cat, name = pkg.split('/')
        match = STEM.match(name)
        if match:
            groups[cat + '/' + match.group(1).rstrip('-') + '#' + match.group(3)].add(name)
    for stem, members in sorted(groups.items()):
        cat, pattern = stem.split('/')
        plain = pattern.replace('#', '')
        if cat + '/' + plain in names:
            members.add(plain)
        if len(members) < 2 or stem in DISTINCT:
            continue
        if all(any(fnmatch.fnmatchcase(cat + '/' + m, o) for o in COMPILER_OVERRIDE) for m in members):
            continue
        errors.append('family %s has %d versions: %s' % (stem, len(members), ' '.join(sorted(members))))
    for family, kept in families:
        extra = [p for p in pkgs if fnmatch.fnmatchcase(p, family) and not fnmatch.fnmatchcase(p, kept)]
        if extra:
            errors.append('family %s keeps %s but exports %s' % (family, kept, ' '.join(extra)))


def check_knobs(export, settings, errors):
    kept = {}
    for rel, var, default in KNOBS:
        path = export / rel
        if not path.is_file():
            continue
        accepted = make_words(path, var) or []
        chosen = settings.get(default) or make_words(path, default) or []
        if len(accepted) != 1 or accepted != chosen:
            errors.append('knob %s in %s is "%s"; the default is "%s"; keep only the newest'
                          % (var, rel, ' '.join(accepted), ' '.join(chosen)))
        kept[var.split('_')[0]] = chosen
    text = (export / 'lang/python/pyversion.mk').read_text(errors='replace') \
        if (export / 'lang/python/pyversion.mk').is_file() else ''
    if 'PYTHON_27_ACCEPTED' in text:
        errors.append('knob PYTHON_27_ACCEPTED in lang/python/pyversion.mk still offers Python 2.7')
    return kept


def recipe_files(export, pkg):
    base = export / pkg
    for name in sorted(os.listdir(base)):
        if name == 'Makefile' or name.startswith('Makefile.') or name.endswith('.mk'):
            path = base / name
            if path.is_file():
                yield name, path


def check_recipes(export, pkgs, kept, errors):
    names = set(pkgs)
    dangling = collections.defaultdict(set)
    pinned = []
    for pkg in pkgs:
        for name, path in recipe_files(export, pkg):
            text = path.read_text(errors='replace')
            for target in REF.findall(text):
                cat = target.split('/')[0]
                if cat in SKIP_TOP or target in names or (export / target).is_file():
                    continue
                if (export / target).is_dir() and not (export / target / 'Makefile').is_file():
                    continue
                dangling[target].add(pkg)
            for line in text.splitlines():
                match = ASSIGN.match(line)
                if not match or match.group(1) not in PINS:
                    continue
                want = kept.get(PINS[match.group(1)])
                words = [w for w in match.group(2).split() if not w.startswith('$')]
                if not want or not words:
                    continue
                if match.group(1).endswith('INCOMPATIBLE'):
                    bad = want[0] in words
                else:
                    bad = want[0] not in words and line.split('=')[0].rstrip().endswith(('ACCEPTED', 'ACCEPTED?', 'ACCEPTED+'))
                if bad:
                    pinned.append('%s/%s: %s' % (pkg, name, line.strip()))
    for target, users in sorted(dangling.items()):
        errors.append('reference to unexported %s from %s' % (target, ' '.join(sorted(users))))
    for pin in pinned:
        errors.append('pin excludes the kept version: ' + pin)


def check_copies(export, pkgs, overlay, errors):
    by_name = collections.defaultdict(list)
    for pkg in pkgs:
        by_name[pkg.split('/')[1].lower()].append(pkg)
    for name, where in sorted(by_name.items()):
        if len(where) > 1 and any(p.split('/')[0] in overlay or p.split('/')[0].startswith('local-')
                                  for p in where):
            errors.append('duplicate local copy %s' % ' '.join(where))


def check_libraries(export, pkgs, overlay, errors):
    providers = collections.defaultdict(set)
    for pkg in pkgs:
        for plist in (export / pkg).glob('PLIST*'):
            for line in plist.read_text(errors='replace').splitlines():
                match = SHLIB.match(line.strip())
                if match:
                    providers[match.group(1)].add(pkg)
    for lib, where in sorted(providers.items()):
        if len(where) > 1 and any(p in overlay for p in where):
            errors.append('library %s is installed by %s' % (lib, ' '.join(sorted(where))))


def overlay_packages():
    found = set()
    base = ROOT / 'pkgsrc'
    for cat in os.listdir(base):
        if (base / cat).is_dir() and not cat.startswith('.'):
            for name in os.listdir(base / cat):
                if (base / cat / name / 'Makefile').is_file():
                    found.add(cat + '/' + name)
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('export', type=Path, help='pkgsrc tree prepared by scripts/prepare-pkgsrc.py')
    parser.add_argument('--check', action='append', choices=CHECKS,
                        help='run only this check (repeatable); default: all')
    args = parser.parse_args()
    checks = args.check or list(CHECKS)
    export = args.export.resolve()
    pkgs = packages(export)
    settings, families = versions_settings()
    overlay = overlay_packages()
    errors = []
    if 'families' in checks:
        check_families(export, pkgs, families, errors)
    knob_errors = []
    kept = check_knobs(export, settings, knob_errors)
    if 'knobs' in checks:
        errors.extend(knob_errors)
    if 'defaults' in checks:
        check_defaults(export, settings, families, errors)
    if 'recipes' in checks:
        check_recipes(export, pkgs, kept, errors)
    if 'copies' in checks:
        check_copies(export, pkgs, {p.split('/')[0] for p in overlay
                                    if p.split('/')[0].startswith('local-')}, errors)
    if 'libraries' in checks:
        check_libraries(export, pkgs, overlay, errors)
    errors = list(dict.fromkeys(errors))
    for error in errors:
        print('FAIL: ' + error)
    if errors:
        print('FAIL: %d one-version problems in %d packages (%s)'
              % (len(errors), len(pkgs), ', '.join(checks)))
        return 1
    print('PASS: %d packages, one version each (%s)' % (len(pkgs), ', '.join(checks)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
