#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Use the package-owned license installation.
set -eu
ports=$(CDPATH= cd "$(dirname "$0")/../.." && pwd -P)
exec sh "$ports/pkgsrc/local-robotics/gtsam/files/install-licenses.sh" "$@"
