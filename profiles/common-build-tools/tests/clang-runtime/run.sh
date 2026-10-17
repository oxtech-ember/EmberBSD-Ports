#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed compiler and libclang acceptance.
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 NEW_OUTPUT" >&2; exit 2; }
source=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
unset LD_LIBRARY_PATH LD_PRELOAD CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH
cd "$work"
sysctl kern.boottime > boot.before
pkg_info -e clang > package.txt
clang --version > version.txt
grep -q 'version 23.1.3' version.txt
clang -std=c11 -Wall -Wextra -Werror "$source/c-api.c" -I/usr/pkg/include \
    -L/usr/pkg/lib -Wl,-rpath,/usr/pkg/lib -lclang -o c-api > c-build.log 2>&1
clang++ -std=c++20 -Wall -Wextra -Werror -pthread "$source/runtime.cc" -o runtime \
    > cxx-build.log 2>&1
for executable in c-api runtime; do
    timeout -k 5 60 "./$executable" > "$executable.log" 2>&1
    ldd "./$executable" > "$executable.ldd"
    ! grep -q 'not found' "$executable.ldd"
    sha256 "./$executable" >> outputs.sha256
done
grep -q '/usr/pkg/lib/libclang' c-api.ldd
grep -q '/usr/pkg/gcc16/lib/libstdc++' runtime.ldd
clang++ -### "$source/runtime.cc" > native.trace 2>&1
grep -q '/usr/pkg/gcc16/lib/gcc/.*/16.2.0/crtbegin' native.trace
clang++ --no-default-config --sysroot=/ember-unused-sdk -### "$source/runtime.cc" \
    > sdk.trace 2>&1
! grep -q '/usr/pkg/gcc16' sdk.trace
clang++ --target=aarch64-unknown-linux-gnu -### "$source/runtime.cc" > foreign.trace 2>&1
! grep -q '/usr/pkg/gcc16' foreign.trace
printf 'int main(void) { not valid C syntax; }\n' > invalid.c
if clang -c invalid.c > invalid.log 2>&1; then
    echo 'FAIL: invalid C accepted' >&2; exit 1
fi
[ ! -e invalid.o ]
scan-build --help > scan-build-help.log 2>&1
sysctl kern.boottime > boot.after
cmp boot.before boot.after
cat c-api.log
echo 'PASS: native C/C++, GCC16 runtime, libclang, target-config isolation and scan-build loading'
