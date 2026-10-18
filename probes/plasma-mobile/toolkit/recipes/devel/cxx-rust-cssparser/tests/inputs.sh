#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Compiler responses are fixture boundaries; no Rust toolchain is installed.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
helper=$root/files/verify-cross-inputs.sh
[ -f "$helper" ] || { echo 'FAIL: target std preflight is missing' >&2; exit 1; }
work=$(mktemp -d /tmp/ember-cssparser-inputs.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
work=$(CDPATH= cd -- "$work" && pwd -P)
mkdir -p "$work/host/bin" "$work/wrappers"
export FIXTURE_HOST=$work/host
cat > "$work/host/bin/rustc" <<'SH'
#!/bin/sh
case "$1" in
  -vV)
    echo 'rustc 1.99.1 (58cf8f9c3 2026-10-13)'
    echo 'commit-hash: 58cf8f9c35b355199727627d07ae34a4e2846d67'
    echo "host: ${FIXTURE_HOST_TRIPLE:-aarch64-apple-darwin}";;
  --target)
    [ "$3" = --print ] && [ "$4" = target-libdir ] || exit 99
    echo "$FIXTURE_HOST/lib/rustlib/$2/lib";;
  --crate-type=lib)
    [ "${FIXTURE_BAD_STD:-0}" = 0 ] || { echo 'error[E0514]: incompatible std producer' >&2; exit 1; }
    previous=
    for argument do
      if [ "$previous" = -o ]; then printf 'compiled metadata fixture\n' > "$argument"; fi
      previous=$argument
    done;;
  *) exit 99;;
esac
SH
cat > "$work/host/bin/cargo" <<'SH'
#!/bin/sh
[ "$1" = -V ] || { echo 'FAIL: cargo must not build during preflight' >&2; exit 99; }
echo 'cargo 1.99.1 (fixture)'
SH
for triplet in aarch64--netbsd x86_64--netbsd; do
  for driver in gcc g++; do
    cat > "$work/wrappers/$triplet-$driver" <<SH
#!/bin/sh
case "\$1" in -dumpmachine) echo '$triplet';; -dumpfullversion) echo 16.2.0;; *) exit 99;; esac
SH
    chmod 755 "$work/wrappers/$triplet-$driver"
  done
done
chmod 755 "$work/host/bin/rustc" "$work/host/bin/cargo"
for std_target in aarch64-unknown-netbsd x86_64-unknown-netbsd; do
  mkdir -p "$work/host/lib/rustlib/$std_target/lib"
  printf 'target std fixture\n' > "$work/host/lib/rustlib/$std_target/lib/libstd-test.rlib"
  printf 'target core fixture\n' > "$work/host/lib/rustlib/$std_target/lib/libcore-test.rlib"
done
run() {
  sh "$helper" "$work/host" "${target:-aarch64-unknown-netbsd}" "${gnu:-aarch64--netbsd}" "$work/wrappers" "$work/probe.rmeta"
}
[ "$(run)" = aarch64-apple-darwin ]
(target=x86_64-unknown-netbsd gnu=x86_64--netbsd run) > "$work/amd64.host"
grep -qx aarch64-apple-darwin "$work/amd64.host"
(FIXTURE_HOST_TRIPLE=x86_64-apple-darwin run) > "$work/native-x86.host"
grep -qx x86_64-apple-darwin "$work/native-x86.host"
reject() {
  if run > "$work/reject.log" 2>&1; then echo "FAIL: accepted $1" >&2; exit 1; fi
}
(gnu=x86_64--netbsd reject 'mixed GNU architecture')
(target=riscv64-unknown-netbsd reject 'unsupported target')
(FIXTURE_BAD_STD=1 reject 'incompatible std producer')
mv "$work/host/lib/rustlib/aarch64-unknown-netbsd/lib/libcore-test.rlib" "$work/core.saved"
reject 'missing target std'
echo 'PASS: native host detection, two targets, missing/incompatible std and mixed compiler guards'
