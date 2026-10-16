#!/bin/sh
# Exercise the cross-built consumers against the installed target providers.
set -eu
arch=${EMBERBSD_RUST_TARGET_ARCH:-aarch64}
case "$arch" in aarch64|x86_64) ;; *) echo 'unsupported Rust target architecture' >&2; exit 2 ;; esac
if [ "$#" -ne 1 ] || [ "$(uname -s)" != NetBSD ] ||
    [ "$(uname -p)" != "$arch" ]; then
    echo 'usage on matching NetBSD target: run-on-target.sh ABS_PROBE_DIR' >&2
    exit 2
fi
case "$1" in /*) probe=$1 ;; *) exit 2 ;; esac
[ -z "${LD_LIBRARY_PATH-}" ] && [ -z "${LD_PRELOAD-}" ] || {
    echo 'library-path/preload overrides are not accepted' >&2
    exit 2
}
unset LD_LIBRARY_PATH LD_PRELOAD
PATH=/usr/bin:/bin:/usr/sbin:/sbin:/rescue
export PATH
tmp=$(mktemp -d /tmp/ember-rust.XXXXXXXX)
trap 'rm -rf "$tmp"' 0
trap 'exit 1' HUP INT TERM
verify() {
    seen=0
    while read -r hash name; do
        [ "${#hash}" -eq 64 ] || return 1
        case "$hash" in *[!0-9a-f]*) return 1 ;; esac
        case "$name" in
            "$probe/rust-runtime") bit=1 ;;
            "$probe/librust-runtime.so") bit=2 ;;
            "$probe/rust-c-consumer") bit=4 ;;
            "$probe/run-on-target.sh") bit=8 ;;
            /usr/pkg/gcc16/lib/libgcc_s.so.1) bit=16 ;;
            /usr/lib/libc.so) bit=32 ;;
            /usr/lib/libpthread.so) bit=64 ;;
            /libexec/ld.elf_so) bit=128 ;;
            *) return 1 ;;
        esac
        [ "$((seen & bit))" -eq 0 ] || return 1
        seen=$((seen | bit))
        [ "$(sha256 -q "$name")" = "$hash" ] || return 1
    done < "$probe/files.sha256"
    [ "$seen" -eq 255 ]
}
verify
for name in rust-runtime librust-runtime.so; do
    ldd "$probe/$name" > "$tmp/$name.ldd"
    cat "$tmp/$name.ldd"
    grep '/usr/pkg/gcc16/lib/libgcc_s.so.1' "$tmp/$name.ldd" > /dev/null
done
timeout -k 5 30 "$probe/rust-runtime"
timeout -k 5 30 "$probe/rust-c-consumer" "$probe/librust-runtime.so"
verify
echo 'PASS: target Rust consumers and runtime provider hashes'
