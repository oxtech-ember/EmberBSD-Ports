#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Preserve upstream licenses and provenance, and
# install the legacy lz4c name and lz4frame_static.h as the upstream Makefile does.
set -eu
[ "$#" = 3 ] || exit 2
source=$1 prefix=$2 recipe=$3
mkdir -p "$prefix/share/licenses/lz4"
cp "$source/lib/LICENSE" "$prefix/share/licenses/lz4/LICENSE.BSD"
cp "$source/programs/COPYING" "$prefix/share/licenses/lz4/COPYING.GPL2"
cp "$recipe/files/SOURCE" "$prefix/share/licenses/lz4/SOURCE"
ln -sf lz4 "$prefix/bin/lz4c"
ln -sf lz4.1 "$prefix/man/man1/lz4c.1"
cp "$source/lib/lz4frame_static.h" "$prefix/include/lz4frame_static.h"
