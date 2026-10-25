#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted GCC metadata and supported Clang config contracts.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 CONFIG_GENERATOR NEW_WORK" >&2; exit 2; }
generator=$1
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd -P)
prefix=$work/gcc16
mkdir -p "$prefix/bin" "$prefix/lib/gcc/aarch64--netbsd/16.2.0" \
    "$prefix/lib" "$prefix/include/c++/16.2.0/aarch64--netbsd" "$prefix/include/c++/16.2.0/backward"
mkdir -p "$work/build/bin" "$work/build/lib"
private=$prefix/lib/gcc/aarch64--netbsd/16.2.0
for file in crtbegin.o crtbeginS.o crtend.o crtendS.o libgcc.a; do : > "$private/$file"; done
for file in libgcc_s.so.1 libstdc++.so; do : > "$prefix/lib/$file"; done
cat > "$prefix/bin/gcc" <<'GCC'
#!/bin/sh
set -eu
prefix=${0%/bin/gcc}
case "$1" in
    -dumpfullversion) echo "${MOCK_VERSION:-16.2.0}" ;;
    -dumpmachine) echo aarch64--netbsd ;;
    -print-file-name=*)
        name=${1#*=}
        case "$name" in libgcc_s.so.1|libstdc++.so) echo "$prefix/lib/$name" ;;
            *) echo "$prefix/lib/gcc/aarch64--netbsd/16.2.0/$name" ;; esac ;;
    -E)
        echo '#include <...> search starts here:'
        for path in '' aarch64--netbsd backward; do echo " $prefix/include/c++/16.2.0${path:+/$path}"; done
        [ "${MOCK_DUPLICATE:-0}" = 0 ] || echo " $prefix/include/c++/16.2.0/backward"
        echo 'End of search list.'
        exit "${MOCK_PREPROCESS_STATUS:-0}" ;;
    *) exit 2 ;;
esac
GCC
cat > "$work/build/bin/clang-metadata" <<'CLANG'
#!/bin/sh
if [ -n "${MOCK_EXPECT_LIBRARY:-}" ]; then
    case ":${LD_LIBRARY_PATH-}:" in *":$MOCK_EXPECT_LIBRARY:"*) ;; *) exit 9 ;; esac
fi
if [ -n "${MOCK_EXPECT_PREVIOUS:-}" ]; then
    case ":${LD_LIBRARY_PATH-}:" in *":$MOCK_EXPECT_PREVIOUS:"*) ;; *) exit 9 ;; esac
fi
case "$*" in *--target=*) echo aarch64-unknown-netbsd; exit ;; esac
echo "${MOCK_TRIPLE:-aarch64-unknown-netbsd}"
CLANG
chmod +x "$prefix/bin/gcc" "$work/build/bin/clang-metadata"
sh "$generator" "$prefix/bin/gcc" "$work/build/bin/clang-metadata" "$prefix" "$work/config"
grep -Fqx -- "-B$private/" "$work/config/aarch64-unknown-netbsd.cfg"
grep -Fqx -- "\$-Wl,-rpath,$prefix/lib" "$work/config/aarch64-unknown-netbsd.cfg"
[ "$(grep -c '^-stdlib++-isystem' "$work/config/aarch64-unknown-netbsd.cfg")" = 3 ]
MOCK_EXPECT_LIBRARY="$work/build/lib" MOCK_EXPECT_PREVIOUS="$work/previous" \
    LD_LIBRARY_PATH="$work/previous" sh "$generator" "$prefix/bin/gcc" \
    "$work/build/bin/clang-metadata" "$prefix" "$work/ld-path-config"
