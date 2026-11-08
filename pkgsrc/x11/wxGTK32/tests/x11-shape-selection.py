#!/usr/bin/env python3
"""Execute the actual GTK4 X11 dependency selection with controlled metadata.
Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--shell', required=True)
parser.add_argument('--work-parent', type=Path, required=True)
a = parser.parse_args()
source = (a.source / 'configure').read_text()
start = source.index('        if test "$WXGTK4" = 1 && $PKG_CONFIG --exists gtk4-x11; then')
end = source.index('\n        fi', start) + len('\n        fi')
block = source[start:end]
with tempfile.TemporaryDirectory(prefix='wx-x11-selection-', dir=a.work_parent) as tmp:
    work = Path(tmp)
    pkg = work / 'pkg-config'
    pkg.write_text('''#!SHELL
op=$1
shift
printf '%s\\n' "$*" >> "$QUERY_LOG"
case "$*" in
    gtk4-x11) [ "$HAS_X11" = yes ]; exit $? ;;
    "xi xext") [ "$HAS_XI" = yes ] && [ "$HAS_XEXT" = yes ] || exit 1 ;;
    xi) [ "$HAS_XI" = yes ] || exit 1 ;;
    *) exit 1 ;;
esac
case "$op" in
    --libs) echo '-lXi -lXext' ;;
    --cflags) echo '-I/selected/X11' ;;
esac
'''.replace('SHELL', a.shell))
    pkg.chmod(0o755)
    driver = work / 'configure-x11.sh'
    driver.write_text('''as_fn_error() { echo "$2" >&2; exit 1; }
WXGTK4=$1
GUI_TK_LIBRARY='-lgtk-4'
TOOLKIT_INCLUDE='-I/selected/gtk4'
''' + block + '''
printf '%s|%s\\n' "$TOOLKIT_INCLUDE" "$GUI_TK_LIBRARY"
''')
    for name, gtk4, x11, xi, xext, success in [
        ('x11-missing-shape', '1', 'yes', 'yes', 'no', False),
        ('x11-complete', '1', 'yes', 'yes', 'yes', True),
        ('x11-missing-input', '1', 'yes', 'no', 'yes', False),
        ('wayland-only', '1', 'no', 'no', 'no', True),
        ('gtk3-unchanged', '0', 'yes', 'no', 'no', True),
    ]:
        log = work / (name + '.log')
        result = subprocess.run([a.shell, str(driver), gtk4], text=True,
                                capture_output=True,
                                env=dict(os.environ, PKG_CONFIG=str(pkg), HAS_X11=x11,
                                         HAS_XI=xi, HAS_XEXT=xext, QUERY_LOG=str(log)))
        assert (result.returncode == 0) == success, (name, result.stdout, result.stderr)
        if not success:
            assert 'requires libXi and libXext' in result.stderr, result.stderr
        if name == 'x11-complete':
            assert result.stdout.strip() == '-I/selected/gtk4 -I/selected/X11|-lgtk-4 -lXi -lXext'
        if name == 'gtk3-unchanged':
            assert not log.exists()
        if name == 'wayland-only':
            assert log.read_text().splitlines() == ['gtk4-x11']
        print(name, 'PASS')
