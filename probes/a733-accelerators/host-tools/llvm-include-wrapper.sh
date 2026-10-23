#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD contributors (AI-assisted).
# Replace the shared host include directory with its selected-LLVM view.
set -eu
[ "$#" -ge 3 ] || {
    echo "usage: $0 COMPILER HOST_INCLUDE OVERLAY [COMPILER_ARGUMENT ...]" >&2
    exit 2
}
compiler=$1
host_include=$2
overlay=$3
case "$compiler:$host_include:$overlay" in
    *[!A-Za-z0-9_./:+-]*) echo "Use absolute paths without whitespace or quotes." >&2; exit 2 ;;
esac
case "$compiler:$host_include:$overlay" in
    /*:/*:/*) ;;
    *) echo "Compiler and include paths must be absolute." >&2; exit 2 ;;
esac
run_compiler()
{
    compiler=$1
    host_include=$2
    overlay=$3
    shift 3
    original_count=$#
    pending=no
    for argument do
        if [ "$pending" = yes ]; then
            [ "$argument" = "$host_include" ] && argument=$overlay
            pending=no
        else
            case "$argument" in
                -I|-isystem|-iquote|-idirafter) pending=yes ;;
                "-I$host_include") argument="-I$overlay" ;;
                "-isystem$host_include") argument="-isystem$overlay" ;;
                "-iquote$host_include") argument="-iquote$overlay" ;;
                "-idirafter$host_include") argument="-idirafter$overlay" ;;
            esac
        fi
        set -- "$@" "$argument"
    done
    [ "$pending" = no ] || { echo "Compiler command ends with an include option." >&2; exit 2; }
    while [ "$original_count" -gt 0 ]; do
        shift
        original_count=$((original_count - 1))
    done
    exec "$compiler" "$@"
}
run_compiler "$@"
