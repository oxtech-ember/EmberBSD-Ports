#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors.
# Shared by cross-bulk and the graph exporter. The selected pkg_info owns
# pattern/version semantics and its -K argument selects the native database.

native_current_pattern()
{
    [ -n "$1" ] || return 2
    case "$2" in
        "$1"-[0-9]*) printf '%s>=%s\n' "$1" "${2#"$1"-}" ;;
        *) printf '%s\n' "$1" ;;
    esac
}

native_current_query()
{
    ncp_pattern=$(native_current_pattern "$1" "$2") || return 2
    shift 2
    "$@" -e "$ncp_pattern"
}

case "${0##*/}" in
    native-package-current.sh)
        case "$1" in
            pattern) shift; native_current_pattern "$@" ;;
            names) shift; native_current_query "$@" ;;
            *) exit 2 ;;
        esac ;;
esac
