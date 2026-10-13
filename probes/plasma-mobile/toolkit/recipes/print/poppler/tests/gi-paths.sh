#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), Poppler scanner selection and sysroot paths.
# Use real pkgsrc metadata and the original CMake GIR macro. The scanner
# fixture records argv/environment; it does not compile or execute target code.
set -eu
[ "$#" = 5 ] || {
    echo 'Usage: gi-paths.sh PKGSRC MAKECONF POPPLER_RECIPE POPPLER_SOURCE NEW_OUTPUT' >&2
    exit 2
}
: "${BMAKE:?Set native bmake}" "${CMAKE:?Set native CMake}"
pkgsrc=$1 conf=$2 recipe=$3 source=$4 out=$5
for item in "$@" "$BMAKE" "$CMAKE"; do
    case "$item" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
[ -f "$source/cmake/modules/GObjectIntrospectionMacros.cmake" ]
mkdir "$out"
make_recipe()
{
    "$BMAKE" -C "$pkgsrc/print/poppler" -f "$recipe/Makefile" \
        MAKECONF="$conf" WRKOBJDIR="$out/work" "$@"
}
field()
{
    sed -n "s/^$1=//p" "$2"
}
fail()
{
    echo "FAIL: $*" >&2
    exit 1
}
for mode in no yes; do
    make_recipe USE_CROSS_COMPILE="$mode" \
        -V 'FAIL=${PKG_FAIL_REASON}' -V 'ARGS=${CMAKE_CONFIGURE_ARGS}' \
        -V 'SUBST=${SUBST_CLASSES}' -V 'ENV=${MAKE_ENV}' \
        -V 'ROOT=${CROSS_DESTDIR}' -V 'WRKDIR=${WRKDIR}' \
        -V 'TOOLBASE=${TOOLBASE}' -V 'GI_FILES=${EMBERBSD_GI_FILESDIR}' \
        -V 'PKG_TOOLS=${NATIVE_PKG_TOOLS_BIN}' \
        -V 'DEPS=${DEPENDS} ${BUILD_DEPENDS} ${TOOL_DEPENDS}' > "$out/$mode.log"
    [ -z "$(field FAIL "$out/$mode.log")" ] || fail "$mode metadata rejected"
    args=" $(field ARGS "$out/$mode.log") "
    case "$args" in *' -DENABLE_GLIB=ON '*) ;; *) fail 'GLib feature removed' ;; esac
    case "$(field DEPS "$out/$mode.log")" in *:../../x11/gtk2*) fail 'GTK2 dependency added' ;; esac
    case "$(field DEPS "$out/$mode.log")" in *gobject-introspection*) ;; *) fail 'GI dependency removed' ;; esac
    if [ "$mode" = no ]; then
        case "$args" in *-DINTROSPECTION_SCANNER=*|*-DINTROSPECTION_COMPILER=*) fail 'native build uses cross scanner override' ;; esac
        case " $(field SUBST "$out/$mode.log") " in *' girpaths '*) fail 'native build rewrites target includes' ;; esac
        case "$(field ENV "$out/$mode.log")" in *GI_CROSS_LAUNCHER=*) fail 'native build uses target executor' ;; esac
        if make_recipe USE_CROSS_COMPILE=no -n poppler-gi-shim > "$out/native-shim.log" 2>&1; then
            fail 'native build creates a cross scanner shim'
        fi
    else
        case "$args" in *"-DINTROSPECTION_SCANNER=$(field WRKDIR "$out/$mode.log")/bin/g-ir-scanner"*) ;; *) fail 'cross scanner shim absent' ;; esac
        case "$(field ENV "$out/$mode.log")" in *GI_CROSS_LAUNCHER=*) ;; *) fail 'real target query executor lost' ;; esac
    fi
done

# Use a new sysroot alias with a regexp metacharacter. A similar path must
# remain unchanged, as must an unrelated host/source include directory.
ln -s "$(field ROOT "$out/yes.log")" "$out/sysroot.v1"
root=$out/sysroot.v1
real_root=$(CDPATH= cd -- "$root" && pwd -P)
mkdir -p "$out/tools/bin" "$out/shim" "$out/fixture/glib" "$out/host-include"
cat > "$out/tools/bin/g-ir-scanner" <<'SCANNER'
#!/bin/sh
set -eu
{
    printf 'CC=%s\nCXX=%s\nCONFIG=%s\n' "$CC" "$CXX" "$CWRAPPERS_CONFIG_DIR"
    printf 'ARG=%s\n' "$@"
} > "$POPPLER_TEST_LOG"
while [ "$#" -gt 0 ]; do
    if [ "$1" = --output ]; then shift; : > "$1"; exit 0; fi
    shift
