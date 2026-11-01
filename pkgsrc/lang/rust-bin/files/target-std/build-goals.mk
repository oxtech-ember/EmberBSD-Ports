# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# Classify source and metadata-only goals before requiring Rust build inputs.
.if !defined(_EMBERBSD_RUST_TARGET_STD_BUILD_GOALS_MK)
_EMBERBSD_RUST_TARGET_STD_BUILD_GOALS_MK= yes

_EMBERBSD_RUST_TARGET_STD_BUILD_GOALS:= ${.TARGETS}
.for _rust_source_goal in fetch checksum checksum-phase makesum makepatchsum distinfo \
    fetch-list fetch-list-one-package fetch-list-recursive mirror-distfiles \
    show-distfiles depends-fetch depends-checksum show-var show-vars
_EMBERBSD_RUST_TARGET_STD_BUILD_GOALS:= ${_EMBERBSD_RUST_TARGET_STD_BUILD_GOALS:N${_rust_source_goal}}
.endfor

# Empty/default, build, mixed, and unknown goals still require every build input.
_EMBERBSD_RUST_NEEDS_BUILD_INPUTS= yes
.if !empty(.TARGETS) && empty(_EMBERBSD_RUST_TARGET_STD_BUILD_GOALS)
_EMBERBSD_RUST_NEEDS_BUILD_INPUTS= no
.endif

.endif
