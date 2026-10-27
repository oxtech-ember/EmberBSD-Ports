#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Preserve upstream licenses and provenance.
set -eu
[ "$#" = 3 ] || exit 2
source=$1 prefix=$2 recipe=$3
mkdir -p "$prefix/share/licenses/flann"
cp "$source/COPYING" "$prefix/share/licenses/flann/LICENSE"
cp "$recipe/files/SOURCE" "$prefix/share/licenses/flann/SOURCE"
