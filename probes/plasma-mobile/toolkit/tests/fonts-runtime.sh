#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Installed full Noto payload and target hooks.
set -eu
[ "$#" = 2 ] || { echo 'Usage: fonts-runtime.sh EXPECTED_PAYLOAD_SHA256 NEW_OUTPUT' >&2; exit 2; }
expected=$1
mkdir "$2"
out=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
sysctl kern.boottime > "$out/boot.before"
for pkg in noto-fonts noto-cjk-fonts mkfontscale libfontenc encodings; do
    pkg_info -e "$pkg" >> "$out/packages.txt"
    pkg_admin check "$pkg" >> "$out/package-check.txt" 2>&1
done
count=0
while read -r hash path; do
    [ "$(sha256 -q "$path")" = "$hash" ] || { echo "Payload differs: $path" >&2; exit 1; }
    count=$((count + 1))
done < "$expected"
printf 'Verified payloads: %s\n' "$count" > "$out/payload-check.txt"
fontdir=/usr/pkg/share/fonts/X11/TTF
for index in fonts.dir fonts.scale; do
    [ -s "$fontdir/$index" ]
    head -1 "$fontdir/$index" >> "$out/index-counts.txt"
    [ "$(head -1 "$fontdir/$index")" -eq "$(($(wc -l < "$fontdir/$index") - 1))" ]
    grep -q NotoSans-Regular.ttf "$fontdir/$index"
    ! grep -q '/Volumes/\|/private/tmp/' "$fontdir/$index"
done
fc-scan --format '%{family}\n' "$fontdir/NotoSans-Regular.ttf" > "$out/latin-family.txt"
grep -q 'Noto Sans' "$out/latin-family.txt"
for name in NotoSansCJK NotoSansMonoCJK NotoSerifCJK; do
    fc-scan --format '%{family}\n' "$fontdir/$name-VF.otf.ttc" > "$out/$name.txt"
    [ -s "$out/$name.txt" ]
done
fc-match -f '%{file}\n' 'Noto Sans:lang=ru' > "$out/russian-match.txt"
grep -q '/NotoSans-Regular.ttf' "$out/russian-match.txt"
fc-match -f '%{file}\n' 'Noto Sans CJK JP:lang=ja' > "$out/japanese-match.txt"
grep -q '/NotoSansCJK-VF.otf.ttc' "$out/japanese-match.txt"
sysctl kern.boottime > "$out/boot.after"
cmp "$out/boot.before" "$out/boot.after"
echo 'PASS: installed font bytes, native target indexes, Latin/CJK scanning and Russian/Japanese matching'
