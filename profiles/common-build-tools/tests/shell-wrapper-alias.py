#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise pkgsrc's generated shell-wrapper alias guard from its source."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile


def alias_recipe(pkgsrc):
    source = pkgsrc / 'mk/wrapper/bsd.wrapper.mk'
    lines = source.read_text().splitlines()
    for index, line in enumerate(lines):
        if 'if [ ! -x' in line and '${.TARGET}' in line:
            condition = line.strip().rstrip('\\').strip()
            link = lines[index + 2].strip().rstrip('\\').strip()
            break
    else:
        raise SystemExit('pkgsrc shell-wrapper alias recipe shape changed')
    match = re.fullmatch(
        r'\$\{LN\}\s+(-f\$\{WRAPPER_USE_SYMLINK:Ds\})\s+'
        r'("?\$\$wrapper"?)\s+("?\$\{\.TARGET\}"?);', link)
    if not match:
        raise SystemExit('pkgsrc shell-wrapper link command shape changed')
    _, source_arg, destination_arg = match.groups()
    shell_condition = condition.replace('${.TARGET}', '$target').replace('$$wrapper', '$wrapper')
    shell_link = f'ln -f {source_arg.replace("$$wrapper", "$wrapper")} '
    shell_link += f'{destination_arg.replace("${.TARGET}", "$target")}'
    return f'wrapper=$1; target=$2; {shell_condition} {shell_link}; fi', condition, link


def run_recipe(recipe, source, destination):
    return subprocess.run(['/bin/sh', '-c', recipe, 'alias-test', str(source), str(destination)],
                          capture_output=True, text=True)


def require_no_alias(recipe, source, destination, label):
    result = run_recipe(recipe, source, destination)
    if result.returncode:
        raise SystemExit(f'{label}: alias recipe failed: {result.stderr.strip()}')
    if destination.exists() or destination.is_symlink():
        raise SystemExit(f'{label}: created an alias for an invalid compiler path')


def require_alias(recipe, source, destination, label):
    result = run_recipe(recipe, source, destination)
    if result.returncode:
        raise SystemExit(f'{label}: alias recipe failed: {result.stderr.strip()}')
    if not destination.is_file() or not destination.stat().st_mode & 0o111:
        raise SystemExit(f'{label}: did not create an executable alias '
                         f'(stdout={result.stdout!r}, stderr={result.stderr!r}, '
                         f'exists={destination.exists()}, symlink={destination.is_symlink()})')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    args = parser.parse_args()
    recipe, condition, link = alias_recipe(args.pkgsrc)
    with tempfile.TemporaryDirectory(prefix='pkgsrc-wrapper-alias-') as directory:
        root = Path(directory)
        bin_dir = root / 'host-tools'
        bin_dir.mkdir()
        dest_dir = root / 'wrapper-bin'
        dest_dir.mkdir()

        directory_source = bin_dir / 'compiler-directory'
        directory_source.mkdir()
        require_no_alias(recipe, directory_source, dest_dir / 'directory-alias', 'directory source')
        require_no_alias(recipe, '', dest_dir / 'empty-alias', 'empty source')
        require_no_alias(recipe, bin_dir / 'missing-compiler', dest_dir / 'missing-alias', 'missing source')

        spaced_bin = root / 'host tools'
        spaced_bin.mkdir()
        spaced_dest = root / 'wrapper bin'
        spaced_dest.mkdir()

        executable = spaced_bin / 'compiler with spaces'
        executable.write_text('#!/bin/sh\nexit 0\n')
        executable.chmod(0o755)
        require_alias(recipe, executable, spaced_dest / 'compiler alias', 'regular executable')

        symlink = spaced_bin / 'compiler symlink'
        symlink.symlink_to(executable)
        require_alias(recipe, symlink, spaced_dest / 'symlink alias', 'symlink to executable')

        nonexecutable = spaced_bin / 'nonexecutable compiler'
        nonexecutable.write_text('not executable\n')
        nonexecutable.chmod(0o644)
        require_no_alias(recipe, nonexecutable, spaced_dest / 'nonexecutable alias', 'nonexecutable source')

    if '"$$wrapper"' not in condition or '"${.TARGET}"' not in condition:
        raise SystemExit('pkgsrc alias guard must quote wrapper and destination paths')
    if '"$$wrapper"' not in link or '"${.TARGET}"' not in link:
        raise SystemExit('pkgsrc alias link command must quote source and destination paths')

    print('PASS: pkgsrc shell-wrapper aliases require a regular executable source')


if __name__ == '__main__':
    main()
