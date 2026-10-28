#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# A cross mlir build runs its generators on the build host. Evaluate the
# real recipe under a cross MAKECONF and require native LLVM and mlir
# generators and the host Python, and refusals for missing or target tools.
# NATIVE_MLIR holds native mlir-tblgen, mlir-pdll, mlir-src-sharder,
# mlir-linalg-ods-yaml-gen and mlir-irdl-to-cpp.
# Usage: BMAKE=... cross-inputs.sh PKGSRC MAKECONF NATIVE_MLIR NEW_WORK
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 PKGSRC MAKECONF NATIVE_MLIR NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 native=$3 work=$4
: "${BMAKE:?Set the native BSD make executable}"
for path in "$pkgsrc" "$makeconf" "$native" "$work"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2 ;; esac
done
mkdir "$work"
query() { "$BMAKE" -C "$pkgsrc/lang/mlir" MAKECONF="$makeconf" "$@"; }
query EMBERBSD_MLIR_NATIVE_TOOLS="$native" -V '${PKG_FAIL_REASON}' > "$work/valid.log"
# Shared LLVM host-tool checks in lang/llvm/cross.mk are covered by their own
# tests; this test owns the mlir, Python and native-LLVM-directory inputs.
if grep -qi "mlir\|PYTHON\|NATIVE_TOOLS must" "$work/valid.log"; then
    cat "$work/valid.log"; echo "FAIL: refused"; exit 1
fi
[ -z "$(cat "$work/valid.log")" ] || echo "NOTE: other refusals: $(cat "$work/valid.log")"
query EMBERBSD_MLIR_NATIVE_TOOLS="$native" -V '${EMBERBSD_LLVM_NATIVE_TOOLS}' > "$work/llvm.log"
query EMBERBSD_MLIR_NATIVE_TOOLS="$native" -V '${EMBERBSD_CROSS_BUILD_PYTHON}' > "$work/python.log"
query EMBERBSD_MLIR_NATIVE_TOOLS="$native" -V '${CMAKE_CONFIGURE_ARGS}' | tr ' ' '\n' > "$work/cmake.log"
llvm=$(cat "$work/llvm.log") python=$(cat "$work/python.log")
for arg in "-DLLVM_TABLEGEN_EXE=$llvm/llvm-tblgen" "-DPython3_EXECUTABLE=$python" \
    "-DMLIR_TABLEGEN=$native/mlir-tblgen" "-DMLIR_PDLL_TABLEGEN=$native/mlir-pdll" \
    "-DMLIR_SRC_SHARDER_TABLEGEN=$native/mlir-src-sharder" \
    "-DMLIR_LINALG_ODS_YAML_GEN=$native/mlir-linalg-ods-yaml-gen" \
    "-DMLIR_IRDL_TO_CPP=$native/mlir-irdl-to-cpp"; do
    grep -qxF -- "$arg" "$work/cmake.log" || { echo "FAIL: missing $arg"; exit 1; }
done
# An unset, partial or non-host selection is refused.
query EMBERBSD_MLIR_NATIVE_TOOLS= -V '${PKG_FAIL_REASON}' > "$work/unset.log" 2>&1
grep -q 'EMBERBSD_MLIR_NATIVE_TOOLS must select' "$work/unset.log" || { echo 'FAIL: unset accepted'; exit 1; }
mkdir "$work/partial"
ln -s "$native/mlir-tblgen" "$work/partial/mlir-tblgen"
query EMBERBSD_MLIR_NATIVE_TOOLS="$work/partial" -V '${PKG_FAIL_REASON}' > "$work/partial.log" 2>&1
grep -q 'lacks the native mlir-pdll' "$work/partial.log" || { echo 'FAIL: partial accepted'; exit 1; }
query EMBERBSD_MLIR_NATIVE_TOOLS=/usr/bin -V '${PKG_FAIL_REASON}' > "$work/wrong.log" 2>&1
grep -q 'mlir-tblgen must execute on the build host' "$work/wrong.log" || { echo 'FAIL: non-host accepted'; exit 1; }
echo 'PASS: cross mlir runs native LLVM and mlir generators and host Python'
