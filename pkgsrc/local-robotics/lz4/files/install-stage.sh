#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Preserve upstream licenses and provenance.
set -eu
[ "$#" = 3 ] || exit 2
source=$1 prefix=$2 recipe=$3
mkdir -p "$prefix/share/licenses/lz4"
cp "$source/lib/LICENSE" "$prefix/share/licenses/lz4/LICENSE.BSD"
cp "$source/programs/COPYING" "$prefix/share/licenses/lz4/COPYING.GPL2"
cp "$recipe/files/SOURCE" "$prefix/share/licenses/lz4/SOURCE"
