#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed target Libtool acceptance.
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 NEW_OUTPUT" >&2; exit 2; }
[ "$(uname -s)" = NetBSD ] || exit 2
case "$1" in /*) ;; *) exit 2 ;; esac
case "$1" in *[!a-zA-Z0-9_./-]*) exit 2 ;; esac
[ ! -e "$1" ] && [ ! -L "$1" ] || exit 2
export PATH=/usr/pkg/gcc16/bin:/usr/pkg/bin:/usr/pkg/sbin:/bin:/usr/bin:/sbin:/usr/sbin
unset LD_LIBRARY_PATH LD_PRELOAD LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH
pkg_info -e libtool-base-2.6.2nb1
pkg_info -e 'gcc16>=16.2.0nb1'
mkdir -p "$1"
cd "$1"
output=$(pwd -P)
uname -a > platform.txt
pkg_admin check libtool-base > package-integrity.txt
libtool --config > config.txt
grep -qx max_cmd_len=196608 config.txt
! grep -E '/private/|/opt/homebrew/|apple-darwin' config.txt
cat > answer.c <<'SOURCE'
int c_answer(void) { return 42; }
SOURCE
cat > answer.cc <<'SOURCE'
#include <stdexcept>
extern "C" int c_answer(void);
extern "C" int answer(void)
{
    try { throw std::runtime_error("across the selected C++ runtime"); }
    catch (const std::exception &) { return c_answer(); }
}
SOURCE
cat > main.cc <<'SOURCE'
extern "C" int answer(void);
int main() { return answer() == 42 ? 0 : 1; }
SOURCE
mkdir -p installed/lib installed/bin
libtool --tag=CC --mode=compile gcc -std=c11 -Wall -Wextra -Werror -c answer.c -o c-answer.lo
libtool --tag=CXX --mode=compile g++ -std=c++20 -Wall -Wextra -Werror -c answer.cc -o answer.lo
libtool --tag=CXX --mode=link g++ -o libanswer.la c-answer.lo answer.lo \
    -rpath "$output/installed/lib" -version-info 3:0:1
libtool --mode=install install -c libanswer.la "$output/installed/lib/libanswer.la"
libtool --mode=finish "$output/installed/lib"
libtool --tag=CXX --mode=link g++ -std=c++20 main.cc \
    "$output/installed/lib/libanswer.la" -o shared-consumer
libtool --mode=install install -c shared-consumer "$output/installed/bin/shared-consumer"
"$output/installed/bin/shared-consumer"
ldd "$output/installed/bin/shared-consumer" | sed 's,/\./,/,g' > consumer-linkage.txt
grep -Fq "$output/installed/lib/libanswer.so.2" consumer-linkage.txt
grep -q '/usr/pkg/gcc16/lib/libstdc++.so.7' consumer-linkage.txt
! grep -q 'libstdc++.so.9' consumer-linkage.txt
libtool --tag=CXX --mode=link g++ -std=c++20 -static-libtool-libs main.cc \
    "$output/installed/lib/libanswer.la" -o static-consumer
./static-consumer
ldd ./static-consumer > static-linkage.txt
! grep -q 'libanswer.so' static-linkage.txt
# Exercise the installed shared-only pkgsrc entry point too.
shlibtool --tag=CC --mode=compile gcc -c answer.c -o shared-only.lo
test -f .libs/shared-only.o
mkdir bootstrap
cd bootstrap
cat > configure.ac <<'SOURCE'
AC_INIT([ember-libtool-consumer], [1])
AC_CONFIG_AUX_DIR([build-aux])
AC_CONFIG_MACRO_DIRS([m4])
LT_INIT
AC_OUTPUT
SOURCE
libtoolize --copy --force
test -s build-aux/ltmain.sh
test -s m4/libtool.m4
test -s m4/ltversion.m4
cd ..
libtool --mode=uninstall rm -f "$output/installed/lib/libanswer.la"
test ! -e installed/lib/libanswer.so
test ! -e installed/lib/libanswer.a
echo 'PASS: installed C/C++ shared and static consumers, runtime, libtoolize, shlibtool and uninstall'
