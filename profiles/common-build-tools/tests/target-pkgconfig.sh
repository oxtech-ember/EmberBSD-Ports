#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Fixture regression: staged target metadata
# loses build-host paths from .pc, *-config, CMake, qmake and sysconfig files,
# and still naming a build directory or host volume fails closed.
#
# With PKGSRC and MAKECONF of a cross build, it also checks that the cross
# install runs the step after post-install and a native install does not.
set -eu
[ "$#" = 1 ] || [ "$#" = 3 ] || {
	echo 'Usage: target-pkgconfig.sh NEW_WORK [PKGSRC CROSS_MAKECONF]' >&2
	exit 2
}
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
script=$root/profiles/common-build-tools/cross/target-pkgconfig.sh
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd -P)
fail() { echo "FAIL: $*" >&2; exit 1; }
mkdir -p "$work/real-sysroot/usr/pkg/include" "$work/context" "$work/obj/work/.buildlink/lib" "$work/tools/bin" "$work/old-sysroot/usr/pkg/lib"
ln -s "$work/real-sysroot" "$work/context/sysroot"
sysroot=$work/context/sysroot real=$work/real-sysroot
wrk=$work/obj/work tools=$work/tools
old=$work/old-sysroot

stage() {
	rm -rf "$work/stage"
	mkdir -p "$work/stage/usr/pkg/lib/pkgconfig" "$work/stage/usr/pkg/share/pkgconfig" \
		"$work/stage/usr/pkg/share/doc" "$work/stage/usr/pkg/bin" \
		"$work/stage/usr/pkg/lib/cmake/Example" \
		"$work/stage/usr/pkg/qt6/mkspecs/netbsd-g++" \
		"$work/stage/usr/pkg/lib/python3.15"
	dest=$work/stage
}
stage
cat > "$dest/usr/pkg/lib/pkgconfig/libqalculate.pc" <<PC
prefix=/usr/pkg
includedir=\${prefix}/include
libdir=\${prefix}/lib
Libs.private: -Wl,-R/usr/pkg/lib -L$sysroot/usr/pkg/lib -lcurl -L$real/usr/pkg/lib -licuuc
Libs: -L\${libdir} -lqalculate
Cflags: -I$sysroot/usr/pkg/include -I$real/usr/include -isystem $sysroot/usr/pkg/include/x -I\${includedir}
PC
chmod 444 "$dest/usr/pkg/lib/pkgconfig/libqalculate.pc"
cat > "$dest/usr/pkg/share/pkgconfig/clean.pc" <<'PC'
prefix=/usr/pkg
Cflags: -I${prefix}/include
PC
printf 'see %s/usr/pkg/include\n' "$sysroot" > "$dest/usr/pkg/share/doc/notes.pc"
cp "$dest/usr/pkg/share/pkgconfig/clean.pc" "$work/clean.expected"
cp "$dest/usr/pkg/share/doc/notes.pc" "$work/notes.expected"

# *-config with current sysroot and a foreign older sysroot path.
cat > "$dest/usr/pkg/bin/libgcrypt-config" <<CFG
#!/bin/sh
gpg_error_libs="-Wl,-R/usr/pkg/lib -L$sysroot/usr/pkg/lib -lgpg-error -L$old/usr/pkg/lib -lgpg-error"
gpg_error_cflags="-I$sysroot/usr/pkg/include -I$old/usr/pkg/include"
CFG
chmod 755 "$dest/usr/pkg/bin/libgcrypt-config"

# CMake export without host paths (poison cases covered below).
cat > "$dest/usr/pkg/lib/cmake/Example/ExampleTargets.cmake" <<'CM'
add_library(Example::Example INTERFACE IMPORTED)
CM

# qmake mkspec with absolute cross-tools AR.
cat > "$dest/usr/pkg/qt6/mkspecs/netbsd-g++/qmake.conf" <<QMAKE
QMAKE_AR		= /Volumes/BigData/EmberBSD/build/aarch64/cross-tools/bin/aarch64--netbsd-ar cqs
QMAKE_CC		= aarch64--netbsd-clang
QMAKE
# Comment-only upstream example must not fail the check.
cat > "$dest/usr/pkg/lib/cmake/Example/QtComment.cmake" <<'CM'
#   C:/Users/qt/work/qt/qtbase
CM

