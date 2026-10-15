#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Preserve upstream and private-vendor notices.
set -eu
[ "$#" = 3 ] || exit 2
source=$1 prefix=$2 recipe=$3
licenses=$prefix/share/licenses/gtsam
mkdir -p "$licenses/ccolamd" "$licenses/cephes"
cp "$source/LICENSE" "$source/LICENSE.BSD" "$recipe/files/SOURCE" "$licenses/"
cp "$source/gtsam/3rdparty/CCOLAMD/Doc/License.txt" "$licenses/ccolamd/"
cp "$source/gtsam/3rdparty/SuiteSparse_config/README.txt" "$licenses/ccolamd/SuiteSparse-README.txt"
cp "$source/gtsam/3rdparty/cephes/LICENSE.txt" "$source/gtsam/3rdparty/cephes/README.md" "$licenses/cephes/"
cp "$source/gtsam/3rdparty/Spectra/SymEigsSolver.h" "$licenses/Spectra-SymEigsSolver.h"
cp "$source/gtsam/3rdparty/Eigen/COPYING.MPL2" "$licenses/Spectra-MPL-2.0.txt"
cp "$source/gtsam/3rdparty/cephes/cephes/lanczos.c" "$source/gtsam/3rdparty/cephes/cephes/igami.c" "$licenses/cephes/"