echo 'PASS: native Clang build library precedes existing LD_LIBRARY_PATH'
reject() {
    name=$1; shift
    if env "$@" sh "$generator" "$prefix/bin/gcc" "$work/build/bin/clang-metadata" "$prefix" \
        "$work/$name" > "$work/$name.log" 2>&1; then echo "FAIL: accepted $name" >&2; exit 1; fi
    [ ! -e "$work/$name" ]
    echo "PASS: rejected $name"
}
reject version MOCK_VERSION=12.5.0
reject duplicate MOCK_DUPLICATE=1
reject failed-preprocess MOCK_PREPROCESS_STATUS=1
reject foreign MOCK_TRIPLE=aarch64-unknown-linux-gnu
reject different-abi MOCK_TRIPLE=aarch64-unknown-netbsd-eabi
mv "$private/crtendS.o" "$work/crtendS.o"
reject missing-crt
mv "$work/crtendS.o" "$private/crtendS.o"
mv "$prefix/lib/libgcc_s.so.1" "$work/libgcc_s.so.1"
ln -s "$work/libgcc_s.so.1" "$prefix/lib/libgcc_s.so.1"
reject escaped-runtime
rm "$prefix/lib/libgcc_s.so.1"
mv "$work/libgcc_s.so.1" "$prefix/lib/libgcc_s.so.1"
if sh "$generator" "$prefix/bin/gcc" "$work/build/bin/clang-metadata" "$prefix" "$work/config" \
    > "$work/existing.log" 2>&1; then exit 1; fi
echo 'PASS: GCC metadata contracts (fixture metadata, not real GCC execution)'
clang=${CLANG:-clang}
if ! command -v "$clang" >/dev/null 2>&1; then
    echo 'SKIP: executable Clang driver config contracts; native gate required'; exit 0
fi
# Execute the available real driver with its native-host version recorded.
# -### emits commands; dummy CRT files are never assembled or linked.
"$clang" --version > "$work/driver-version.txt"
printf 'int main(void) { return 0; }\n' > "$work/input.c"
printf 'int main() { return 0; }\n' > "$work/input.cc"
for language in c c++; do
    case "$language" in c) mode=gcc ;; c++) mode=g++ ;; esac
    "$clang" --target=aarch64-unknown-netbsd --driver-mode="$mode" \
        --config-system-dir="$work/config" --config-user-dir= -### \
        -x "$language" "$work/input.c" > "$work/$language.trace" 2>&1
    grep -Fq "$private/crtbegin.o" "$work/$language.trace"
    grep -Fq -- "\"-L$prefix/lib\"" "$work/$language.trace"
    # The prefix must precede the driver's default library search path.
    sed "s@\"-L$prefix/lib\"@CURRENT@;s@\"-L/usr/lib\"@BASE@" \
        "$work/$language.trace" | grep -q 'CURRENT.*BASE'
done
! grep -Fq "$prefix/include/c++" "$work/c.trace"
! grep -q '"-lstdc++"' "$work/c.trace"
grep -Fq "$prefix/include/c++/16.2.0" "$work/c++.trace"
grep -q '"-lstdc++"' "$work/c++.trace"
for args in '--target=aarch64-unknown-linux-gnu' \
    '--target=aarch64-unknown-netbsd --sysroot=/sdk --no-default-config'; do
    # Fixed named argument sets contain no shell expansions.
    "$clang" $args --config-system-dir="$work/config" --config-user-dir= -### \
        "$work/input.cc" > "$work/cross.trace" 2>&1
    ! grep -Fq "$prefix" "$work/cross.trace"
done
"$clang" --target=aarch64-unknown-netbsd --driver-mode=g++ \
    --config-system-dir="$work/config" --config-user-dir= -nostdinc++ -nostdlib -### \
    "$work/input.cc" > "$work/optouts.trace" 2>&1
! grep -Fq "$prefix/include/c++" "$work/optouts.trace"
! grep -q '"-lstdc++"' "$work/optouts.trace"
for mode in -static -nodefaultlibs -nostdlib++; do
    "$clang" --target=aarch64-unknown-netbsd --driver-mode=g++ \
        --config-system-dir="$work/config" --config-user-dir= "$mode" -### \
        "$work/input.cc" > "$work/${mode#-}.trace" 2>&1
done
grep -q '"-Bstatic"' "$work/static.trace"
grep -q '"-lstdc++"' "$work/static.trace"
! grep -q '"-lstdc++"' "$work/nodefaultlibs.trace"
! grep -q '"-lstdc++"' "$work/nostdlib++.trace"
"$clang" --target=aarch64-unknown-netbsd --driver-mode=g++ --no-default-config \
    -### "$work/input.cc" > "$work/baseline.trace" 2>&1
if grep -Fq "$private/crtbegin.o" "$work/baseline.trace"; then exit 1; fi
echo 'RED: driver without config does not select current fixture CRT'
echo 'PASS: actual available Clang driver config traces; LLVM23 native link/ELF pending'
