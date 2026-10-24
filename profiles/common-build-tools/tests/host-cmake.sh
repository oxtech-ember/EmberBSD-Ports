#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), verified external CMake for host generators.
set -eu
[ "$#" = 5 ] || { echo "Usage: $0 PKGSRC CROSS_MAKECONF NATIVE_MAKECONF HOST_CMAKE NEW_WORK" >&2; exit 2; }
pkgsrc=$1 crossconf=$2 nativeconf=$3 cmake=$4 work=$5
bmake=${BMAKE:-bmake}
. "$(CDPATH= cd -- "$(dirname -- "$0")/../cross" && pwd)/host-gcc16.sh"
ember_require_host_gcc16 HOST_CC c
ember_require_host_gcc16 HOST_CXX c++
mkdir "$work"
for mode in native cross; do
    case "$mode" in native) conf=$nativeconf;; cross) conf=$crossconf;; esac
    cat > "$work/$mode.mk.conf" <<EOF
.include "$conf"
.undef EMBERBSD_BUILD_CMAKE
.undef TOOLS_PLATFORM.cmake
.undef TOOLS_PLATFORM.cpack
EOF
    "$bmake" -C "$pkgsrc/devel/re2c" MAKECONF="$work/$mode.mk.conf" \
        -v TOOL_DEPENDS > "$work/$mode-default.txt"
    grep -q ':../../devel/cmake' "$work/$mode-default.txt"
    "$bmake" -C "$pkgsrc/devel/re2c" MAKECONF="$work/$mode.mk.conf" \
        EMBERBSD_BUILD_CMAKE="$cmake" -v PKG_FAIL_REASON \
        -v TOOLS_PATH.cmake -v TOOL_DEPENDS > "$work/$mode-selected.txt"
    grep -Fxq "$cmake" "$work/$mode-selected.txt"
    if grep -E ':../../devel/cmake|EMBERBSD_BUILD_CMAKE must' "$work/$mode-selected.txt"; then
        echo 'Host CMake was not selected without a redundant package dependency' >&2; exit 1
    fi
# Qt uses USE_TOOLS directly, without including devel/cmake/build.mk.
"$bmake" -C "$pkgsrc/x11/qt6-qtbase" MAKECONF="$work/$mode.mk.conf" \
    EMBERBSD_BUILD_CMAKE="$cmake" -v TOOLS_PATH.cmake -v TOOL_DEPENDS \
    > "$work/$mode-qt-tools.txt"
grep -Fxq "$cmake" "$work/$mode-qt-tools.txt"
if grep -q ':../../devel/cmake' "$work/$mode-qt-tools.txt"; then
    echo 'Qt selected a redundant native CMake package' >&2; exit 1
fi
done
cat > "$work/old-cmake" <<'SH'
#!/bin/sh
echo 'cmake version 4.4.3'
SH
cat > "$work/broken-cmake" <<'SH'
#!/bin/sh
echo 'cmake version 4.4.4'
exit 1
SH
cp "$work/old-cmake" "$work/nonexecutable"
chmod +x "$work/old-cmake" "$work/broken-cmake"
for invalid in cmake /nonexistent/ember-cmake "$work/old-cmake" "$work/broken-cmake" "$work/nonexecutable"; do
    "$bmake" -C "$pkgsrc/devel/re2c" MAKECONF="$work/native.mk.conf" \
        EMBERBSD_BUILD_CMAKE="$invalid" -v PKG_FAIL_REASON > "$work/invalid.txt"
    grep -q 'EMBERBSD_BUILD_CMAKE must' "$work/invalid.txt"
done
"$bmake" -C "$pkgsrc/devel/re2c" MAKECONF="$work/native.mk.conf" \
    EMBERBSD_BUILD_CMAKE="$cmake" CMAKE_REQD='3.20 99.0' \
    -v PKG_FAIL_REASON > "$work/required-version.txt"
grep -q 'CMake >=99.0' "$work/required-version.txt"
mkdir "$work/companion"
cat > "$work/companion/cmake" <<'SH'
#!/bin/sh
echo 'cmake version 4.4.4'
SH
chmod +x "$work/companion/cmake"
for companion in missing mismatch failure; do
    case "$companion" in
    missing) ;;
    mismatch) printf '#!/bin/sh\necho "cpack version 4.4.3"\n' > "$work/companion/cpack";;
    failure) printf '#!/bin/sh\necho "cpack version 4.4.4"\nexit 1\n' > "$work/companion/cpack";;
    esac
    [ ! -f "$work/companion/cpack" ] || chmod +x "$work/companion/cpack"
    "$bmake" -C "$pkgsrc/devel/re2c" MAKECONF="$work/native.mk.conf" \
        EMBERBSD_BUILD_CMAKE="$work/companion/cmake" \
        -v PKG_FAIL_REASON > "$work/companion-$companion.txt"
    grep -q 'requires matching executable CPack' "$work/companion-$companion.txt"
done

mkdir "$work/source"
cat > "$work/source/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 4.4)
project(ember_host_cmake LANGUAGES C CXX)
enable_testing()
add_library(probe STATIC value.c)
add_executable(consumer main.cc)
target_link_libraries(consumer PRIVATE probe)
add_test(NAME host-consumer COMMAND consumer)
install(TARGETS consumer RUNTIME DESTINATION bin)
CMAKE
cat > "$work/source/value.c" <<'C'
int value(void) { return 42; }
C
cat > "$work/source/main.cc" <<'CXX'
extern "C" int value(void);
int main() { return value() != 42; }
CXX
"$cmake" -S "$work/source" -B "$work/build" -G 'Unix Makefiles' \
    -DCMAKE_C_COMPILER="$HOST_CC" \
    -DCMAKE_CXX_COMPILER="$HOST_CXX" \
    -DCMAKE_INSTALL_PREFIX="$work/prefix"
"$cmake" --build "$work/build" -j2
"$cmake" --build "$work/build" --target test
"$cmake" --install "$work/build"
"$work/prefix/bin/consumer"
echo 'PASS: native/cross CMake override, unchanged defaults, version/failure guards and installed host C/C++ consumer'
