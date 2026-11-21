#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Keep pkg_info status and every matched name across both graph callers."""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_package_current import native_current_pattern, native_package_current, native_package_names


with tempfile.TemporaryDirectory() as directory:
    info = Path(directory) / 'pkg_info'
    info.write_text('''#!/bin/sh
case "$2" in
  "lib-foo>=1.2nb3") echo lib-foo-1.3; echo lib-foo-1.2nb3 ;;
  broken) exit 3 ;;
  *) exit 1 ;;
esac
''')
    info.chmod(0o755)
    assert native_current_pattern('lib-foo', 'lib-foo-1.2nb3') == 'lib-foo>=1.2nb3'
    assert native_current_pattern('lib-foo', 'unexpected') == 'lib-foo'
    assert native_package_names([info], 'lib-foo', 'lib-foo-1.2nb3') == ('lib-foo-1.2nb3','lib-foo-1.3')
    assert not native_package_current([info], 'missing', 'missing-1')
    try:
        native_package_current([info], 'broken', 'unexpected')
    except RuntimeError as error:
        assert 'status 3' in str(error)
    else:
        raise AssertionError('pkgdb error treated as an absent package')
print('PASS: native package queries preserve matches, absence and database errors')
