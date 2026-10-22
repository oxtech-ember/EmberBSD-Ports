#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed Meson/Ninja C/C++ consumer acceptance.
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 NEW_OUTPUT" >&2; exit 2; }
[ "$(uname -s)" = NetBSD ] || exit 2
case "$1" in /*) ;; *) exit 2;; esac
case "$1" in *[!a-zA-Z0-9_./-]*) exit 2;; esac
[ ! -e "$1" ] && [ ! -L "$1" ] || exit 2
export PATH=/usr/pkg/gcc16/bin:/usr/pkg/bin:/usr/pkg/sbin:/bin:/usr/bin:/sbin:/usr/sbin
unset LD_LIBRARY_PATH LD_PRELOAD LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH
unset PYTHONHOME PYTHONPATH CC CXX CFLAGS CXXFLAGS LDFLAGS
work=$1
mkdir -p "$work/source"
cd "$work"
pkg_info -e meson-1.12.1
pkg_info -e ninja-build-1.13.2
pkg_info -e binutils-2.47nb2
pkg_admin check meson ninja-build binutils > package-integrity.txt
uname -a > platform.txt
meson --version > meson-version.txt
ninja --version > ninja-version.txt
# The bootstrap GCC package hardcodes base as/ld. Keep the current tools
# explicit until its default-tool migration is accepted. This checks direct
# ELF links; it does not establish collect2 or LTO support.
/usr/pkg/gcc16/bin/gcc -dumpspecs > installed.specs
awk '
    /^\*invoke_as:$/ { block = 1; print; next }
    block && /^$/ { block = 0; print; next }
    block { changed += sub(/(^|[[:space:]])as[[:space:]]/, " /usr/pkg/gnu/bin/as "); print }
    END { if (changed != 1) exit 1 }
' installed.specs > selected-tools.specs
printf '*linker:\n/usr/pkg/gnu/bin/ld\n\n' >> selected-tools.specs
cat > native.ini <<EOF
[binaries]
c = ['/usr/pkg/gcc16/bin/gcc', '-specs=$work/selected-tools.specs']
cpp = ['/usr/pkg/gcc16/bin/g++', '-specs=$work/selected-tools.specs']
pkg-config = '/usr/pkg/bin/pkg-config'
[built-in options]
c_link_args = ['-Wl,-rpath,/usr/pkg/gcc16/lib']
cpp_link_args = ['-Wl,-rpath,/usr/pkg/gcc16/lib']
EOF
cat > source/meson.options <<'EOF'
option('answer', type: 'integer', value: 42)
EOF
cat > source/meson.build <<'EOF'
project('ember-installed-tools', 'c', 'cpp', version: '1.0', meson_version: '>=1.12.1',
  default_options: ['c_std=c11', 'cpp_std=c++20', 'warning_level=3', 'werror=true'])
config = configuration_data()
config.set('ANSWER', get_option('answer'))
configure_file(output: 'config.h', configuration: config)
lib = shared_library('emberprobe', 'library.cc', install: true,
  install_rpath: '/usr/pkg/gcc16/lib')
static = static_library('emberstatic', 'static.c')
probe = executable('probe', 'main.cc', link_with: [lib, static], install: true,
  install_rpath: join_paths(get_option('prefix'), get_option('libdir')) + ':/usr/pkg/gcc16/lib')
test('c-cpp-dso', probe)
python = dependency('python-3.14-embed', method: 'pkg-config', version: '>=3.14')
embedded = executable('embedded', 'embedded.c', dependencies: python,
  install: true, install_rpath: '/usr/pkg/lib:/usr/pkg/gcc16/lib')
test('python-embedding', embedded)
pkg = import('pkgconfig')
pkg.generate(lib, name: 'emberprobe', description: 'Installed shared C++ consumer',
  version: meson.project_version())
EOF
cat > source/library.cc <<'CXX'
#include "config.h"
#include <stdexcept>
extern "C" int ember_answer(void)
{
    throw std::runtime_error("shared runtime");
}
extern "C" int ember_value(void) { return ANSWER; }
CXX
cat > source/static.c <<'C'
int ember_static(void) { return 7; }
C
cat > source/main.cc <<'CXX'
#include "config.h"
#include <cstdio>
#include <stdexcept>
#include <cstring>
extern "C" int ember_answer(void);
extern "C" int ember_value(void);
extern "C" int ember_static(void);
int main()
{
    try { (void)ember_answer(); return 1; }
    catch (const std::exception &error) {
        if (std::strcmp(error.what(), "shared runtime") != 0) return 1;
    }
    if (ember_value() != ANSWER || ember_static() != 7) return 1;
    std::printf("%d\n", ember_value());
    return 0;
}
CXX
cat > source/embedded.c <<'C'
#define PY_SSIZE_T_CLEAN
#include <Python.h>
int main(void)
{
    Py_Initialize();
    PyObject *module = PyImport_ImportModule("ssl");
    if (!module) { PyErr_Print(); return 1; }
    Py_DECREF(module);
    return Py_FinalizeEx() < 0;
}
C
meson setup build source --native-file native.ini --prefix "$work/prefix" --libdir lib
meson compile -C build -j2
meson test -C build --print-errorlogs
[ "$(build/probe)" = 42 ]
ninja -C build -t browse --help > browse-help.txt
grep -q -- '--no-browser' browse-help.txt
ninja -C build -n > unchanged.txt
grep -q 'no work to do' unchanged.txt
meson configure build -Danswer=43
meson compile -C build -j2
meson test -C build --print-errorlogs
[ "$(build/probe)" = 43 ]
# An actual compiler failure must propagate through both build tools.
cp source/static.c source/static.saved
printf '\n#error intentional acceptance failure\n' >> source/static.c
if meson compile -C build -j2 > rejected-build.txt 2>&1; then
    echo 'A compiler error unexpectedly succeeded' >&2; exit 1
fi
grep -q 'intentional acceptance failure' rejected-build.txt
mv source/static.saved source/static.c
meson compile -C build -j2
meson test -C build --print-errorlogs
meson install -C build --no-rebuild --destdir "$work/stage"
meson install -C build --no-rebuild
[ "$(prefix/bin/probe)" = 43 ]
prefix/bin/embedded
ldd prefix/bin/probe | sed 's,/\./,/,g' > installed-linkage.txt
grep -Fq "$work/prefix/lib/libemberprobe.so" installed-linkage.txt
grep -q '/usr/pkg/gcc16/lib/libstdc++.so.7' installed-linkage.txt
if grep -E 'not found|libstdc\+\+\.so\.9|/stage/|/build/' installed-linkage.txt; then
    echo 'Installed executable retained the wrong library paths' >&2; exit 1
fi
readelf -d "stage$work/prefix/bin/probe" > staged-dynamic.txt
if grep -E '/stage/|/build/|/private/|/opt/homebrew/' staged-dynamic.txt; then
    echo 'Staged executable retained a build path' >&2; exit 1
fi
cat > installed-consumer.cc <<'CXX'
extern "C" int ember_value(void);
int main() { return ember_value() != 43; }
CXX
export PKG_CONFIG_PATH=$work/prefix/lib/pkgconfig
g++ -specs="$work/selected-tools.specs" -std=c++20 installed-consumer.cc $(pkg-config --cflags --libs emberprobe) \
    -Wl,-R"$work/prefix/lib" -Wl,-R/usr/pkg/gcc16/lib -o installed-consumer
./installed-consumer
meson introspect build --targets > targets.json
echo 'PASS: installed Meson/Ninja and browse interpreter, C/C++ shared/static consumers, embedding, incremental build, failure propagation and staged/installed RPATH'