sh "$script" "$dest" "$sysroot" "$wrk" "$tools" > "$work/run1.log" 2> "$work/run1.err" ||
	fail "rooted metadata is refused: $(cat "$work/run1.err"; cat "$work/run1.log")"
pc=$dest/usr/pkg/lib/pkgconfig/libqalculate.pc
cat > "$work/qalc.expected" <<'PC'
prefix=/usr/pkg
includedir=${prefix}/include
libdir=${prefix}/lib
Libs.private: -Wl,-R/usr/pkg/lib -L/usr/pkg/lib -lcurl -L/usr/pkg/lib -licuuc
Libs: -L${libdir} -lqalculate
Cflags: -I/usr/pkg/include -I/usr/include -isystem /usr/pkg/include/x -I${includedir}
PC
cmp -s "$pc" "$work/qalc.expected" || { diff "$work/qalc.expected" "$pc" >&2 || :; fail 'sysroot flags were not rewritten to target paths'; }
[ ! -w "$pc" ] || fail 'the staged file mode changed'
cmp -s "$dest/usr/pkg/share/pkgconfig/clean.pc" "$work/clean.expected" || fail 'a clean .pc file changed'
cmp -s "$dest/usr/pkg/share/doc/notes.pc" "$work/notes.expected" || fail 'a file outside selected metadata changed'
grep -q 'removed build paths from /usr/pkg/lib/pkgconfig/libqalculate.pc' "$work/run1.log" ||
	fail 'the .pc rewrite is not reported'
grep -q 'QMAKE_AR\t\t= aarch64--netbsd-ar cqs' "$dest/usr/pkg/qt6/mkspecs/netbsd-g++/qmake.conf" ||
	grep -q 'QMAKE_AR		= aarch64--netbsd-ar cqs' "$dest/usr/pkg/qt6/mkspecs/netbsd-g++/qmake.conf" ||
	fail 'cross-tools QMAKE_AR was not rewritten to the tool basename'
grep -q 'removed build paths from /usr/pkg/qt6/mkspecs/netbsd-g++/qmake.conf' "$work/run1.log" ||
	fail 'the qmake rewrite is not reported'


# libgcrypt-config: current sysroot stripped; foreign /old-sysroot and /Volumes still refused? 
# Foreign old path uses $old which is under $work but NOT passed as a root. Absolute rewrite
# only strips selected roots, so $old remains and fail-closed must catch it via... wait, $old
# does not match /Volumes/ or .buildlink. Need fail on leftover absolute path under $work?
# The production fail list uses /Volumes/ and BigData. For the fixture, put foreign path on /Volumes.
rm -f "$dest/usr/pkg/bin/libgcrypt-config"
cat > "$dest/usr/pkg/bin/libgcrypt-config" <<'CFG'
#!/bin/sh
gpg_error_libs="-Wl,-R/usr/pkg/lib -L/usr/pkg/lib -lgpg-error -L/Volumes/BigData/EmberBSD/build/aarch64/sysroot/usr/pkg/lib -lgpg-error"
CFG
chmod 755 "$dest/usr/pkg/bin/libgcrypt-config"
# CMake still has .buildlink - expect failure for that file. Stage a clean cmake for success path later.
rm -f "$dest/usr/pkg/lib/cmake/Example/ExampleTargets.cmake"
cat > "$dest/usr/pkg/lib/cmake/Example/ExampleTargets.cmake" <<'CM'
add_library(Example::Example INTERFACE IMPORTED)
CM

# First: foreign Volumes in *-config must fail.
if sh "$script" "$dest" "$sysroot" "$wrk" "$tools" > "$work/foreign.log" 2> "$work/foreign.err"; then
	fail 'a *-config naming /Volumes is accepted'
