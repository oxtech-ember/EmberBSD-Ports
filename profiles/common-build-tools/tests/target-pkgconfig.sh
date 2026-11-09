#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Fixture regression for staged target metadata
# sanitization: sysroot rewrite (longest-first), foreign /sysroot/ refusal,
# cross-tools normalization, token-safe .buildlink CMake mapping, Python
# sysconfig via host python, --sysroot= without trailing slash, binary
# *-config skip, and install hook wiring.
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
mkdir -p "$work/real-sysroot/usr/pkg/include" "$work/context" \
	"$work/obj/work/.buildlink/lib" "$work/tools/bin" \
	"$work/host-sdk/bin" \
	"$work/foreign/build/aarch64/sysroot/usr/pkg/lib"
ln -s "$work/real-sysroot" "$work/context/sysroot"
sysroot=$work/context/sysroot
real=$work/real-sysroot
wrk=$work/obj/work
tools=$work/tools
hostsdk=$work/host-sdk
foreign=$work/foreign/build/aarch64/sysroot

stage() {
	rm -rf "$work/stage"
	mkdir -p "$work/stage/usr/pkg/lib/pkgconfig" "$work/stage/usr/pkg/share/pkgconfig" \
		"$work/stage/usr/pkg/share/doc" "$work/stage/usr/pkg/bin" \
		"$work/stage/usr/pkg/lib/cmake/Example" \
		"$work/stage/usr/pkg/qt6/mkspecs/netbsd-g++" \
		"$work/stage/usr/pkg/lib/python3.15"
	dest=$work/stage
}

run_hook() {
	sh "$script" "$dest" "$sysroot" "$wrk" "$tools" "$hostsdk" "$@"
}

# --- /private substring must not eat a longer /private/tmp/... sysroot ---
stage
cat > "$dest/usr/pkg/lib/pkgconfig/sub.pc" <<PC
Cflags: -I$sysroot/usr/pkg/include
Libs: -L$sysroot/usr/pkg/lib -lx
PC
run_hook > "$work/sub.log" 2> "$work/sub.err" ||
	fail "substring probe refused: $(cat "$work/sub.err")"
grep -q 'Cflags: -I/usr/pkg/include' "$dest/usr/pkg/lib/pkgconfig/sub.pc" || fail 'sysroot Cflags not rewritten'
grep -q 'Libs: -L/usr/pkg/lib -lx' "$dest/usr/pkg/lib/pkgconfig/sub.pc" || fail 'sysroot Libs not rewritten'
! grep -q '/private/usr/pkg' "$dest/usr/pkg/lib/pkgconfig/sub.pc" || fail 'shorter /private alias ate the sysroot path'

# --- main rewrite suite ---
stage
cat > "$dest/usr/pkg/lib/pkgconfig/libqalculate.pc" <<PC
prefix=/usr/pkg
Libs.private: -Wl,-R/usr/pkg/lib -L$sysroot/usr/pkg/lib -lcurl -L$real/usr/pkg/lib -licuuc
Cflags: -I$sysroot/usr/pkg/include -isystem $sysroot/usr/pkg/include/x -I\${includedir}
Description: uses a path-like word without embedding a host root
PC
chmod 444 "$dest/usr/pkg/lib/pkgconfig/libqalculate.pc"
cat > "$dest/usr/pkg/share/pkgconfig/clean.pc" <<'PC'
prefix=/usr/pkg
Cflags: -I${prefix}/include
PC
printf 'see %s/usr/pkg/include\n' "$sysroot" > "$dest/usr/pkg/share/doc/notes.pc"
cp "$dest/usr/pkg/share/pkgconfig/clean.pc" "$work/clean.expected"
cp "$dest/usr/pkg/share/doc/notes.pc" "$work/notes.expected"

# ICU-style double-slash cross-tools path in *-config
cat > "$dest/usr/pkg/bin/icu-config" <<CFG
#!/bin/sh
AR="/opt/cross/build/aarch64/cross-tools/bin//usr/bin/ar"
CC="aarch64--netbsd-clang --sysroot=$sysroot"
CFG
chmod 755 "$dest/usr/pkg/bin/icu-config"

