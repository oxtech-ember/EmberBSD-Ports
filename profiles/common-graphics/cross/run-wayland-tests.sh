#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; run the complete enabled upstream suite against installed Wayland.
set -eu
check_runtime_sdk_absent() {
  scanner=$1 query=$2 evidence=$3
  status=0
  "$query" -e 'wayland-devel-[0-9]*' > "$evidence/sdk-query.stdout" \
      2> "$evidence/sdk-query.stderr" || status=$?
  [ "$status" -eq 1 ] && [ ! -s "$evidence/sdk-query.stdout" ] &&
      [ ! -s "$evidence/sdk-query.stderr" ] && [ ! -e "$scanner" ] &&
      [ ! -L "$scanner" ] || {
    echo 'Runtime verification requires no target Wayland SDK/scanner and a successful package query' >&2
    return 1
  }
}
usage() { echo "Usage: $0 [--runtime] [--target aarch64|amd64] NEW_RESULT_DIRECTORY" >&2; exit 2; }
target=aarch64
target_seen=no
suite=full
while [ "$#" -gt 0 ]; do
  case "$1" in
    --runtime)
      [ "$suite" = full ] || usage
      suite=runtime
      shift
      ;;
    --target)
      [ "$#" -ge 2 ] && [ -n "$2" ] && [ "$target_seen" = no ] || usage
      target=$2 target_seen=yes
      shift 2
      ;;
    --*) usage;;
    *) break;;
  esac
done
[ "$#" -eq 1 ] || usage
case "$target" in
  aarch64) processor=aarch64;;
  amd64) processor=x86_64;;
  *) usage;;
esac
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = "$processor" ] || {
  echo "Run on EmberBSD/NetBSD $target" >&2; exit 2
}
case "$1" in
  /*) output=$1;;
  *) output=$(pwd -P)/$1;;
esac
cd -- "$(dirname -- "$0")"
bundle=$(pwd -P)
[ -f target.txt ] && [ "$(cat target.txt)" = "$target" ] || {
  echo 'Bundle target does not match selected target' >&2; exit 2
}
[ -f suite.txt ] && [ "$(cat suite.txt)" = "$suite" ] || {
  echo 'Bundle suite does not match selected suite' >&2; exit 2
}
mkdir -m 700 -- "$output"
result=$(cd -- "$output" && pwd -P)
for manifest in artifacts.sha256 runtime.sha256; do
  while read -r expected file; do
    [ -f "$file" ] && [ "$(sha256 -q "$file")" = "$expected" ] || {
      echo "Artifact checksum mismatch: $file" >&2; exit 1
    }
  done < "$manifest"
done
export PATH=/usr/pkg/bin:/usr/bin:/bin:/usr/sbin:/sbin
unset LD_LIBRARY_PATH LD_PRELOAD DYLD_LIBRARY_PATH
unset WAYLAND_TEST_NO_LEAK_CHECK WAYLAND_TEST_NO_TIMEOUTS
ulimit -c 0
uname -a > "$result/platform.txt"
package=wayland-1.26.0nb1
if [ "$suite" = runtime ]; then
  package=wayland-1.26.0nb2
  check_runtime_sdk_absent /usr/pkg/bin/wayland-scanner /usr/sbin/pkg_info "$result"
fi
/usr/sbin/pkg_info -e "$package" > "$result/package.txt"
/usr/sbin/pkg_admin check "$package" > "$result/package-check.txt" 2>&1
# Upstream adds a directory and socket name; result paths can exceed sun_path.
runtime=$(mktemp -d /tmp/ew.XXXXXXXX)
trap 'rm -rf "$runtime"' EXIT HUP INT TERM
mkdir -m 700 "$result/scanner-output"
export XDG_RUNTIME_DIR=$runtime
export TEST_SRC_DIR=$bundle/tests TEST_BUILD_DIR=$bundle/tests
export TEST_DATA_DIR=$bundle/tests/data TEST_OUTPUT_DIR=$result/scanner-output
if [ "$suite" = full ]; then
  export SED=/usr/bin/sed WAYLAND_SCANNER=/usr/pkg/bin/wayland-scanner
  export WAYLAND_EGL_LIB=/usr/pkg/lib/libwayland-egl.so NM=/usr/bin/nm
else
  unset SED WAYLAND_SCANNER WAYLAND_EGL_LIB NM
fi
passed=0 skipped=0 failed=0
while IFS="$(printf '\t')" read -r name executable kind limit; do
  if [ "$kind" = elf ]; then
    ldd "$bundle/$executable" > "$result/$name.ldd"
    if ! awk '$2 == "=>" && ($3 !~ /^\// || ($1 ~ /^-lwayland/ && $3 !~ /^\/usr\/pkg\/lib\/libwayland/)) { bad=1 } END { exit bad }' "$result/$name.ldd"; then
      echo "FAIL $name unresolved or foreign Wayland dependency" | tee -a "$result/results.txt"
      failed=$((failed + 1))
      continue
    fi
  fi
  status=0
  /usr/bin/timeout -k 5 "$limit" "$bundle/$executable" > "$result/$name.log" 2>&1 || status=$?
  case "$status" in
    0) passed=$((passed + 1)); state=PASS;;
    77) skipped=$((skipped + 1)); state=SKIP;;
    *) failed=$((failed + 1)); state=FAIL;;
  esac
  echo "$state $name (exit $status)" | tee -a "$result/results.txt"
done < tests.tsv
echo "Upstream invocations: $passed passed, $skipped skipped, $failed failed" | tee -a "$result/results.txt"
[ "$failed" -eq 0 ]
