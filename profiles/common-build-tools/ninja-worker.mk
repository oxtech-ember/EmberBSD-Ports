# SPDX-License-Identifier: BSD-2-Clause
# Ports gives each adaptive cross-bulk source worker one CPU allocation.
_EMBER_NINJA=       ninja
_EMBER_NINJA_JOBS=  -j ${_MAKE_JOBS_N:U1}
.if defined(EMBERBSD_BULK_NINJA_BUDGET) && defined(EMBERBSD_BULK_NINJA_RUNNER)
_EMBER_NINJA=       ${EMBERBSD_HOST_PYTHON:Q} -B -E -S ${EMBERBSD_BULK_NINJA_RUNNER:Q} run \
                    ${EMBERBSD_BULK_NINJA_BUDGET:Q} ${_MAKE_JOBS_N:U1} \
                    "${MAKE_JOBS_SAFE:Uyes:tl}" ${MAKE_JOBS.${PKGPATH}:Dyes:Uno} ${EMBERBSD_SDK_SOURCE:Q} ninja
_EMBER_NINJA_JOBS=  # the runner supplies the worker's budget
.endif
