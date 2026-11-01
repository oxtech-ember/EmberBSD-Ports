#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Fixture stand-in for the selected SDK's resolve-jobs CLI.
set -eu
while [ "$#" -gt 0 ]; do
    if [ "$1" = --jobs ]; then
        [ "$#" -ge 2 ] || exit 2
        case "$2" in ''|*[!0-9]*|0) exit 2 ;; esac
        echo "$2"
        exit 0
    fi
    shift
done
echo "${CROSS_BULK_TEST_CPUS:-8}"
