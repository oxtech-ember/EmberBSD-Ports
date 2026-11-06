#!/usr/bin/env python3
"""Exercise actual Autoconf/CMake WebKit selection without compiling wxWidgets.

Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
Pass a source tree with the shared Ports patches applied, and selected tools.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--shell', required=True)
p.add_argument('--cmake', required=True)
p.add_argument('--work-parent', type=Path, required=True)
a = p.parse_args()
source = a.source.resolve()
configure = (source / 'configure').read_text()
start = configure.index('if test "$wxUSE_WEBVIEW" = "yes"; then', configure.index('USE_RICHTEXT=0'))
end = configure.index('\n        elif test "$wxUSE_MAC" = 1', start)
block = configure[start:end] + '\n        fi\n    fi\nfi\n'
# Include the independent extension switch immediately before this block.
block = 'USE_WEBVIEW_WEBKIT2_EXTENSION=0\n' + block

with tempfile.TemporaryDirectory(prefix='wx-webkit-selection-', dir=a.work_parent) as tmp:
    work = Path(tmp)
    pkg = work / 'pkg-config'
    pkg.write_text('''#!SHELL
case "$1" in
--atleast-pkgconfig-version) exit 0 ;;
esac
for arg do requested="$arg"; done
printf '%s\\n' "$requested" >> "$QUERY_LOG"
case ":$AVAILABLE:" in
*":$requested:"*) ;;
*) exit 1 ;;
esac
case "$1" in
--cflags) printf '%s\\n' '-I/selected/include' ;;
--libs) printf '%s\\n' "-l$requested" ;;
esac
'''.replace('SHELL', a.shell))
    pkg.chmod(0o755)
    driver = work / 'selection.sh'
    driver.write_text('''exec 5>/dev/null
as_echo=echo
as_me=selection
as_fn_error() { echo "$2" >&2; exit 1; }
wxUSE_WEBVIEW=yes
wxUSE_WEBVIEW_WEBKIT=yes
wxUSE_GTK=1
WXGTK4=$1
WXGTK3=$2
TOOLKIT_VERSION=$2
''' + block + '''
printf '%s|%s|%s\\n' "$USE_WEBVIEW_WEBKIT2" "$USE_WEBVIEW_WEBKIT2_EXTENSION" "$EXTRALIBS_WEBVIEW"
''')
    cases = [('gtk4', '1', '0', 'webkitgtk-6.0', True, '1|0|-lwebkitgtk-6.0'),
             ('gtk4-reject-gtk3', '1', '0', 'webkit2gtk-4.1', False, ''),
             ('gtk4-missing', '1', '0', '', False, ''),
             ('gtk3', '0', '1', 'webkit2gtk-4.1', True, '1|1|-lwebkit2gtk-4.1')]
    for name, gtk4, gtk3, available, success, expected in cases:
        log = work / (name + '.log')
        env = dict(os.environ, PKG_CONFIG=str(pkg), AVAILABLE=available, QUERY_LOG=str(log))
        for key in ['WEBKIT_CFLAGS', 'WEBKIT_LIBS']:
            env.pop(key, None)
        result = subprocess.run([a.shell, str(driver), gtk4, gtk3], env=env,
                                text=True, capture_output=True)
        assert (result.returncode == 0) == success, (name, result.stdout, result.stderr)
        if success:
            assert result.stdout.strip().splitlines()[-1] == expected, (name, result.stdout)
        if gtk4 == '1':
            assert all(q == 'webkitgtk-6.0' for q in log.read_text().splitlines()), name
            if not success:
                assert 'GTK4 WebView requires webkitgtk-6.0' in result.stderr
        print(name, 'PASS')

    # FindWEBKIT2 must use the actual API6 header/library names, including JSC.
    prefix = work / 'prefix'
    (prefix / 'include/webkitgtk-6.0/webkit').mkdir(parents=True)
    (prefix / 'include/webkitgtk-4.1/webkit2').mkdir(parents=True)
    (prefix / 'lib').mkdir()
    for f in ['include/webkitgtk-6.0/webkit/webkit.h',
              'include/webkitgtk-4.1/webkit2/webkit2.h',
              'lib/libwebkitgtk-6.0.a', 'lib/libjavascriptcoregtk-6.0.a',
              'lib/libwebkit2gtk-4.1.a', 'lib/libjavascriptcoregtk-4.1.a']:
        (prefix / f).touch()
    script = work / 'find.cmake'
    script.write_text('''set(CMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH OFF)
set(CMAKE_FIND_USE_CMAKE_SYSTEM_PATH OFF)
set(CMAKE_FIND_USE_PACKAGE_ROOT_PATH OFF)
set(CMAKE_FIND_LIBRARY_PREFIXES lib)
set(CMAKE_FIND_LIBRARY_SUFFIXES .a)
set(CMAKE_PREFIX_PATH "''' + prefix.as_posix() + '''")
set(CMAKE_MODULE_PATH "''' + (source / 'build/cmake/modules').as_posix() + '''")
find_package(WEBKIT2 ${API} REQUIRED)
if(NOT WEBKIT2_LIBRARY MATCHES "${LIBNAME}\\\\.a$")
  message(FATAL_ERROR "Wrong API library: ${WEBKIT2_LIBRARY}")
endif()
if(NOT WEBKIT2_INCLUDE_DIR MATCHES "webkitgtk-${API}$")
  message(FATAL_ERROR "Wrong API headers: ${WEBKIT2_INCLUDE_DIR}")
endif()
''')
    for api, name in [('6.0', 'webkitgtk-6.0'), ('4.1', 'webkit2gtk-4.1')]:
        subprocess.run([a.cmake, '-DAPI=' + api, '-DLIBNAME=' + name, '-P', str(script)], check=True)
        print('cmake-' + api, 'PASS')
    (prefix / 'lib/libjavascriptcoregtk-6.0.a').unlink()
    result = subprocess.run([a.cmake, '-DAPI=6.0', '-DLIBNAME=webkitgtk-6.0', '-P', str(script)],
                            text=True, capture_output=True)
    assert result.returncode and 'WEBKIT2_JS_LIBRARY' in result.stderr, result
    print('cmake-missing-jsc PASS')
