#!/bin/sh
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors
set -eu
[ "$#" -le 1 ] || { echo 'Usage: test-armv7.sh [ABS_PREFIX]' >&2; exit 2; }
prefix=${1:-/usr/pkg}
case "$prefix" in /*) ;; *) echo 'Use an absolute prefix.' >&2; exit 2 ;; esac
export LD_LIBRARY_PATH=$prefix/lib
testdir=$prefix/libexec/ember-dsp
for program in fftw-double fftw-float liquid-contract backend-selection; do
    linked=$(ldd "$testdir/$program")
    printf '%s\n' "$linked"
    if printf '%s\n' "$linked" | grep -q 'not found'; then exit 1; fi
    case "$program" in
        fftw-double) libraries='fftw3_threads fftw3' ;;
        fftw-float) libraries='fftw3f_threads fftw3f' ;;
        liquid-contract) libraries='liquid fftw3f' ;;
        backend-selection) libraries='fftw3f' ;;
    esac
    for library in $libraries; do
        printf '%s\n' "$linked" | grep -F "$prefix/lib/lib$library.so" >/dev/null || {
            echo "Missing selected library: $library" >&2; exit 1;
        }
    done
done
for name in fftw-double fftw-float backend-selection; do "$testdir/$name"; done
for name in filter resample modem spectrum; do "$testdir/liquid-contract" "$name"; done
