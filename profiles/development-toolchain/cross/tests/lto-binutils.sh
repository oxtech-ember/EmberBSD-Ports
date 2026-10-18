#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; verify GCC16 LTO uses the selected current GNU tools.
set -eu
usage() {
    echo 'Usage: lto-binutils.sh GCC16_CROSS_PREFIX NEW_WORK' >&2
    exit 2
}
[ "$#" -eq 2 ] || usage
prefix=$1 work=$2
for path in "$prefix" "$work"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use paths without whitespace or shell metacharacters.' >&2; exit 2;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'NEW_WORK already exists.' >&2; exit 2; }
triplet=aarch64--netbsd
gcc=$prefix/bin/$triplet-gcc
gxx=$prefix/bin/$triplet-g++
ld=$prefix/bin/$triplet-ld
as=$prefix/bin/$triplet-as
readelf=$prefix/bin/$triplet-readelf
gcc_libexec=$prefix/libexec/gcc/$triplet/16.2.0
collect2=$gcc_libexec/collect2
plugin=$gcc_libexec/liblto_plugin.so
lto_wrapper=$gcc_libexec/lto-wrapper
for tool in "$gcc" "$gxx" "$ld" "$as" "$readelf"; do
    [ -x "$tool" ] || { echo "Required GCC16 cross tool missing: $tool" >&2; exit 1; }
done
for tool in "$collect2" "$plugin" "$lto_wrapper"; do
    [ -x "$tool" ] || { echo "Required GCC16 LTO tool missing: $tool" >&2; exit 1; }
done
for compiler in "$gcc" "$gxx"; do
    [ "$("$compiler" -dumpfullversion)" = 16.2.0 ] || {
        echo "GCC 16.2.0 required: $compiler" >&2; exit 1;
    }
    [ "$("$compiler" -dumpmachine)" = "$triplet" ] || {
        echo "AArch64 NetBSD compiler required: $compiler" >&2; exit 1;
    }
    for name in as ld; do
        selected=$("$compiler" -print-prog-name="$name")
        [ "$selected" = "$prefix/bin/$triplet-$name" ] || {
            echo "$compiler selects unexpected $name: $selected" >&2; exit 1;
        }
    done
done
for tool in as ld readelf; do
    version=$($prefix/bin/$triplet-$tool --version 2>&1 | sed -n '1p')
    printf '%s\n' "$version" | grep -Eq 'GNU .* 2[.]47([.]|[[:space:]]|$)' || {
        echo "GNU $tool 2.47 required: $version" >&2; exit 1;
    }
done
mkdir "$work"
work=$(CDPATH= cd -- "$work" && pwd -P)
{
    printf 'target=%s\n' "$triplet"
    printf 'gcc=%s\n' "$gcc"
    printf 'gxx=%s\n' "$gxx"
    printf 'as=%s\n' "$as"
    printf 'ld=%s\n' "$ld"
    printf 'readelf=%s\n' "$readelf"
    printf 'collect2=%s\nplugin=%s\nlto_wrapper=%s\n' "$collect2" "$plugin" "$lto_wrapper"
    "$gcc" --version | sed -n '1p'
    "$gxx" --version | sed -n '1p'
    "$as" --version | sed -n '1p'
    "$ld" --version | sed -n '1p'
    "$readelf" --version | sed -n '1p'
    shasum -a 256 "$gcc" "$gxx" "$as" "$ld" "$readelf"
} > "$work/inputs.txt"
cat > "$work/probe.c" <<'EOF'
__attribute__((noreturn)) void
_start(void)
{
    for (;;)
        __asm__ volatile("wfe");
}
EOF
cat > "$work/probe.cc" <<'EOF'
extern "C" __attribute__((noreturn)) void
_start(void)
{
    for (;;)
        __asm__ volatile("wfe");
}
EOF
"$gcc" -v -O2 -flto -fuse-linker-plugin -ffreestanding \
    -fno-stack-protector -nostdlib -nostartfiles \
    -Wl,-e,_start -Wl,-v "$work/probe.c" -o "$work/probe-c.elf" \
    > "$work/c-link.log" 2>&1
"$gxx" -v -O2 -flto -fuse-linker-plugin -ffreestanding \
    -fno-stack-protector -fno-exceptions -fno-rtti \
    -nostdlib -nostartfiles -Wl,-e,_start -Wl,-v \
    "$work/probe.cc" -o "$work/probe-cxx.elf" > "$work/cxx-link.log" 2>&1
for log in "$work/c-link.log" "$work/cxx-link.log"; do
    grep -F "$collect2" "$log" >/dev/null
    grep -F "$plugin" "$log" >/dev/null
    grep -F "$lto_wrapper" "$log" >/dev/null
    grep -F "$ld" "$log" >/dev/null
    grep -F "$as" "$log" >/dev/null
done
for image in "$work/probe-c.elf" "$work/probe-cxx.elf"; do
    "$readelf" -h "$image" > "$image.header"
    grep -Eq 'Type:[[:space:]]+EXEC' "$image.header"
    grep -Eq 'Machine:[[:space:]]+AArch64' "$image.header"
done
echo 'PASS: GCC16 C/C++ LTO uses collect2, the GCC plugin, and default Binutils 2.47; both outputs are AArch64 ELF executables.'
