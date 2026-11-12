# SPDX-License-Identifier: BSD-2-Clause
# Only pure pkgsrc variable queries defer compiler availability checks.
_EMBER_METADATA_ONLY=no
.if !empty(.TARGETS) && empty(.TARGETS:Nshow-var:Nshow-vars)
_EMBER_METADATA_ONLY=yes
.endif
