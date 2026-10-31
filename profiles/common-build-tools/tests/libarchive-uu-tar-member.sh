#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: libarchive-uu-tar-member.sh LIBARCHIVE_SOURCE CC PYTHON NEW_WORK
#
# The uu filter bidder of libarchive 3.8.10 skipped lines with control
# characters while it looked for a "begin" line, so it found one inside a
# tar member and took the whole tar for a uuencoded stream. The
# MIME-tools distfile, which ships uuencoded test messages, was then an
# unrecognized archive. Build bsdtar from LIBARCHIVE_SOURCE with the host
# compiler and require that a tar with a uuencoded member lists as a tar.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 LIBARCHIVE_SOURCE CC PYTHON NEW_WORK" >&2; exit 2; }
source=$1 cc=$2 python=$3 work=$4
[ ! -e "$work" ] || { echo "FAIL: $work exists" >&2; exit 1; }
mkdir -p "$work"
cp -R "$source" "$work/src"
cd "$work/src"
CC=$cc ./configure --disable-shared --enable-bsdtar=static \
    --disable-bsdcpio --disable-bsdcat --disable-bsdunzip --disable-acl \
    --disable-xattr --without-zlib --without-bz2lib --without-libb2 \
    --without-iconv --without-lz4 --without-zstd --without-lzma \
    --without-cng --without-openssl --without-xml2 --without-expat \
    > "$work/configure.log" 2>&1
make -j4 bsdtar > "$work/make.log" 2>&1
"$python" - "$work/uu-member.tar" <<'PY'
import io, sys, tarfile
uu = b"Subject: uu\n\nbegin 644 hello.txt\n&:&5L;&\\*\n`\nend\n"
with tarfile.open(sys.argv[1], "w", format=tarfile.GNU_FORMAT) as t:
    for name, data in (("d/a.txt", b"x\n"), ("d/msg.uu", uu)):
        info = tarfile.TarInfo(name)
        info.size = len(data)
        info.mtime = 0
        t.addfile(info, io.BytesIO(data))
PY
if ! ./bsdtar -tf "$work/uu-member.tar" > "$work/list" 2> "$work/list.err"; then
	echo "FAIL: bsdtar did not read the tar with a uuencoded member:" >&2
	cat "$work/list.err" >&2
	exit 1
fi
printf 'd/a.txt\nd/msg.uu\n' | cmp -s - "$work/list" || {
	echo "FAIL: unexpected listing:" >&2; cat "$work/list" >&2; exit 1; }
echo "PASS: a uuencoded tar member does not make the tar a uu stream"
