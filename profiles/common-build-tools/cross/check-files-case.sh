#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), preserve target PLIST spelling on cross hosts.
set -eu
[ "$#" = 3 ] || { echo 'Usage: check-files-case.sh STAGE EXPECTED ADDED' >&2; exit 2; }
stage=$1 expected=$2 added=$3
[ -d "$stage" ] && [ -f "$expected" ] && [ -f "$added" ]
probe=$(mktemp -d "$stage/.pkgsrc-case.XXXXXX")
output=$added.case.$$
collisions=$added.collisions.$$
trap 'rm -f "$probe/probe" "$output" "$collisions"; rmdir "$probe"' EXIT
trap 'exit 1' HUP INT TERM
: > "$probe/probe"
# A case-sensitive stage already preserves the target spelling exactly.
[ -e "$probe/PROBE" ] || exit 0
LC_ALL=C; export LC_ALL

# A case-insensitive stage cannot represent every target path. Permit only
# PLIST aliases that resolve to the same staged symlink target, plus the two
# OpenSSL names generated from one OSSL_trace_enabled.pod manual page.
awk '
    FILENAME == ARGV[1] {
        key=tolower($0)
        if (key in spelling && spelling[key] != $0)
            print spelling[key] "\t" $0
        else
            spelling[key]=$0
    }
' "$expected" > "$collisions"
while IFS="$(printf '\t')" read -r first second; do
    [ -n "$second" ] || continue
    first_target=
    second_target=
    if [ -L "$first" ] && [ -L "$second" ]; then
        first_target=$(readlink "$first" 2>/dev/null || true)
        second_target=$(readlink "$second" 2>/dev/null || true)
    else
        first_base=${first##*/}
        second_base=${second##*/}
        if [ "${first%/*}" = "${second%/*}" ]; then
            case "$first_base:$second_base" in
                OSSL_TRACE_ENABLED.3:OSSL_trace_enabled.3|OSSL_trace_enabled.3:OSSL_TRACE_ENABLED.3)
                    if [ -f "$first" ] && [ -f "$second" ] &&
                        grep -q 'OSSL_TRACE_ENABLED' "$first" &&
                        grep -q 'OSSL_trace_enabled' "$first"; then
                        first_target=OpenSSL-OSSL_trace_enabled-manual
                        second_target=$first_target
                    fi
                    ;;
            esac
        fi
    fi
    if [ -z "$first_target" ] || [ "$first_target" != "$second_target" ]; then
        echo "Ambiguous target files on case-insensitive stage: $first and $second" >&2
        exit 1
    fi
    echo "Preserving case-colliding aliases: $first and $second"
done < "$collisions"

# One physical symlink may represent multiple identical target aliases on this
# host. Emit every exact PLIST spelling so pkg_create archives each target name.
awk '
    FILENAME == ARGV[1] {
        key=tolower($0)
        found=0
        for (i=1; i<=count[key]; i++)
            if (spelling[key, i] == $0)
                found=1
        if (!found)
            spelling[key, ++count[key]]=$0
        next
    }
    {
        key=tolower($0)
        if (key in count)
            for (i=1; i<=count[key]; i++)
                print spelling[key, i]
        else
            print $0
    }
' "$expected" "$added" > "$output"
sort -u "$output" > "$added"

