#!/bin/sh
# Run from the Telegram recipe in a prepared pkgsrc tree with SDK bmake and MAKECONF.
set -eu
recipe=${1:-Makefile}
diagnostic() {
    bmake -f "$recipe" TELEGRAM_API_TEST=YES TELEGRAM_API_ID=1 TELEGRAM_API_HASH=fixture "$@"
}
args=$(diagnostic -V CMAKE_CONFIGURE_ARGS)
case "$args" in *-DTDESKTOP_API_TEST=ON*) ;; *) echo 'Expected diagnostic identity' >&2; exit 1;; esac
case "$args" in *-DTDESKTOP_API_ID=*|*-DTDESKTOP_API_HASH=*) echo 'Unexpected release inputs in diagnostic mode' >&2; exit 1;; esac
for stage in pre-install pre-package; do
    if log=$(diagnostic "$stage" 2>&1); then
        echo "Diagnostic build accepted $stage" >&2
        exit 1
    fi
    case "$log" in *'TELEGRAM_API_TEST is for local diagnostics only'*) ;; *) echo "$log" >&2; exit 1;; esac
done
echo 'PASS: diagnostic identity selected and both packaging stages refused'
