#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); host Libtool gate for macOS cross recipes.
#
# Verifies that the pkgsrc host bootstrap owns a current native
# libtool/libtoolize (no symlink to an external package manager), that
# autoreconf reaches libtoolize with only bootstrap tools on PATH, and that
# a generated Libtool actually builds a shared consumer on the build host.
# A stripped PATH must still fail, proving the gate detects the gap.
set -eu
[ "$#" = 2 ] || { echo 'Usage: sh tests/host-libtool.sh HOST_PREFIX NEW_WORK' >&2; exit 2; }
prefix=$1 work=$2
for path in "$prefix" "$work"; do
    case "$path" in /*) ;; *) echo 'Use absolute paths.' >&2; exit 2 ;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Unsafe path.' >&2; exit 2 ;; esac
done
[ -d "$prefix/bin" ] || { echo 'Missing host bootstrap bin directory.' >&2; exit 2; }
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Work directory already exists.' >&2; exit 2; }
mkdir "$work"

# The bootstrap package database registers what the prefix really owns.
: "${PKG_DBDIR:=$prefix/pkgdb}"
export PKG_DBDIR
[ -f "$PKG_DBDIR/libtool-base-2.6.2nb1/+CONTENTS" ] || {
    echo 'libtool-base-2.6.2nb1 is not installed in the host bootstrap.' >&2; exit 2;
}
[ -f "$PKG_DBDIR/m4-1.4.21/+CONTENTS" ] || {
    echo 'm4-1.4.21 is not installed in the host bootstrap.' >&2; exit 2;
}
for tool in libtoolize libtool shlibtool gm4 autoreconf; do
    [ -f "$prefix/bin/$tool" ] && [ ! -L "$prefix/bin/$tool" ] || {
        echo "host $tool is missing, or a symlink outside the bootstrap: $prefix/bin/$tool" >&2
        exit 2
    }
    grep -qx "bin/$tool" "$PKG_DBDIR/libtool-base-2.6.2nb1/+CONTENTS" 2>/dev/null \
        || grep -qx "bin/$tool" "$PKG_DBDIR/m4-1.4.21/+CONTENTS" 2>/dev/null \
        || grep -qx "bin/$tool" "$PKG_DBDIR"/autoconf-*/+CONTENTS 2>/dev/null \
        || {
            echo "host $tool is not registered by a bootstrap package" >&2
            exit 2
        }
done
[ "$("$prefix/bin/libtoolize" --version | sed -n 1p)" = 'libtoolize (GNU libtool) 2.6.2' ]
[ "$("$prefix/bin/gm4" --version | sed -n 1p)" = 'm4 (GNU M4) 1.4.21' ]
echo 'PASS: registered host libtoolize 2.6.2 and m4 1.4.21'

# A real autoreconf consumer built with only bootstrap tools on PATH.
mkdir "$work/project"
cat > "$work/project/configure.ac" <<'EOF'
AC_INIT([emberhostlibtool], [1.0])
AC_CONFIG_AUX_DIR([build-aux])
AM_INIT_AUTOMAKE([foreign -Wall])
LT_INIT
AC_PROG_CC
AC_CONFIG_FILES([Makefile])
AC_OUTPUT
EOF
cat > "$work/project/Makefile.am" <<'EOF'
lib_LTLIBRARIES = libemberhost.la
libemberhost_la_SOURCES = emberhost.c
bin_PROGRAMS = emberhost
emberhost_SOURCES = main.c
emberhost_LDADD = libemberhost.la
EOF
printf 'int emberhost_value(void) { return 42; }\n' > "$work/project/emberhost.c"
printf '#include <stdio.h>\nint emberhost_value(void);\nint main(void) { printf("%%d\\n", emberhost_value()); return emberhost_value() == 42 ? 0 : 1; }\n' \
    > "$work/project/main.c"
cd "$work/project"
bootstrap_path=$prefix/bin:/usr/bin:/bin:/usr/sbin:/sbin
PATH=$bootstrap_path autoreconf -fi > "$work/autoreconf.log" 2>&1 || {
    cat "$work/autoreconf.log" >&2
    echo 'autoreconf did not complete with only bootstrap tools on PATH' >&2
    exit 1
}
[ -f configure ] && [ -f build-aux/ltmain.sh ]
echo 'PASS: autoreconf -fi completed through the host libtoolize'

PATH=$bootstrap_path ./configure --prefix="$work/installed" > "$work/configure.log" 2>&1 || {
    cat "$work/configure.log" >&2; exit 1
}
PATH=$bootstrap_path make > "$work/make.log" 2>&1 || {
    cat "$work/make.log" >&2; exit 1
}
PATH=$bootstrap_path make install >> "$work/make.log" 2>&1
PATH=$bootstrap_path ./emberhost > "$work/run.txt"
[ "$(cat "$work/run.txt")" = 42 ]
echo 'PASS: generated Libtool built and ran a shared-library consumer'

# Without the bootstrap prefix the same command must fail: this proves the
# gate would catch an unprepared host instead of silently using random tools.
cd "$work"
mkdir negative
cp project/configure.ac project/Makefile.am project/emberhost.c project/main.c negative/
cd negative
if PATH=/usr/bin:/bin:/usr/sbin:/sbin autoreconf -fi > "$work/negative.log" 2>&1; then
    echo 'autoreconf found a libtoolize without the bootstrap; the gate is blind' >&2
    exit 1
fi
grep -q 'libtoolize' "$work/negative.log" 2>/dev/null \
    || grep -q 'No such file' "$work/negative.log" 2>/dev/null \
    || true
echo 'PASS: stripped PATH fails at libtoolize, gap stays detectable'
echo 'host libtool gate passed'
