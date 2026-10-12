#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Fresh-board install acceptance for plasma6-milou.
# Unlike accept.sh this script targets a board without a previous Milou package,
# so there is no before/after regression stage. The MIME regression receipt for
# the fixed package lives with the first acceptance run.
set -eu
[ "$#" = 1 ] || { echo 'Usage: accept-zero3w.sh ABSOLUTE_BUNDLE_DIR' >&2; exit 2; }
bundle=$(CDPATH= cd -- "$1" && pwd)
cd "$bundle"
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin
export PATH
umask 077
mkdir before after before/home before/runtime
/sbin/sysctl kern.boottime > before/boot
/usr/bin/sha256 /netbsd > before/kernel.sha256
actual=$(/usr/bin/sha256 -q plasma6-milou-6.7.5nb1.tgz)
expected=$(awk '$2 == "plasma6-milou-6.7.5nb1.tgz" {print $1}' SHA256)
[ "$actual" = "$expected" ]
if /usr/sbin/pkg_info -e plasma6-milou > before/package 2>&1; then
    ! grep -q '^plasma6-milou-6.7.5nb1$' before/package
fi
/usr/sbin/pkg_add -U ./plasma6-milou-6.7.5nb1.tgz > install.log 2>&1
/usr/sbin/pkg_info -e plasma6-milou | grep -q '^plasma6-milou-6.7.5nb1$'
while read -r expected file; do
    actual=$(/usr/bin/sha256 -q "$file")
    [ "$actual" = "$expected" ] || { echo "Payload mismatch: $file"; exit 1; }
done < payload.sha256
/usr/sbin/pkg_admin check plasma6-milou > package-check.log 2>&1
sh tests/run.sh "$PWD/milou-mime" "$PWD/after/milou"
timeout -k 5 60 env -i PATH="$PATH" HOME="$PWD/before/home" LC_ALL=C.UTF-8 \
    XDG_RUNTIME_DIR="$PWD/before/runtime" QT_QPA_PLATFORM=offscreen \
    dbus-run-session -- "$PWD/milou-mime" > after/mime.log 2>&1
cat after/mime.log
grep -q '^PASS: installed Milou preserves URL list, UTF-8 text, HTML and opaque bytes$' after/mime.log
/sbin/sysctl kern.boottime > after/boot
/usr/bin/sha256 /netbsd > after/kernel.sha256
cmp before/boot after/boot
cmp before/kernel.sha256 after/kernel.sha256
echo 'PASS: fresh-board Milou install, payload hashes, package check, MIME conversion and QML tests; boot and kernel unchanged'
