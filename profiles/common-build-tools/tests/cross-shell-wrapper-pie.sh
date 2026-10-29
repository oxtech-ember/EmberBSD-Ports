#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise generated target C/C++ wrappers.
set -eu
[ "$#" = 3 ] || { echo 'Usage: cross-shell-wrapper-pie.sh WRAPPER_DIR READELF NEW_WORK' >&2; exit 2; }
wrappers=$1 readelf=$2 work=$3
[ ! -e "$work" ] || { echo 'New work path required' >&2; exit 2; }
mkdir "$work"
printf 'int value(void) { return 7; } int main(void) { return value() != 7; }\n' > "$work/test.c"
printf 'extern "C" int value() { return 7; } int main() { return value() != 7; }\n' > "$work/test.cpp"
for lang in c cxx; do
    case "$lang" in c) compiler=$wrappers/cc; source=$work/test.c;; cxx) compiler=$wrappers/cxx; source=$work/test.cpp;; esac
    for mode in compile executable source-executable shared relocatable disabled; do
        log=$work/$lang-$mode.log
        case "$mode" in
            compile) set -- -c "$source" -o "$work/$lang.o";;
            executable|disabled) set -- "$work/$lang.o" -o "$work/$lang-$mode";;
            source-executable) set -- "$source" -o "$work/$lang-$mode";;
            shared) set -- -shared "$work/$lang.o" -o "$work/$lang.so";;
            relocatable) set -- -r "$work/$lang.o" -o "$work/$lang-rel.o";;
        esac
        if [ "$mode" = disabled ]; then pie=; else pie=-pie; fi
        WRAPPER_DEBUG=yes WRAPPER_LOG="$log" MKPIE_CFLAGS=-fPIC MKPIE_LDFLAGS="$pie" "$compiler" "$@"
        command=$(grep '^<\.>' "$log" | tail -1)
        case "$mode" in executable|source-executable) printf '%s\n' "$command" | grep -E '(^| )-pie( |$)' >/dev/null;;
            *) if printf '%s\n' "$command" | grep -E '(^| )-pie( |$)' >/dev/null; then echo "Unexpected PIE flag: $lang $mode" >&2; exit 1; fi;; esac
    done
    grep -E '(^| )-fPIC( |$)' "$work/$lang-source-executable.log" >/dev/null
    "$readelf" -h "$work/$lang-source-executable" | grep -E 'Type:[[:space:]]+DYN' >/dev/null
    "$readelf" -h "$work/$lang-executable" | grep -E 'Type:[[:space:]]+DYN' >/dev/null
    "$readelf" -l "$work/$lang-executable" | grep -F INTERP >/dev/null
    "$readelf" -h "$work/$lang.so" | grep -E 'Type:[[:space:]]+DYN' >/dev/null
    "$readelf" -l "$work/$lang.so" | grep -F INTERP >/dev/null && { echo 'Shared library has an interpreter' >&2; exit 1; }
    "$readelf" -h "$work/$lang-rel.o" | grep -E 'Type:[[:space:]]+REL' >/dev/null
    "$readelf" -h "$work/$lang-disabled" | grep -E 'Type:[[:space:]]+EXEC' >/dev/null
 done
echo 'Cross shell wrapper C/C++ PIE policy PASS'
