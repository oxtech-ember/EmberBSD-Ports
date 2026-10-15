#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), exercise the actual cross-target cases.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 PRISTINE_PYTHON PATCHED_PYTHON NEW_WORK" >&2; exit 2; }
pristine=$1 patched=$2 work=$3
mkdir "$work"
extract_cases()
{
    awk '
        /^[ \t]*case "\$host" in$/ { if (!active) { active = 1; block = ""; depth = 0 } }
        active {
            block = block $0 "\n"
            if ($0 ~ /^[ \t]*case /) depth++
            if ($0 ~ /^[ \t]*esac([ \t;]|$)/) {
                depth--
                if (!depth) {
                    if (block ~ /cross build not supported for/) { printf "%s", block; count++ }
                    active = 0
                }
            }
        }
        END { if (active || count != 2) exit 1 }
    ' "$1" > "$2"
}
for variant in pristine patched; do
    case "$variant" in pristine) source=$pristine;; patched) source=$patched;; esac
    extract_cases "$source/configure" "$work/$variant.cases"
    {
        printf '%s\n' '#!/bin/sh' 'set -eu' 'as_fn_error() { exit 42; }'
        printf '%s\n' 'host=$1 host_cpu=${host%%-*}' 'MACHDEP=netbsd11'
        cat "$work/$variant.cases"
        printf '%s\n' 'printf "%s/%s\n" "$ac_sys_system" "$_host_ident"'
    } > "$work/$variant.sh"
done
if sh "$work/pristine.sh" aarch64--netbsd > "$work/before.txt" 2>&1; then
    echo 'Pristine cross barrier unexpectedly accepted NetBSD' >&2; exit 1
fi
for target in ${PYTHON_CROSS_TARGETS:-aarch64--netbsd aarch64-unknown-netbsd11.0}; do
    [ "$(sh "$work/patched.sh" "$target")" = "NetBSD/${target%%-*}" ]
done
for variant in pristine patched; do
    [ "$(sh "$work/$variant.sh" aarch64-unknown-linux-gnu)" = Linux/aarch64 ]
    if sh "$work/$variant.sh" aarch64-unknown-unlisted > "$work/$variant-unknown.txt" 2>&1; then
        echo 'Unknown target unexpectedly accepted' >&2; exit 1
    fi
    if sh "$work/$variant.sh" riscv64-unknown-netbsd > "$work/$variant-foreign-netbsd.txt" 2>&1; then
        echo 'Unsupported NetBSD architecture unexpectedly accepted' >&2; exit 1
    fi
done
# The maintained input carries the same two added cases as configure.
for file in configure configure.ac; do
    awk '/^[ \t]*aarch64-\*-netbsd\*.*\)/ { active = 1; count++ }
        active { print }
        active && /;;/ { active = 0 }
        END { if (count != 2 || active) exit 1 }' \
        "$patched/$file" > "$work/$file.netbsd-cases"
done
cmp "$work/configure.netbsd-cases" "$work/configure.ac.netbsd-cases"
echo 'PASS: original NetBSD barrier, both repaired cases, existing Linux and unknown-target rejection'
