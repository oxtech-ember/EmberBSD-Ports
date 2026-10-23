#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
set -eu

: "${BUILD_DIR:?Set BUILD_DIR to an external build directory}"
: "${USB_HEADER:=/usr/include/dev/usb/usb.h}"
: "${CC:=cc}"
: "${CFLAGS:=-O1 -g -ftrivial-auto-var-init=pattern}"
case "$BUILD_DIR" in
/*) ;;
*) echo 'BUILD_DIR must be absolute' >&2; exit 1 ;;
esac

cd "$(dirname "$0")/.."
mkdir -p "$BUILD_DIR/include/dev/usb"
ln -sf "$USB_HEADER" "$BUILD_DIR/include/dev/usb/usb.h"
for payload in payload_*.bin; do
    xxd -i "$payload" "$BUILD_DIR/${payload%.bin}.h"
done
# Use the target USB header with host pthreads and libc. No USB nodes are opened.
# CPPFLAGS and LDFLAGS can select the host OpenSSL installation.
$CC -std=c11 -D_DEFAULT_SOURCE -DGASTER_NETBSD_NATIVE \
    -Wall -Wextra -Wpedantic $CFLAGS ${CPPFLAGS:-} \
    -isystem "$BUILD_DIR/include" -I"$BUILD_DIR" \
    tests/native-backend.c lzfse.c ${LDFLAGS:-} -lcrypto -lpthread \
    -o "$BUILD_DIR/native-backend"

ulimit -c 0
failed=0
for test in timeout timeout-default timeout-limit timeout-overflow timeout-max \
    start create-error success stall join-error spray-reset-default \
    spray-reset-opt-in skip-reset-legacy poll-default poll-opt-in poll-bounds \
    poll-invalid; do
    "$BUILD_DIR/native-backend" "$test" || failed=1
done
exit "$failed"
