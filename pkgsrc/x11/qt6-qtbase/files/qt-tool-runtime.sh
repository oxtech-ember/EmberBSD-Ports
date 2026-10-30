#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run a Qt host tool with the selected view.
set -eu
: "${QT_NATIVE_RUNTIME_PYTHON:?}" "${QT_NATIVE_RUNTIME_LAUNCHER:?}" "${QT_NATIVE_RUNTIME_VIEW:?}"
exec "$QT_NATIVE_RUNTIME_PYTHON" -I -S "$QT_NATIVE_RUNTIME_LAUNCHER" --runtime-view "$QT_NATIVE_RUNTIME_VIEW" -- "$@"
