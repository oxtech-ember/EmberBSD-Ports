#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
set -eu
cd "$(dirname "$0")"

dependencies=$(/usr/bin/env -i PATH=/bin:/usr/bin /usr/bin/ldd ./nss-runtime-smoke)
printf '%s\n' "$dependencies" | grep -F '/usr/pkg/lib/nss/' | grep -F 'libnss3.so' >/dev/null
printf '%s\n' "$dependencies" | grep -F '/usr/pkg/lib/nss/' | grep -F 'libnssutil3.so' >/dev/null
printf '%s\n' "$dependencies" | grep -F '/usr/pkg/lib/nspr/' | grep -F 'libnspr4.so' >/dev/null
if printf '%s\n' "$dependencies" | grep -F 'libgcc_s.so.1' >/dev/null; then
    printf '%s\n' "$dependencies" | grep -F '/usr/pkg/gcc16/lib/' | grep -F 'libgcc_s.so.1' >/dev/null
fi

exec /usr/bin/env -i PATH=/bin:/usr/bin ./nss-runtime-smoke
