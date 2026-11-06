#!/usr/bin/env python3
"""Execute the patched configure spellchecker selection with controlled metadata.
Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--shell', required=True)
p.add_argument('--work-parent', type=Path, required=True)
a = p.parse_args()
s = (a.source / 'configure').read_text()
start = s.index('if test "$wxUSE_SPELLCHECK" = "yes"; then')
end = s.index('\nfi', s.index('#define wxUSE_SPELLCHECK 1', start)) + len('\nfi')
block = s[start:end]
with tempfile.TemporaryDirectory(prefix='wx-spelling-selection-', dir=a.work_parent) as tmp:
    work = Path(tmp)
    pkg = work / 'pkg-config'
    pkg.write_text('''#!SHELL
case "$1" in --atleast-pkgconfig-version) exit 0 ;; esac
for arg do requested="$arg"; done
printf '%s\\n' "$requested" >> "$QUERY_LOG"
[ "$requested" = "$AVAILABLE" ] || exit 1
case "$1" in
--cflags) printf '%s\\n' '-I/selected/include' ;;
--libs) printf '%s\\n' "-l$requested" ;;
esac
'''.replace('SHELL', a.shell))
    pkg.chmod(0o755)
    driver = work / 'configure-spelling.sh'
    driver.write_text('''exec 5>/dev/null
as_echo=echo
as_me=spellcheck
as_fn_error() { echo "$2" >&2; exit 1; }
wxUSE_SPELLCHECK=$1
WXGTK4=$2
WXGTK3=1
''' + block + '''
printf '%s|%s\\n' "$wxUSE_SPELLCHECK" "$GUI_TK_LIBRARY"
''')
    for name, feature, gtk4, available, success, expected in [
        ('gtk4', 'yes', '1', 'libspelling-1', True, 'yes| -llibspelling-1'),
        ('gtk4-reject-gspell', 'yes', '1', 'gspell-1', False, ''),
        ('gtk4-missing', 'yes', '1', '', False, ''),
        ('gtk3', 'yes', '0', 'gspell-1', True, 'yes| -lgspell-1'),
        ('explicit-feature-off', 'no', '1', '', True, 'no|')]:
        log = work / (name + '.log')
        env = dict(os.environ, PKG_CONFIG=str(pkg), AVAILABLE=available, QUERY_LOG=str(log))
        for key in ['GSPELL_CFLAGS', 'GSPELL_LIBS', 'SPELLING_CFLAGS', 'SPELLING_LIBS']:
            env.pop(key, None)
        result = subprocess.run([a.shell, str(driver), feature, gtk4], cwd=work, env=env,
                                text=True, capture_output=True)
        assert (result.returncode == 0) == success, (name, result.stdout, result.stderr)
        if success:
            assert result.stdout.strip().splitlines()[-1] == expected, (name, result.stdout)
        if gtk4 == '1' and feature == 'yes':
            assert all(q == 'libspelling-1' for q in log.read_text().splitlines()), name
            if not success:
                assert 'GTK4 spell checking requires libspelling-1' in result.stderr
        if feature == 'no':
            assert not log.exists(), name
        print(name, 'PASS')