done
exit 1
SCANNER
cat > "$out/tools/bin/g-ir-compiler" <<'COMPILER'
#!/bin/sh
set -eu
while [ "$#" -gt 0 ]; do
    if [ "$1" = -o ]; then shift; : > "$1"; exit 0; fi
    shift
done
exit 1
COMPILER
chmod +x "$out/tools/bin/g-ir-scanner" "$out/tools/bin/g-ir-compiler"
make_cross()
{
    make_recipe USE_CROSS_COMPILE=yes EMBERBSD_CROSS_SYSROOT="$root" \
        WRKDIR="$out/shim" WRKSRC="$out/fixture" \
        CMAKE_BUILD_DIR=gi-regression-build TOOLBASE="$out/tools" \
        PKG_TOOLS_BIN="$(field PKG_TOOLS "$out/yes.log")" \
        NATIVE_PKG_TOOLS_BIN="$(field PKG_TOOLS "$out/yes.log")" "$@"
}
make_cross poppler-gi-shim > "$out/shim.log"
sh -n "$out/shim/bin/g-ir-scanner"
make_cross -V 'CC=${_POPPLER_GI_CC}' -V 'CXX=${_POPPLER_GI_CXX}' \
    -V 'CONFIG=${CWRAPPERS_CONFIG_DIR}' -V 'FAIL=${PKG_FAIL_REASON}' > "$out/wrapper-expected.log"
[ -z "$(field FAIL "$out/wrapper-expected.log")" ] || fail 'scanner fixture metadata rejected'
cat > "$out/fixture/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.13)
project(PopplerGIRRule NONE)
set(CMAKE_INSTALL_DATADIR share)
set(CMAKE_INSTALL_LIBDIR lib)
include("$ENV{POPPLER_SOURCE}/cmake/modules/GObjectIntrospectionMacros.cmake")
add_subdirectory(glib)
CMAKE
cat > "$out/fixture/glib/CMakeLists.txt" <<'CMAKE'
set(INTROSPECTION_SCANNER "$ENV{POPPLER_OUT}/shim/bin/g-ir-scanner")
set(INTROSPECTION_COMPILER "$ENV{POPPLER_OUT}/tools/bin/g-ir-compiler")
set(INTROSPECTION_SCANNER_ARGS "--label=argument with spaces")
set(Poppler_0_18_gir_CFLAGS
    "-I$ENV{POPPLER_ROOT}/usr/pkg/include/glib-2.0"
    "-I$ENV{POPPLER_REAL_ROOT}/usr/include"
    "-I$ENV{POPPLER_OUT}/sysrootXv1/usr/pkg/include/keep"
    "-I$ENV{POPPLER_ROOT}-suffix/include/keep"
    "-I$ENV{POPPLER_OUT}/host-include")
set(girs Poppler-0.18.gir)
gir_add_introspections(girs)
CMAKE
POPPLER_SOURCE=$source POPPLER_OUT=$out POPPLER_ROOT=$root POPPLER_REAL_ROOT=$real_root
export POPPLER_SOURCE POPPLER_OUT POPPLER_ROOT POPPLER_REAL_ROOT
"$CMAKE" -S "$out/fixture" -B "$out/fixture/gi-regression-build" -G 'Unix Makefiles' > "$out/cmake.log" 2>&1
rule=$out/fixture/gi-regression-build/glib/CMakeFiles/gir-typelibs.dir/build.make
cp "$rule" "$out/rule-before.make"
make_cross subst-girpaths > "$out/subst.log"
cp "$rule" "$out/rule-after.make"
POPPLER_TEST_LOG=$out/scanner.log
export POPPLER_TEST_LOG
"$CMAKE" --build "$out/fixture/gi-regression-build" --target gir-typelibs --parallel 1 > "$out/rule-run.log" 2>&1
for key in CC CXX CONFIG; do
    [ "$(field "$key" "$out/scanner.log")" = "$(field "$key" "$out/wrapper-expected.log")" ] || fail "wrong wrapper $key"
done
for arg in --use-ldd-wrapper "$(field GI_FILES "$out/yes.log")/elf-needed.sh" \
    '--label=argument with spaces' -I/usr/pkg/include/glib-2.0 -I/usr/include \
    "-I$out/sysrootXv1/usr/pkg/include/keep" "-I$root-suffix/include/keep" "-I$out/host-include"; do
    grep -Fqx -- "ARG=$arg" "$out/scanner.log" || fail "scanner argument missing: $arg"
done
if grep -Fq -- "ARG=-I$root/usr/" "$out/scanner.log" || grep -Fq -- "ARG=-I$real_root/usr/" "$out/scanner.log"; then
    fail 'sysroot prefix remains in scanner includes'
fi
echo 'PASS: native GI discovery, cross wrappers, literal sysroot aliases and generated scanner rule'
echo 'No Poppler package was built; no target code or real GType query was executed.'
