#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Causal test for the Libtool Flang-on-NetBSD
# case.  Upstream Libtool knows Flang only on Linux and FreeBSD, so on NetBSD
# the FC tag gets an empty wl and the pkgsrc NetBSD archive_cmds pass a bare
# -soname to flang, which rejects it.  The test configures the pkgsrc-patched
# Libtool for the target and builds a versioned Fortran shared library.
#
# Usage: libtool-flang-netbsd.sh DISTFILE PATCHDIR CLANG FLANG LD SYSROOT
#            RTLIBDIR TARGET READELF OUT
#   DISTFILE is the libtool-<version>.tar.gz distfile, PATCHDIR the recipe's
#   patches directory, RTLIBDIR the directory with the shared Flang runtime.
#   OUT must not exist.
set -eu
if [ "$#" -ne 10 ]; then
	echo "usage: $0 DISTFILE PATCHDIR CLANG FLANG LD SYSROOT RTLIBDIR TARGET READELF OUT" >&2
	exit 2
fi
dist=$1 patches=$2 clang=$3 flang=$4 ld=$5 sysroot=$6 rtlib=$7 target=$8
readelf=$9 out=${10}
for path in "$dist" "$patches" "$clang" "$flang" "$ld" "$sysroot" "$rtlib" \
    "$readelf" "$out"; do
	case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
	case "$path" in *[!A-Za-z0-9_./+-]*)
		echo 'Use paths without shell metacharacters' >&2; exit 2 ;;
	esac
done
fail() { echo "FAIL: $*" >&2; exit 1; }

mkdir "$out"
mkdir "$out/bin" "$out/lib"
# The basename flang is what fortran.mk installs as the pkgsrc FC.
cat > "$out/bin/flang" <<SH
#!/bin/sh
exec "$flang" --target=$target --sysroot="$sysroot" -fuse-ld="$ld" -L"$rtlib" "\$@"
SH
cat > "$out/bin/cc" <<SH
#!/bin/sh
exec "$clang" --target=$target --sysroot="$sysroot" -fuse-ld="$ld" "\$@"
SH
chmod +x "$out/bin/flang" "$out/bin/cc"

(cd "$out" && gzip -dc "$dist" | tar -xf -)
src=$(cd "$out" && echo libtool-*)
[ -d "$out/$src" ] || fail "distfile did not extract one libtool tree"
for p in "$patches"/patch-*; do
	patch -s -f -N -F 0 -p0 -d "$out/$src" < "$p" >"$out/patch.log" 2>&1 ||
		{ cat "$out/patch.log" >&2; fail "patch $p does not apply"; }
done
(cd "$out/$src" && ./configure --host="$target" --disable-ltdl-install \
    CC="$out/bin/cc" FC="$out/bin/flang" F77="$out/bin/flang" \
    >"$out/configure.log" 2>&1) ||
	{ tail -20 "$out/configure.log" >&2; fail 'libtool configure failed'; }
lt=$out/$src/libtool
grep -q '^# ### BEGIN LIBTOOL TAG CONFIG: FC$' "$lt" || fail 'no FC tag'

cat > "$out/lib/answer.f90" <<'F90'
integer function answer()
  answer = 42
end function answer
F90
(cd "$out/lib" &&
	"$lt" --tag=FC --mode=compile "$out/bin/flang" -c answer.f90 &&
	"$lt" --tag=FC --mode=link "$out/bin/flang" -rpath /usr/pkg/lib \
	    -version-info 1:0:0 -o libanswer.la answer.lo) \
    >"$out/build.log" 2>&1 ||
	{ cat "$out/build.log" >&2; fail 'libtool Fortran shared library failed'; }
so=$out/lib/.libs/libanswer.so.1
[ -f "$so" ] || fail 'libtool did not build libanswer.so.1'
case $(file -b "$so") in
ELF*64-bit*aarch64*) ;;
*) fail "unexpected library: $(file -b "$so")" ;;
esac
"$readelf" -d "$so" | grep -q '(SONAME).*\[libanswer\.so\.1\]' ||
	fail 'library lacks the libtool SONAME'
"$readelf" -d "$so" | grep -q '(NEEDED).*\[libflang_rt\.runtime\.so' ||
	fail 'library does not need the shared Flang runtime'
grep -q 'fPIC' "$out/build.log" || fail 'Fortran object was not built PIC'
echo 'PASS: libtool builds a Flang shared library for NetBSD'
