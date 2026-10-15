#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Check target-only recovery without changing the completed host frontend.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
work=$(mktemp -d /tmp/ember-runtime-layout.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
triplet=x86_64--netbsd
mkdir -p "$work/build/gcc" "$work/build/$triplet/libstdc++-v3/src/.libs" \
    "$work/build/$triplet/libgcc" "$work/stage/usr/pkg/gcc16/$triplet/lib"
for file in Makefile config.cache config.status config.log auto-host.h configargs.h xgcc cc1 cc1plus; do
    printf 'preserved frontend %s\n' "$file" > "$work/build/gcc/$file"
done
printf 'original receipt\n' > "$work/inputs.txt"
for file in Makefile config.cache config.status config.log libtool; do
    printf 'old configure %s\n' "$file" > "$work/build/$triplet/libstdc++-v3/$file"
done
printf 'old install path\n' > "$work/build/$triplet/libstdc++-v3/src/libstdc++.la"
printf 'old install path\n' > "$work/build/$triplet/libstdc++-v3/src/.libs/libstdc++.lai"
printf 'preserved target object\n' > "$work/build/$triplet/libstdc++-v3/src/object.lo"
printf 'preserved libgcc map\n' > "$work/build/$triplet/libgcc/libgcc.map"
printf 'partial target DSO\n' > "$work/stage/usr/pkg/gcc16/$triplet/lib/libgcc_s.so.1"
ln -s libgcc_s.so.1 "$work/stage/usr/pkg/gcc16/$triplet/lib/libgcc_s.so"
fail() { echo "$*" >&2; exit 2; }
. "$here/resume-state.sh"
command -v backup_runtime_resume >/dev/null || { echo 'FAIL: target-only runtime recovery is missing' >&2; exit 1; }
backup_runtime_resume
verify_frontend_state
[ -z "$(find "$work/stage" -type f -o -type l)" ]
[ -f "$resume_backup/stage/usr/pkg/gcc16/$triplet/lib/libgcc_s.so.1" ]
(cd "$resume_backup/stage" && shasum -a 256 -c ../stage.sha256)
grep -F 'libgcc_s.so' "$resume_backup/stage.symlinks" >/dev/null
[ ! -e "$work/build/$triplet/libstdc++-v3/Makefile" ]
[ ! -e "$work/build/$triplet/libstdc++-v3/libtool" ]
[ ! -e "$work/build/$triplet/libstdc++-v3/src/libstdc++.la" ]
[ ! -e "$work/build/$triplet/libstdc++-v3/src/.libs/libstdc++.lai" ]
grep -qx 'preserved target object' "$work/build/$triplet/libstdc++-v3/src/object.lo"
grep -qx 'preserved libgcc map' "$work/build/$triplet/libgcc/libgcc.map"
printf 'changed frontend config\n' >> "$work/build/gcc/configargs.h"
if (verify_frontend_state) > "$work/reject.log" 2>&1; then
    echo 'FAIL: changed frontend configure state accepted' >&2; exit 1
fi
grep -q -- '--with-toolexeclibdir=/usr/pkg/gcc16/lib' "$here/build.sh" || {
    echo 'FAIL: canonical cross-library configure argument is missing' >&2; exit 1;
}
echo 'PASS: full stage backup, target metadata reset, object reuse and immutable frontend state'
