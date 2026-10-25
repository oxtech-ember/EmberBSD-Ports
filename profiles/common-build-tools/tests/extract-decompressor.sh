#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual pkgsrc extract script.
# Input PKGSRC must not contain pkgsrc-extract-decompressor.patch yet.
# GZIP and TAR are absolute tools. EXTRACT_SH runs the script, default /bin/sh.
# This test copies mk/extract/extract. It does not build or install packages.
set -eu

[ "$#" = 2 ] || {
    echo "Usage: $0 PKGSRC NEW_WORK" >&2
    exit 2
}
pkgsrc=$(CDPATH= cd -- "$1" && pwd)
profile=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
patch=${PATCH:-patch}
sh=${EXTRACT_SH:-/bin/sh}
for tool in "${GZIP:-}" "${TAR:-}" "$sh"; do
    case "$tool" in
        /*) [ -f "$tool" ] && [ -x "$tool" ] ||
                { echo "Not an executable file: $tool" >&2; exit 2; } ;;
        *) echo 'Set GZIP and TAR to absolute executables.' >&2; exit 2 ;;
    esac
done
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
export LC_ALL=C

for variant in original patched; do
    mkdir -p "$work/$variant/mk/extract"
    cp "$pkgsrc/mk/extract/extract" "$work/$variant/mk/extract/"
done
(cd "$work/patched" && "$patch" -F0 -p1 \
    < "$profile/patches/pkgsrc-extract-decompressor.patch") > "$work/patch.log" 2>&1

fail()
{
    echo "$*" >&2
    exit 1
}

# A real gzip tar archive, and inputs for the missing-tool cases.
mkdir -p "$work/src/fixture-1.0" "$work/bin" "$work/dist"
printf '%s\n' 'extract payload' > "$work/src/fixture-1.0/payload"
(cd "$work/src" && "$TAR" -cf - fixture-1.0) > "$work/fixture-1.0.tar"
"$GZIP" -c < "$work/fixture-1.0.tar" > "$work/dist/fixture-1.0.tar.gz"
cp "$work/dist/fixture-1.0.tar.gz" "$work/dist/fixture-1.0.shar.gz"
: > "$work/dist/fixture-1.0.tar.bz2"
: > "$work/bin/not-executable"
ln -s "$GZIP" "$work/bin/gzip"

# Replace the gzip CRC-32 and size trailer. gzip writes the complete tar
# stream and then fails, so tar alone accepts the corrupt distfile.
tgz=$work/dist/fixture-1.0.tar.gz
corrupt=$work/dist/corrupt-1.0.tar.gz
size=$(wc -c < "$tgz" | tr -d ' ')
dd if="$tgz" of="$corrupt" bs=1 count=$((size - 8)) 2> /dev/null
printf '\377\377\377\377\377\377\377\377' >> "$corrupt"
if "$GZIP" -dc < "$corrupt" > "$work/corrupt.tar" 2> "$work/corrupt.log"; then
    fail 'gzip accepted the corrupt trailer'
fi
cmp "$work/fixture-1.0.tar" "$work/corrupt.tar" ||
    fail 'gzip did not write the complete stream before its trailer error'

# A long zero tail after the tar end. tar can stop reading before gzip
# writes it all; that SIGPIPE is not a decompressor failure.
(cat "$work/fixture-1.0.tar"; dd if=/dev/zero bs=65536 count=64 2> /dev/null) |
    "$GZIP" -c > "$work/dist/padded-1.0.tar.gz"

# run VARIANT CASE DISTFILE [NAME=VALUE ...]: extract in a new directory.
# OPTIONS and MEMBERS hold extract options and archive members.
# The private TMPDIR must stay empty.
run_extract()
{
    variant=$1 case_dir=$work/$1-$2 distfile=$3
    shift 3
    mkdir -p "$case_dir/tmp"
    status=0
    env PATH="$work/bin:/usr/bin:/bin" TMPDIR="$case_dir/tmp" TAR="$TAR" "$@" "$sh" \
        "$work/$variant/mk/extract/extract" ${OPTIONS:-} -d "$case_dir/out" "$distfile" ${MEMBERS:-} \
        > "$case_dir/log" 2>&1 || status=$?
    [ -z "$(ls -A "$case_dir/tmp")" ] || fail "$variant $2 left temporary files"
    return "$status"
}

missing=$work/bin/missing-zcat
payload=fixture-1.0/payload

# The original script returns 0 for a missing decompressor, which extracts
# nothing, and for a corrupt distfile.
run_extract original missing "$tgz" GZCAT="$missing" ||
    fail 'Original script did not reproduce the accepted missing decompressor'
[ ! -e "$work/original-missing/out/fixture-1.0" ] ||
    fail 'Original script extracted without a decompressor'
grep -F "$missing" "$work/original-missing/log" > /dev/null ||
    fail 'Original script did not run the missing decompressor'
run_extract original corrupt "$corrupt" GZCAT="$GZIP -dc" ||
    fail 'Original script did not reproduce the accepted corrupt distfile'
cmp "$work/src/$payload" "$work/original-corrupt/out/$payload"

# The patched script refuses missing absolute tools before the archive program.
for case_name in missing not-executable shar bzip2; do
    case "$case_name" in
        missing) set -- "$tgz" GZCAT="$missing"; tool=$missing ;;
        not-executable) set -- "$tgz" GZCAT="$work/bin/not-executable -dc"
            tool=$work/bin/not-executable ;;
        shar) set -- "$work/dist/fixture-1.0.shar.gz" GZCAT="$missing"; tool=$missing ;;
        bzip2) set -- "$work/dist/fixture-1.0.tar.bz2" BZCAT="$missing"; tool=$missing ;;
    esac
    if run_extract patched "$case_name" "$@"; then
        fail "Patched script accepted the $case_name decompressor"
    fi
    grep -Fx "extract: decompressor not found: $tool" "$work/patched-$case_name/log" > /dev/null ||
        { cat "$work/patched-$case_name/log" >&2; fail "Missing $case_name diagnostic"; }
    [ ! -e "$work/patched-$case_name/out" ] ||
        fail "Patched script created the $case_name extract directory"
done

# A decompressor that fails after the archive program accepted its output,
# also with the exclude list file, or a relative one that is not found.
for case_name in corrupt corrupt-exclude relative-missing; do
    case "$case_name" in
        corrupt) OPTIONS= ; set -- "$corrupt" GZCAT="$GZIP -dc"; code=1 ;;
        corrupt-exclude) OPTIONS=-x; set -- "$corrupt" GZCAT="$GZIP -dc"; code=1 ;;
        relative-missing) OPTIONS= ; set -- "$tgz" GZCAT='missing-zcat -dc'; code=127 ;;
    esac
    MEMBERS=
    [ "$case_name" != corrupt-exclude ] || MEMBERS=fixture-1.0/excluded
    if run_extract patched "$case_name" "$@"; then
        fail "Patched script accepted the $case_name decompressor"
    fi
    grep -Fx "extract: decompressor failed with status $code: ${1}" \
        "$work/patched-$case_name/log" > /dev/null ||
        { cat "$work/patched-$case_name/log" >&2; fail "Missing $case_name diagnostic"; }
done
OPTIONS= MEMBERS=
run_extract original relative-missing "$tgz" GZCAT='missing-zcat -dc' ||
    fail 'Original script did not reproduce the accepted relative decompressor'

# Present absolute and relative decompressors still extract the archive.
run_extract patched absolute "$tgz" GZCAT="$GZIP -dc" ||
    { cat "$work/patched-absolute/log" >&2; fail 'Absolute decompressor failed'; }
run_extract patched relative "$tgz" GZCAT='gzip -dc' ||
    { cat "$work/patched-relative/log" >&2; fail 'Relative decompressor failed'; }
run_extract patched padded "$work/dist/padded-1.0.tar.gz" GZCAT="$GZIP -dc" ||
    { cat "$work/patched-padded/log" >&2; fail 'Early archive end failed'; }
for case_name in absolute relative padded; do
    cmp "$work/src/$payload" "$work/patched-$case_name/out/$payload"
done

echo 'PASS: original silent success for missing, corrupt and relative decompressors;' \
    'seven refused decompressors; absolute, relative and early-end extraction'
