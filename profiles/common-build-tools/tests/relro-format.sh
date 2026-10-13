#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the real RELRO backend and error gate.
set -eu
[ "$#" -eq 3 ] || {
    echo "Usage: $0 PKGSRC CHECK_RELRO_MK NEW_OUTPUT" >&2
    exit 2
}
: "${BMAKE:?Set native bmake}" "${CHECK_AWK:?Set native awk}"
: "${CROSS_AS:?Set the AArch64 ELF assembler}" "${CROSS_LD:?Set the ELF linker}"
: "${READELF:?Set an ELF readelf executable}"
pkgsrc=$1 fragment=$2 out=$3
for path in "$@" "$BMAKE" "$CHECK_AWK" "$CROSS_AS" "$CROSS_LD" "$READELF"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use portable path characters' >&2; exit 2 ;; esac
done
mkdir "$out"
fail() { echo "FAIL: $*" >&2; exit 1; }
cat > "$out/fixture.mk" <<'MAKE'
WRKDIR= ${CASE}/work
DESTDIR= ${CASE}/dest
PREFIX= /usr/pkg
PLIST= ${CASE}/PLIST
PKGNAME= relro-format-test
PKG_DEVELOPER= yes
_PKGSRC_USE_RELRO= partial
_USE_CHECK_RELRO_NATIVE= yes
CHECK_RELRO= yes
CHECK_RELRO_SUPPORTED= yes
CHECK_RELRO_SKIP=
RUN= @set -e;
MKDIR= mkdir -p
RM= rm
ECHO= echo
TEST= test
CAT= cat
MV= mv
SED= sed
EGREP= grep -E
AWK= ${CHECK_AWK}
TOOLS_PATH.readelf= ${READELF}
PKGSRC_SETENV= env
STEP_MSG= echo
WARNING_CAT= sed -e 's|^|WARNING: |' 1>&2
ERROR_CAT= sed -e 's|^|ERROR: |' 1>&2
_NONZERO_FILESIZE_P= ${AWK} 'END { exit (NR > 0) ? 0 : 1; }'
.include "${PKGSRCDIR}/mk/bsd.pkg.error.mk"
.include "${CHECK_FRAGMENT}"
.if target(_check-relro)
SELECTED= yes
.else
SELECTED= no
.endif
.PHONY: privileged-install-hook
privileged-install-hook:
	@true
MAKE
run_check() {
    "$BMAKE" -r -f "$out/fixture.mk" PKGSRCDIR="$pkgsrc" \
        CHECK_FRAGMENT="$fragment" CASE="$case_dir" OBJECT_FMT="$format" \
        CHECK_AWK="$CHECK_AWK" READELF="$READELF" "$@"
}
prepare() {
    case_dir=$out/$1
    mkdir -p "$case_dir/work" "$case_dir/dest/usr/pkg/bin" "$case_dir/dest/usr/pkg/lib"
    printf 'bin/script\n' > "$case_dir/PLIST"
    printf '#!/bin/sh\nexit 0\n' > "$case_dir/dest/usr/pkg/bin/script"
    run_check makedirs > "$case_dir/makedirs.log" 2>&1
}
# The native cross-tool package contains host scripts. A target-flavoured
# OPSYS must not cause an ELF-only backend to run without an AWK program.
format=Mach-O
prepare native-scripts
if ! run_check privileged-install-hook > "$case_dir/check.log" 2>&1; then
    cat "$case_dir/check.log" >&2
    fail 'native cross-tool package invoked an unavailable RELRO backend'
fi
[ "$(run_check -V SELECTED)" = no ] || fail 'RELRO backend selected for Mach-O'
[ "$(run_check -V CHECK_RELRO)" = yes ] || fail 'RELRO policy changed'
[ ! -e "$case_dir/work/.error/_check-relro" ] || fail 'non-ELF backend executed'

# Assemble data that needs dynamic relocation. Both outputs are actual ELF
# shared objects. No C implementation or target executable is introduced.
cat > "$out/probe.s" <<'ASM'
.text
.globl relro_probe
.type relro_probe, %function
relro_probe:
    ret
.section .data.rel.ro,"aw"
.quad relro_probe
ASM
"$CROSS_AS" -o "$out/probe.o" "$out/probe.s"
for mode in relro norelro; do
    "$CROSS_LD" -shared -z "$mode" -o "$out/lib$mode.so" "$out/probe.o"
    "$READELF" -Wl "$out/lib$mode.so" > "$out/$mode-headers.log"
    grep -q 'DYNAMIC' "$out/$mode-headers.log" || fail 'fixture lacks dynamic headers'
done
grep -q 'GNU_RELRO' "$out/relro-headers.log" || fail 'positive fixture lacks RELRO'
if grep -q 'GNU_RELRO' "$out/norelro-headers.log"; then fail 'negative fixture has RELRO'; fi
format=ELF
for mode in relro norelro; do
    prepare "$mode"
    cp "$out/lib$mode.so" "$case_dir/dest/usr/pkg/lib/libprobe.so"
    printf 'lib/libprobe.so\n' >> "$case_dir/PLIST"
    [ "$(run_check -V SELECTED)" = yes ] || fail 'ELF checker not selected'
    if run_check privileged-install-hook > "$case_dir/check.log" 2>&1; then
        [ "$mode" = relro ] || fail 'ELF without RELRO passed'
    else
        [ "$mode" = norelro ] || { cat "$case_dir/check.log" >&2; fail 'ELF with RELRO failed'; }
        grep -F 'lib/libprobe.so: missing RELRO' "$case_dir/check.log" >/dev/null
    fi
done
echo 'PASS: native cross-tool format selects no unavailable backend; policy stays enabled'
echo 'PASS: real ELF RELRO accepted; missing RELRO rejected by the pkgsrc error gate'
echo 'No package was installed. No target program was executed.'