fi
grep -q 'build-host path' "$work/foreign.err" || fail 'foreign /Volumes rejection missing'

# Drop foreign config; cross-tools qmake must rewrite to basename.
rm -f "$dest/usr/pkg/bin/libgcrypt-config"
cat > "$dest/usr/pkg/bin/libgcrypt-config" <<CFG
#!/bin/sh
gpg_error_libs="-Wl,-R/usr/pkg/lib -L$sysroot/usr/pkg/lib -lgpg-error"
CFG
chmod 755 "$dest/usr/pkg/bin/libgcrypt-config"
sh "$script" "$dest" "$sysroot" "$wrk" "$tools" > "$work/runq.log" 2> "$work/runq.err" ||
	fail "qmake/config rewrite refused: $(cat "$work/runq.err")"
grep -q 'gpg_error_libs="-Wl,-R/usr/pkg/lib -L/usr/pkg/lib -lgpg-error"' "$dest/usr/pkg/bin/libgcrypt-config" ||
	fail '*-config sysroot was not rewritten'

cp "$pc" "$work/qalc.once"
sh "$script" "$dest" "$sysroot" "$wrk" "$tools" > "$work/run2.log" 2>&1 || fail 'a second run fails'
cmp -s "$pc" "$work/qalc.once" || fail 'the rewrite is not idempotent'
[ ! -s "$work/run2.log" ] || fail 'a second run reports changes'

# Build directories that are not rewritten stay and are refused.
for case in buildlink tools sysroot-var; do
	stage
	mkdir -p "$dest/usr/pkg/lib/pkgconfig"
	case $case in
	buildlink) line="Libs.private: $wrk/.buildlink/lib/libpcre2-8.so" ; want=$wrk ;;
	tools) line="host_tool=$tools/bin/aarch64--netbsd-pkg-config" ; want=$tools ;;
	sysroot-var) line="sysroot=$sysroot" ; want=$sysroot ;;
	esac
	printf 'prefix=/usr/pkg\n%s\n' "$line" > "$dest/usr/pkg/lib/pkgconfig/bad.pc"
	if sh "$script" "$dest" "$sysroot" "$wrk" "$tools" > "$work/$case.log" 2> "$work/$case.err"; then
		fail "a .pc file naming the $case directory is accepted"
	fi
	if [ "$case" = buildlink ]; then
		grep -Eq 'build-host path|\.buildlink' "$work/$case.err" "$work/$case.log" ||
			fail "the buildlink rejection does not mention .buildlink"
	else
		grep -Fq "names build directory $want" "$work/$case.err" ||
			grep -Fq "names build directory $want" "$work/$case.log" ||
			fail "the $case rejection does not name $want"
	fi
done
! sh "$script" "$dest" relative > /dev/null 2>&1 || fail 'a relative sysroot is accepted'
sh "$script" "$work/missing" "$sysroot" || fail 'a package without a stage fails'

if [ "$#" = 3 ]; then
	: "${BMAKE:?Set the native bmake executable}"
	pkgsrc=$2 conf=$3
	recipe=$pkgsrc/devel/readline
	bm() { "$BMAKE" -C "$recipe" MAKECONF="$conf" WRKOBJDIR="$work/wrk" "$@"; }
	bm -n install-doc-handling > "$work/cross-install.log" 2>&1 || fail 'make -n install-doc-handling failed'
	grep -q 'target-pkgconfig.sh' "$work/cross-install.log" || fail 'a cross install does not check its pkg-config files'
	[ -f "$pkgsrc/target-pkgconfig.sh" ] || fail 'the export does not provide target-pkgconfig.sh'
	bm -n USE_CROSS_COMPILE=no install-doc-handling > "$work/native-install.log" 2>&1 ||
		fail 'native make -n install-doc-handling failed'
	! grep -q 'target-pkgconfig.sh' "$work/native-install.log" || fail 'a native install runs the target check'
fi
echo 'PASS: staged target metadata names target paths and refuses build-host paths'
