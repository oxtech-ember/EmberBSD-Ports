# SPDX-License-Identifier: BSD-2-Clause
# Compiler-free metadata and source-integrity goals do not need an executable.
# A mixed request retains the normal compiler check: `all fetch` must not turn
# a build into a metadata-only query.
_EMBER_COMPILER_FREE_GOALS=no
.if !empty(.TARGETS) && empty(.TARGETS:Nshow-var:Nshow-vars:Nfetch:Nchecksum)
_EMBER_COMPILER_FREE_GOALS=yes
.endif
