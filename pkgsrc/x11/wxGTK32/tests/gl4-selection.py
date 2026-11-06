#!/usr/bin/env python3
"""Execute actual configure GL selection against controlled pkg-config metadata.
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
start = s.index('                        if test "$WXGTK4" = 1; then',
                s.index('OPENGL_LIBS="-lGL -lGLU"'))
end = s.index('\n                        fi\n                    fi\n                fi\n\n                if test "$found_gl"', start)
block = s[start:end] + '\n                        fi\n'
with tempfile.TemporaryDirectory(prefix='wx-gl4-selection-', dir=a.work_parent) as tmp:
    work = Path(tmp)
    pkg = work / 'pkg-config'
    pkg.write_text('''#!SHELL
case "$1" in --atleast-pkgconfig-version) exit 0 ;; esac
for arg do requested="$arg"; done
printf '%s\\n' "$requested" >> "$QUERY_LOG"
[ "$requested" = "$AVAILABLE" ] || exit 1
case "$1" in
--cflags) printf '%s\\n' '-I/selected/gl' ;;
--libs) printf '%s\\n' '-lSelectedEGL -lSelectedEpoxy' ;;
esac
'''.replace('SHELL', a.shell))
    pkg.chmod(0o755)
    driver = work / 'configure-gl.sh'
    driver.write_text('''exec 5>/dev/null
as_echo=echo
as_echo_n='printf %s'
as_me=glcheck
as_fn_error() { echo "$2" >&2; exit 1; }
WXGTK4=$1
WXGTK3=1
wxUSE_GLCANVAS_EGL=$2
wx_cv_gdk_wayland=no
OPENGL_LIBS='-lGL -lGLU'
''' + block + '''
printf '%s|%s\\n' "$CPPFLAGS" "$OPENGL_LIBS"
''')
    for name, gtk4, feature, available, success in [
        ('gtk4-egl-epoxy', '1', 'yes', 'egl >= 1.5 epoxy', True),
        ('gtk4-old-egl', '1', 'yes', 'egl >= 1.4', False),
        ('gtk4-missing-epoxy', '1', 'yes', 'egl >= 1.5', False),
        ('gtk4-refuse-disable-egl', '1', 'no', 'egl >= 1.5 epoxy', False),
        ('gtk3-existing-egl', '0', 'yes', 'egl >= 1.4', True)]:
        log = work / (name + '.log')
        env = dict(os.environ, PKG_CONFIG=str(pkg), AVAILABLE=available, QUERY_LOG=str(log))
        for key in ['EGL_CFLAGS', 'EGL_LIBS', 'WAYLAND_EGL_CFLAGS', 'WAYLAND_EGL_LIBS']:
            env.pop(key, None)
        result = subprocess.run([a.shell, str(driver), gtk4, feature], cwd=work,
                                env=env, text=True, capture_output=True)
        assert (result.returncode == 0) == success, (name, result.stdout, result.stderr)
        if gtk4 == '1' and success:
            assert result.stdout.strip().splitlines()[-1] == '-I/selected/gl|-lGL -lGLU -lSelectedEGL -lSelectedEpoxy'
        if gtk4 == '1' and not success:
            assert 'GTK4 GLCanvas requires EGL' in result.stderr, result.stderr
        if gtk4 == '1' and feature != 'no':
            assert set(log.read_text().splitlines()) == {'egl >= 1.5 epoxy'}, name
        if feature == 'no':
            assert not log.exists(), name
        print(name, 'PASS')
