#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Select an explicit SDK API1 source and the common Python 3.15 host runtime.
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
exec "${PYTHON:-python3.15}" -B "$base/build-llvm-config.py" "$@"
