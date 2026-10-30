#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Run before every push: no commit in BASE..HEAD drops an export.conf entry,
# and a fresh export of the checkout applies every entry and keeps every
# recipe and file. PY names the Python interpreter from Ports or the SDK;
# EXPORT_TEST_GIT and EXPORT_TEST_PATCH default to git and gpatch on PATH.
# Usage: PY=python3 scripts/tests/pre-push.sh BASE NEW_WORK
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 BASE NEW_WORK" >&2; exit 2; }
EXPORT_TEST_GIT=${EXPORT_TEST_GIT:-$(command -v git)}
EXPORT_TEST_PATCH=${EXPORT_TEST_PATCH:-$(command -v gpatch)}
export EXPORT_TEST_GIT EXPORT_TEST_PATCH
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
[ -z "$(git -C "$root" status --porcelain --untracked-files=no -- pkgsrc profiles scripts)" ] ||
    { echo "pre-push: commit or stash tracked changes first; the export uses the checkout" >&2; exit 1; }
"$PY" -B "$root/scripts/tests/export-conf-history.py" --root "$root" "$1" HEAD
sh "$root/scripts/tests/recipe-host-variables.sh"
sh "$root/scripts/tests/github-commit-distfiles.sh"
sh "$root/scripts/tests/qt-host-tool-depends.sh" "${BMAKE:-bmake}"
sh "$root/scripts/tests/export-composition.sh" "$2"
sh "$root/scripts/tests/native-profile-jobs.sh" "${BMAKE:-bmake}" "$2/export"
sh "$root/scripts/tests/freestanding-native-tools.sh" "${BMAKE:-bmake}" "$2/export"
sh "$root/scripts/tests/cross-target-strings.sh" "${BMAKE:-bmake}" "$2/export"
sh "$root/scripts/tests/cross-runtime-tool-values.sh" "${BMAKE:-bmake}" "$2/export"
echo "PASS: pre-push export checks"