# Python sysconfig with abs_srcdir and host paths (helper uses host python)
cat > "$dest/usr/pkg/lib/python3.15/_sysconfigdata_netbsd11.py" <<PY
build_time_vars = {
  'AR': '/opt/cross/build/aarch64/cross-tools/bin/aarch64--netbsd-ar',
  'abs_srcdir': '$wrk/Python-3.15.2',
  'abs_builddir': '$wrk/Python-3.15.2',
  'srcdir': '$wrk/Python-3.15.2',
  'RUNSHARED': 'LD_LIBRARY_PATH=$wrk/Python-3.15.2',
  'CONFIG_ARGS': "'--with-build-python=$hostsdk/bin/python3.15' 'PKG_CONFIG_LIBDIR=$wrk/.buildlink/lib/pkgconfig'",
  'LN': '$hostsdk/bin/gln',
  'CC': 'aarch64--netbsd-clang --sysroot=$sysroot',
  'CFLAGS': '-I$sysroot/usr/pkg/include',
}
PY
cat > "$dest/usr/pkg/lib/python3.15/_sysconfig_vars_netbsd11.json" <<JSON
{"abs_srcdir": "$wrk/Python-3.15.2", "AR": "/opt/cross/build/aarch64/cross-tools/bin/ar", "CC": "clang --sysroot=$sysroot"}
JSON

# CMake .buildlink forms: quoted, unquoted if(...), and ;-separated list
cat > "$dest/usr/pkg/lib/cmake/Example/ExampleTargets.cmake" <<CM
set_target_properties(Example::Example PROPERTIES
  INTERFACE_LINK_LIBRARIES "$wrk/.buildlink/lib/libpcre2-8.so")
if($wrk/.buildlink/lib/libinotify.so)
  message(STATUS "has inotify")
endif()
set(Example_LIBS "$wrk/.buildlink/lib/liba.so;$wrk/.buildlink/lib/libb.so")
CM

# qmake cross-tools
cat > "$dest/usr/pkg/qt6/mkspecs/netbsd-g++/qmake.conf" <<QMAKE
QMAKE_AR		= /opt/cross/build/aarch64/cross-tools/bin/aarch64--netbsd-ar cqs
QMAKE
# Comment-only upstream example path must not fail.
cat > "$dest/usr/pkg/lib/cmake/Example/QtComment.cmake" <<'CM'
#   C:/Users/qt/work/qt/qtbase
CM

# Binary *-config must be skipped (ELF magic), not rewritten.
printf '\177ELF\000\001\002\003binary-config-payload' > "$dest/usr/pkg/bin/blob-config"
chmod 755 "$dest/usr/pkg/bin/blob-config"
cp "$dest/usr/pkg/bin/blob-config" "$work/blob.expected"

run_hook > "$work/run1.log" 2> "$work/run1.err" ||
	fail "suite refused: $(cat "$work/run1.err"; cat "$work/run1.log")"

pc=$dest/usr/pkg/lib/pkgconfig/libqalculate.pc
grep -q 'Libs.private: -Wl,-R/usr/pkg/lib -L/usr/pkg/lib -lcurl -L/usr/pkg/lib -licuuc' "$pc" || fail '.pc Libs.private not rewritten'
grep -q 'Cflags: -I/usr/pkg/include -isystem /usr/pkg/include/x' "$pc" || fail '.pc Cflags not rewritten'
[ ! -w "$pc" ] || fail 'staged .pc mode changed'
cmp -s "$dest/usr/pkg/share/pkgconfig/clean.pc" "$work/clean.expected" || fail 'clean .pc changed'
cmp -s "$dest/usr/pkg/share/doc/notes.pc" "$work/notes.expected" || fail 'non-metadata file changed'
grep -q 'removed build paths from /usr/pkg/lib/pkgconfig/libqalculate.pc' "$work/run1.log" || fail '.pc rewrite not reported'

