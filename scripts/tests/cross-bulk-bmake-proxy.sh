#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Proxy used by cross-bulk fixtures to supply the selected SDK job resolver.
set -eu
: "${CROSS_BULK_TEST_REAL_BMAKE:?set fixture bmake path}"
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
for arg do
    if [ "$arg" = VARNAME=PKG_ADMIN ]; then
        # Use pkgsrc's own version ordering, including nb revisions, when
        # the fixture has selected a real SDK prefix for cross-bulk.
        python=${CROSS_BULK_TEST_HOST_PYTHON:-${TEST_PYTHON:-}}
        admin=${CROSS_BULK_TEST_PKG_ADMIN:-}
        case "$python" in */bin/*) admin=${admin:-${python%/bin/*}/sbin/pkg_admin} ;; esac
        if [ -n "$admin" ] && [ -x "$admin" ]; then printf '%s\n' "$admin"; exit 0; fi
    fi
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
