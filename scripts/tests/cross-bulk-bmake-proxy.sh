#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Proxy used by cross-bulk fixtures to supply the selected SDK job resolver.
set -eu
: "${CROSS_BULK_TEST_REAL_BMAKE:?set fixture bmake path}"
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
for arg do
    if [ "$arg" = "VARNAMES=EMBERBSD_HOST_PYTHON EMBERBSD_SDK_SOURCE" ]; then
        if [ -n "${CROSS_BULK_TEST_HOST_PYTHON:-}" ] &&
            [ -n "${CROSS_BULK_TEST_SDK_SOURCE:-}" ]; then
            printf '%s\n' "$CROSS_BULK_TEST_HOST_PYTHON" "$CROSS_BULK_TEST_SDK_SOURCE"
            exit 0
        fi
        printf '%s\n' "$ports/scripts/tests/cross-bulk-resolve-jobs.sh" "$ports"
        exit 0
    fi
done
exec "$CROSS_BULK_TEST_REAL_BMAKE" "$@"