grep -q 'AR="ar"' "$dest/usr/pkg/bin/icu-config" || {
	echo "icu-config became: $(cat "$dest/usr/pkg/bin/icu-config")" >&2
	fail 'ICU double-slash cross-tools path not normalized to ar'
}
grep -q 'CC="aarch64--netbsd-clang"' "$dest/usr/pkg/bin/icu-config" || {
	echo "icu-config became: $(cat "$dest/usr/pkg/bin/icu-config")" >&2
	fail '--sysroot=<selected> without trailing slash not stripped from CC'
}

cm=$dest/usr/pkg/lib/cmake/Example/ExampleTargets.cmake
grep -q 'INTERFACE_LINK_LIBRARIES "/usr/pkg/lib/libpcre2-8.so"' "$cm" || fail 'quoted buildlink CMake not mapped'
grep -q 'if(/usr/pkg/lib/libinotify.so)' "$cm" || {
	echo "cmake became: $(cat "$cm")" >&2
	fail 'unquoted if(buildlink) not mapped to if(/usr/pkg/lib/...)'
}
! grep -q 'if(/usr/pkg/lib/libinotify.so))' "$cm" || fail 'buildlink rewrite ate a parenthesis'
grep -q 'set(Example_LIBS "/usr/pkg/lib/liba.so;/usr/pkg/lib/libb.so")' "$cm" || {
	echo "cmake became: $(cat "$cm")" >&2
	fail 'semicolon-separated buildlink list not mapped'
}

grep -q 'QMAKE_AR		= aarch64--netbsd-ar cqs' \
	"$dest/usr/pkg/qt6/mkspecs/netbsd-g++/qmake.conf" || fail 'qmake cross-tools AR not rewritten'

py=$dest/usr/pkg/lib/python3.15/_sysconfigdata_netbsd11.py
python3 -c "import ast,pathlib; t=pathlib.Path(r'''$py''').read_text(); i=t.index('{'); d=ast.literal_eval(t[t.index('=')+1:].strip()); assert d['abs_srcdir']==''; assert d['AR']=='aarch64--netbsd-ar'; assert '--sysroot' not in d.get('CC',''); assert d['LN']=='gln'; assert '$wrk' not in str(d)" || {
	echo "python sysconfig became: $(cat "$py")" >&2
	fail 'python sysconfig not neutralized/reparsed'
}
python3 -c "import json,pathlib; d=json.loads(pathlib.Path(r'''$dest/usr/pkg/lib/python3.15/_sysconfig_vars_netbsd11.json''').read_text()); assert d['abs_srcdir']==''; assert d['AR']=='ar'; assert '--sysroot' not in d.get('CC','')" || fail 'python json sysconfig not neutralized'

grep -q 'skipping binary file /usr/pkg/bin/blob-config' "$work/run1.log" || fail 'binary *-config not skipped'
cmp -s "$dest/usr/pkg/bin/blob-config" "$work/blob.expected" || fail 'binary *-config was corrupted'

# Idempotent second run
cp "$pc" "$work/qalc.once"
run_hook > "$work/run2.log" 2>&1 || fail 'second run fails'
cmp -s "$pc" "$work/qalc.once" || fail 'rewrite not idempotent'

# Android NDK template path must not trip /sysroot/ detection.
stage
mkdir -p "$dest/usr/pkg/share/ECM/toolchain"
cat > "$dest/usr/pkg/share/ECM/toolchain/Android.cmake" <<'CM'
set(ANDROID_SYSROOT_PREFIX "${CMAKE_NDK_ROOT}/toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr")
CM
run_hook > "$work/android.log" 2> "$work/android.err" ||
	fail "Android NDK template refused: $(cat "$work/android.err")"
grep -q 'linux-x86_64/sysroot/usr' "$dest/usr/pkg/share/ECM/toolchain/Android.cmake" ||
	fail 'Android NDK template was rewritten'

# Foreign sysroot outside /Volumes (e.g. /home/builder/...) must fail closed.
stage
mkdir -p "$dest/usr/pkg/lib/pkgconfig"
printf 'prefix=/usr/pkg\nLibs.private: -L%s/usr/pkg/lib -lgpg-error\n' "$foreign" \
	> "$dest/usr/pkg/lib/pkgconfig/bad-foreign.pc"
