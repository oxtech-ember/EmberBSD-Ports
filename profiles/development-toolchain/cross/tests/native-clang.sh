#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Native host architecture, OS and libc guard.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-native-clang.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/profile/cross/patches" "$work/bin" "$work/archives" "$work/tools/bin"
cp "$here/host-math.sh" "$here/host-sources.tsv" "$work/profile/cross/"
cp "$here/../sources.tsv" "$work/profile/sources.tsv"
cp "$here/patches/gmp-t-rand-varargs.patch" "$work/profile/cross/patches/"
printf 'deliberately bad archive\n' > "$work/archives/gmp-6.3.0.tar.xz"
printf '#!/bin/sh\nexit 99\n' > "$work/tools/bin/nbgmake"
cat > "$work/bin/clang" <<'EOF'
#!/bin/sh
case "$1" in
    --version) echo 'clang version 21.0.0';;
    -dumpmachine) echo "$FIXTURE_TARGET";;
    -dumpfullversion) echo 21.0.0;;
    *) exit 99;;
esac
EOF
cat > "$work/bin/uname" <<'EOF'
#!/bin/sh
case "$1" in -s) echo "$FIXTURE_OS";; -m) echo "$FIXTURE_ARCH";; *) exit 99;; esac
EOF
cat > "$work/bin/getconf" <<'EOF'
#!/bin/sh
[ "$1" = GNU_LIBC_VERSION ] && echo 'glibc 2.42'
EOF
chmod +x "$work/bin/clang" "$work/bin/uname" "$work/bin/getconf" "$work/tools/bin/nbgmake"
export PATH="$work/bin:$PATH" HOST_CC="$work/bin/clang" HOST_CXX="$work/bin/clang" CROSS_JOBS=1
check() {
    export FIXTURE_OS=$1 FIXTURE_ARCH=$2 FIXTURE_TARGET=$3
    if sh "$work/profile/cross/host-math.sh" --native-clang "$work/archives" "$work/tools" "$work/output" > "$work/result" 2>&1; then
        echo 'FAIL: corrupt archive accepted' >&2; exit 1
    fi
    grep -Fq "$4" "$work/result" || { cat "$work/result"; exit 1; }
    [ ! -e "$work/output" ]
}
check Darwin arm64 arm64-apple-darwin27 'gmp archive SHA256 mismatch'
check Darwin x86_64 x86_64-apple-darwin27 'gmp archive SHA256 mismatch'
check Linux aarch64 aarch64-unknown-linux-gnu 'gmp archive SHA256 mismatch'
check Linux x86_64 x86_64-unknown-linux-gnu 'gmp archive SHA256 mismatch'
check Darwin x86_64 x86_64-unknown-linux-gnu 'Host-only Clang target differs'
check Darwin arm64 arm64-apple-ios20 'Host-only Clang target differs'
check Linux x86_64 x86_64-apple-darwin27 'Host-only Clang target differs'
check Linux aarch64 aarch64-unknown-freebsd16 'Host-only Clang target differs'
check Linux x86_64 x86_64-unknown-linux-musl 'Host-only Clang target differs'
check Linux x86_64 x86_64-unknown-linux-gnux32 'Host-only Clang target differs'
if sh "$work/profile/cross/host-math.sh" "$work/archives" "$work/tools" "$work/output" > "$work/default" 2>&1; then
    echo 'FAIL: default host compiler contract changed' >&2; exit 1
fi
grep -Fq 'GCC 16 host compiler required' "$work/default"
echo 'PASS: four native Clang targets, six same-architecture foreign OS/ABI rejections, unchanged default GCC16 guard'
