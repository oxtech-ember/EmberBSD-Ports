#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Verify the actual batched recovery query preserves values and errors."""
from pathlib import Path
import os
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] / 'cross-bulk.sh').read_text()
start = source.index('    recovery_vars=$(mk ')
end = source.index('    pkg_add_wrapper "$real_pkg_add"', start)
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    script = root / 'check.sh'
    script.write_text('''#!/bin/sh
PKGSRCDIR=/fixture/ports
mk() {
    printf '%s\\n' "$@" >> "$CALLS"
    [ "$QUERY_STATUS" = 0 ] || return "$QUERY_STATUS"
    printf '%s\\n' "$QUERY_VALUES"
}
load() {
''' + source[start:end] + '''
}
load || exit $?
printf '<%s>\\n' "$real_pkg_add" "$target_pkg_info" "$target_settings" "$packages"
''')
    calls = root / 'calls'
    def run(values, status=0):
        calls.write_text('')
        result = subprocess.run(['sh', str(script)], capture_output=True, text=True,
                                env=dict(os.environ, CALLS=str(calls),
                                         QUERY_STATUS=str(status), QUERY_VALUES=values))
        assert calls.read_text().splitlines() == [
            '-C', '/fixture/ports/pkgtools/pkg_install', 'show-vars',
            'VARNAMES=NATIVE_PKG_ADD_CMD PKG_INFO CROSSTARGETSETTINGS PACKAGES']
        return result
    fields = ['/native/sbin/pkg_add -K /native/db', '/native/sbin/pkg_info -K /target/db',
              'TARGET_ARCH=aarch64 TARGET_SETTING=selected', '/build/packages with spaces']
    result = run('\n'.join(fields))
    assert result.returncode == 0 and not result.stderr, result.stderr
    assert result.stdout == ''.join('<' + item + '>\n' for item in fields)
    fields[2] = ''
    result = run('\n'.join(fields))
    assert result.returncode == 0 and result.stdout == ''.join('<' + item + '>\n' for item in fields)
    for index, message in [(0, 'NATIVE_PKG_ADD_CMD is empty'), (1, 'The target PKG_INFO is empty')]:
        invalid = fields.copy(); invalid[index] = ''
        result = run('\n'.join(invalid))
        assert result.returncode == 2 and message in result.stderr and not result.stdout
    # Last mandatory field is empty/truncated: the record is rejected before use.
    for values in ('\n'.join(fields[:-1]), '\n'.join(fields[:-1]) + '\n',
                   '\n'.join(fields) + '\nextra', ''):
        result = run(values)
        assert result.returncode == 2 and not result.stdout
        assert 'Unexpected package recovery environment metadata' in result.stderr
    result = run('\n'.join(fields), status=1)
    assert result.returncode == 2 and not result.stdout
print('PASS: one recovery query, intact fields, optional empty settings, malformed/missing values and query failure')
