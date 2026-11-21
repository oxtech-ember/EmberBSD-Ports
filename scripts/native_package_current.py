# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors.
"""Use cross-bulk's native package selection and pkg_info's version matcher."""
from pathlib import Path
import subprocess


_QUERY = Path(__file__).with_name('native-package-current.sh')


def native_current_pattern(base, name):
    return subprocess.check_output(['/bin/sh', str(_QUERY), 'pattern', base, name],
                                   text=True).rstrip('\n')


def native_package_names(pkg_info_argv, base, name, *, env=None, timeout=None):
    result = subprocess.run(['/bin/sh', str(_QUERY), 'names', base, name, *pkg_info_argv],
                            text=True, capture_output=True, env=env, timeout=timeout)
    if result.returncode == 1:
        return ()
    if result.returncode:
        raise RuntimeError(f'pkg_info -e failed with status {result.returncode}: {result.stderr.strip()}')
    names = result.stdout.splitlines()
    if not names or any(not value or any(c.isspace() for c in value) for value in names):
        raise RuntimeError('pkg_info -e did not identify the matching native package')
    return tuple(sorted(set(names)))


def native_package_current(pkg_info_argv, base, name, *, env=None, timeout=None):
    return bool(native_package_names(pkg_info_argv, base, name, env=env, timeout=timeout))