if run_hook > "$work/foreign.log" 2> "$work/foreign.err"; then
	fail 'a .pc naming a foreign /sysroot/ path is accepted'
fi
grep -q 'build-host path\|names build directory\|/sysroot/' "$work/foreign.err" ||
	fail 'foreign sysroot rejection missing'

# --sysroot=<foreign> without trailing slash must be refused.
stage
mkdir -p "$dest/usr/pkg/bin"
printf '#!/bin/sh\nCC="clang --sysroot=%s"\n' "$foreign" > "$dest/usr/pkg/bin/bad-sysroot-config"
chmod 755 "$dest/usr/pkg/bin/bad-sysroot-config"
if run_hook > "$work/sysrootflag.log" 2> "$work/sysrootflag.err"; then
	fail 'a *-config with --sysroot=<foreign> is accepted'
fi
grep -Eq 'build-host path|names build directory|--sysroot|/sysroot/' "$work/sysrootflag.err" ||
	fail 'foreign --sysroot= rejection missing'

# WRKOBJDIR/work path that is not rewritten must be refused.
stage
mkdir -p "$dest/usr/pkg/lib/pkgconfig"
printf 'prefix=/usr/pkg\nhost_tool=%s/bin/foo\n' "$wrk" > "$dest/usr/pkg/lib/pkgconfig/bad-wrk.pc"
if run_hook > "$work/wrk.log" 2> "$work/wrk.err"; then
	fail 'a .pc naming WRKDIR is accepted'
fi
grep -Fq "names build directory $wrk" "$work/wrk.err" ||
	grep -Fq "names build directory $wrk" "$work/wrk.log" ||
	fail 'WRKDIR rejection missing'

# Selected roots that are not flag-rewritable stay refused.
for case in buildlink tools sysroot-var; do
	stage
	mkdir -p "$dest/usr/pkg/lib/pkgconfig"
	case $case in
	buildlink) line="host_tool=$wrk/.buildlink/bin/foo" ; want=$wrk ;;
	tools) line="host_tool=$tools/bin/aarch64--netbsd-pkg-config" ; want=$tools ;;
	sysroot-var) line="sysroot=$sysroot" ; want=$sysroot ;;
	esac
	printf 'prefix=/usr/pkg\n%s\n' "$line" > "$dest/usr/pkg/lib/pkgconfig/bad.pc"
	if run_hook > "$work/$case.log" 2> "$work/$case.err"; then
		fail "a .pc file naming the $case directory is accepted"
	fi
	grep -Fq "names build directory $want" "$work/$case.err" ||
		grep -Fq "names build directory $want" "$work/$case.log" ||
		grep -Eq 'build-host path|\\.buildlink|/sysroot/' "$work/$case.err" ||
		fail "the $case rejection is missing"
done
! sh "$script" "$dest" relative > /dev/null 2>&1 || fail 'a relative sysroot is accepted'
sh "$script" "$work/missing" "$sysroot" || fail 'a package without a stage fails'

if [ "$#" = 3 ]; then
	: "${BMAKE:?Set the native bmake executable}"
	pkgsrc=$2 conf=$3
	recipe=$pkgsrc/devel/readline
	bm() { "$BMAKE" -C "$recipe" MAKECONF="$conf" WRKOBJDIR="$work/wrk" "$@"; }
	bm -n install-doc-handling > "$work/cross-install.log" 2>&1 || fail 'make -n install-doc-handling failed'
	grep -q 'target-pkgconfig.sh' "$work/cross-install.log" || fail 'a cross install does not check metadata'
	[ -f "$pkgsrc/target-pkgconfig.sh" ] || fail 'the export does not provide target-pkgconfig.sh'
	bm -n USE_CROSS_COMPILE=no install-doc-handling > "$work/native-install.log" 2>&1 ||
		fail 'native make -n install-doc-handling failed'
	! grep -q 'target-pkgconfig.sh' "$work/native-install.log" || fail 'a native install runs the target check'
fi
echo 'PASS: staged target metadata names target paths and refuses build-host paths'
