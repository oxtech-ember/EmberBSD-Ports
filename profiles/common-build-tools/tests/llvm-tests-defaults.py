#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check LLVM-family tests default-off policy with pkgsrc's real bmake options."""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PACKAGES = {
    'lang/llvm': ('PKG_OPTIONS.llvm', 'z3'),
    'lang/clang': ('PKG_OPTIONS.clang', 'z3'),
    'devel/lld': ('PKG_OPTIONS.lld', None),
}


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', type=Path, required=True)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--work-parent', type=Path, required=True)
    args = parser.parse_args()
    require(args.bmake.is_file() and args.bmake.is_absolute(), 'Use an absolute bmake executable')
    require((args.pkgsrc / 'mk/bsd.options.mk').is_file(), 'Expected an exported pkgsrc tree')
    require(args.work_parent.is_dir() and args.work_parent.is_absolute(), 'Use an existing absolute work directory')

    for profile in (ROOT / 'profiles/common-build-tools/mk.conf',
                    ROOT / 'profiles/common-graphics/mk.conf'):
        text = profile.read_text()
        require(not re.search(r'^\s*PKG_OPTIONS\.(?:llvm|clang|lld)\s*\+?=\s*[^\n]*\btests\b', text, re.M),
                'A common profile forces LLVM-family tests: ' + str(profile))

    with tempfile.TemporaryDirectory(prefix='ember-llvm-tests-options-', dir=args.work_parent) as temporary:
        work = Path(temporary)
        defaults = work / 'defaults.mk.conf'
        defaults.write_text((ROOT / 'pkgsrc/defaults.mk.conf').read_text())
        shutil.copyfile(ROOT / 'pkgsrc/versions.mk', work / 'EMBERBSD-VERSIONS.MK')

        def selected(package, role, local=None, global_options=None):
            option_var, other = PACKAGES[package]
            supported = 'tests' + (' ' + other if other else '')
            settings = work / 'settings.mk'
            rows = []
            if local is not None:
                rows.append(option_var + '=' + local)
            if global_options is not None:
                rows.append('PKG_DEFAULT_OPTIONS=' + global_options)
            settings.write_text('\n'.join(rows) + ('\n' if rows else ''))
            makefile = work / 'fixture.mk'
            makefile.write_text(f'''BSD_PKG_MK=yes
PKGPATH={package}
USE_CROSS_COMPILE={'yes' if role == 'target' else 'no'}
PKG_OPTIONS_VAR={option_var}
PKG_SUPPORTED_OPTIONS={supported}
PKG_SUGGESTED_OPTIONS=tests
.include "{settings}"
.include "{defaults}"
.include "{args.pkgsrc / 'mk/bsd.options.mk'}"
all:
\t@printf '%s\\n' "${{PKG_OPTIONS}}"
''')
            command = [str(args.bmake), '-r', '-m', str(args.pkgsrc / 'mk'), '-f', str(makefile)]
            command.append('all')
            result = subprocess.run(command, capture_output=True, text=True)
            require(result.returncode == 0, f'{package} {role} metadata failed:\n{result.stdout}{result.stderr}')
            lines = result.stdout.splitlines()
            require(len(lines) == 1, f'{package} {role} returned unexpected metadata: {result.stdout!r}')
            return set(lines[0].split())

        checks = 0
        for package, (_, other) in PACKAGES.items():
            for role in ('native', 'target'):
                require('tests' not in selected(package, role), f'{package} {role}: tests defaulted on')
                checks += 1
                if other:
                    options = selected(package, role, local=other)
                    require(other in options and 'tests' not in options,
                            f'{package} {role}: unrelated option enabled tests: {sorted(options)}')
                    checks += 1
                require('tests' in selected(package, role, local='tests'),
                        f'{package} {role}: package-specific opt-in was ignored')
                checks += 1
                require('tests' not in selected(package, role, local='-tests'),
                        f'{package} {role}: package-specific opt-out was ignored')
                checks += 1
                require('tests' in selected(package, role, global_options='tests'),
                        f'{package} {role}: global opt-in was ignored')
                checks += 1
                require('tests' not in selected(package, role, global_options='-tests'),
                        f'{package} {role}: global opt-out was ignored')
                checks += 1
        print(f'PASS: {checks} LLVM-family option selections through pkgsrc bmake')


if __name__ == '__main__':
    main()
