#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# AI-assisted regression of the actual pkgsrc ELF metadata rule.
set -eu
[ "$#" = 3 ] || { echo 'Usage: package-requires.sh METADATA_MK BSD_MAKE NEW_OUTPUT' >&2; exit 2; }
metadata=$1
make=$2
output=$3
for path in "$metadata" "$output"; do
    case "$path" in /*) ;; *) exit 2 ;; esac
    case "$path" in *[[:space:]]*) exit 2 ;; esac
done
[ -f "$metadata" ] && [ ! -e "$output" ] && [ ! -L "$output" ] || exit 2
mkdir -p "$output/prefix/bin" "$output/prefix/lib" "$output/external/subdir"
printf '%s\n' bin/consumer lib/libown.so.1 > "$output/PLIST"
: > "$output/prefix/bin/consumer"
: > "$output/prefix/lib/libown.so.1"
: > "$output/external/libown.so.1"
: > "$output/prefix/lib/libunlisted.so.1"
ln -s "$output/external/subdir" "$output/prefix/lib/link"
cat > "$output/ldd" <<EOF_LDD
#!/bin/sh
cat <<EOF_PATHS
libown.so.1 => $output/prefix/lib/./libown.so.1
libown.so.1 => $output/prefix/lib/././libown.so.1
libown.so.1 => $output/prefix/lib/../lib/libown.so.1
libsymlink.so.1 => $output/prefix/lib/link/../libown.so.1
libunlisted.so.1 => $output/prefix/lib/../lib/libunlisted.so.1
libexternal.so.1 => $output/external/./libexternal.so.1
libparent.so.1 => $output/link/../libparent.so.1
libc.so.12 => /usr/lib/libc.so.12
EOF_PATHS
EOF_LDD
chmod +x "$output/ldd"
cat > "$output/Makefile" <<EOF_MAKE
_BUILD_DEFS= PREFIX
PREFIX= $output/prefix
WRKDIR= $output/work
_PLIST_NOKEYWORDS= $output/PLIST
SH= /bin/sh
PKGSRCDIR= $(CDPATH= cd -- "$(dirname -- "$metadata")/../../.." && pwd)
RUN= @set -e;
TEST= test
MKDIR= mkdir -p
ECHO= echo
DATE= date
UNAME= uname
AWK= awk
SORT= sort
SED= sed
CAT= cat
TYPE= type
GREP= grep
CHMOD= chmod
TRUE= true
PKGSRC_SETENV= env
LDD= $output/ldd
INIT_SYSTEM= none
OBJECT_FMT= ELF
CHECK_SHLIBS_SUPPORTED= yes
.include "$metadata"
EOF_MAKE
"$make" -f "$output/Makefile" "$output/work/.pkgdb/+BUILD_INFO" > "$output/make.log" 2>&1
grep '^REQUIRES=' "$output/work/.pkgdb/+BUILD_INFO" > "$output/requires.txt"
cat > "$output/expected.txt" <<EOF_EXPECTED
REQUIRES=/usr/lib/libc.so.12
REQUIRES=$output/prefix/lib/link/../libown.so.1
REQUIRES=$output/prefix/lib/../lib/libunlisted.so.1
REQUIRES=$output/external/libexternal.so.1
REQUIRES=$output/link/../libparent.so.1
EOF_EXPECTED
sort "$output/expected.txt" > "$output/expected-sorted.txt"
cmp "$output/expected-sorted.txt" "$output/requires.txt"
# Repeat with no installed prefix: file identity must use DESTDIR, while
# emitted dependency names must remain target paths without the staging root.
stage=$output/stage
mkdir -p "$stage$output" "$stage$output/external/subdir"
mv "$output/prefix" "$stage$output/prefix"
: > "$stage$output/external/libown.so.1"
rm "$stage$output/prefix/lib/link"
ln -s "$stage$output/external/subdir" "$stage$output/prefix/lib/link"
"$make" -f "$output/Makefile" DESTDIR="$stage" WRKDIR="$output/stage-work" \
    "$output/stage-work/.pkgdb/+BUILD_INFO" > "$output/stage-make.log" 2>&1
grep '^REQUIRES=' "$output/stage-work/.pkgdb/+BUILD_INFO" > "$output/stage-requires.txt"
cmp "$output/expected-sorted.txt" "$output/stage-requires.txt"
echo 'PASS: native and DESTDIR ELF metadata remove proven self requirements; preserve external, unlisted and symlink-distinct paths'
