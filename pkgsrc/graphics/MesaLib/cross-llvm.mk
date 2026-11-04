# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Select and validate the host helper for target LLVM metadata.
.if !defined(EMBERBSD_GRAPHICS_LLVM_CONFIG)
# Snapshot a caller's value before the automatic helper include assigns
# LLVM_CONFIG_PATH. The helper path is recursive and target platform values
# may still be finalized after the make configuration is parsed.
.if defined(LLVM_CONFIG_PATH) && empty(.MAKEOVERRIDES:MLLVM_CONFIG_PATH)
_EMBERBSD_GRAPHICS_LLVM_PRIOR_DEFINED:= yes
_EMBERBSD_GRAPHICS_LLVM_PRIOR_CONFIG:= ${LLVM_CONFIG_PATH}
.else
_EMBERBSD_GRAPHICS_LLVM_PRIOR_DEFINED:= no
.endif
.include "${PKGSRCDIR}/lang/llvm/cross-llvm-config.mk"
EMBERBSD_GRAPHICS_LLVM_CONFIG= ${EMBERBSD_CROSS_LLVM_CONFIG}
.elif defined(EMBERBSD_GRAPHICS_LLVM_CONFIG)
# An explicitly selected graphics helper still rejects a prior caller value.
.if defined(LLVM_CONFIG_PATH) && empty(.MAKEOVERRIDES:MLLVM_CONFIG_PATH)
_EMBERBSD_GRAPHICS_LLVM_PRIOR_DEFINED:= yes
_EMBERBSD_GRAPHICS_LLVM_PRIOR_CONFIG:= ${LLVM_CONFIG_PATH}
.else
_EMBERBSD_GRAPHICS_LLVM_PRIOR_DEFINED:= no
.endif
.endif
.if defined(EMBERBSD_GRAPHICS_LLVM_CONFIG)
LLVM_CONFIG_PATH= ${EMBERBSD_GRAPHICS_LLVM_CONFIG}
.endif
# Source fetch/checksum does not consume target LLVM metadata. Keep the
# selection and version contract at the first consuming configure phase.
pre-configure: emberbsd-graphics-llvm-input-check
.PHONY: emberbsd-graphics-llvm-input-check
.if defined(EMBERBSD_CROSS_LLVM_CONFIG) && ${EMBERBSD_GRAPHICS_LLVM_CONFIG} == ${EMBERBSD_CROSS_LLVM_CONFIG}
emberbsd-graphics-llvm-input-check: emberbsd-cross-llvm-config
.endif
emberbsd-graphics-llvm-input-check:
	${RUN} ember_graphics_llvm=${EMBERBSD_GRAPHICS_LLVM_CONFIG:U:Q}; \
	${TEST} -n "$$ember_graphics_llvm" || { \
	    echo 'Cross Mesa requires EMBERBSD_GRAPHICS_LLVM_CONFIG from the target metadata helper' >&2; exit 1; \
	}; \
	case "$$ember_graphics_llvm" in /*/llvm-config) ;; \
	*) echo 'The graphics LLVM helper must be an absolute installed-metadata llvm-config' >&2; exit 1;; esac; \
	ember_graphics_prior=${_EMBERBSD_GRAPHICS_LLVM_PRIOR_CONFIG:U:Q}; \
	if test ${_EMBERBSD_GRAPHICS_LLVM_PRIOR_DEFINED:Uno:Q} = yes && \
	    test "$$ember_graphics_prior" != "$$ember_graphics_llvm"; then \
	    echo 'Mesa rejects an earlier conflicting LLVM_CONFIG_PATH' >&2; exit 1; \
	fi; \
	ember_graphics_route=${LLVM_CONFIG_PATH:U:Q}; \
	${TEST} "$$ember_graphics_route" = "$$ember_graphics_llvm" || { \
	    echo 'Mesa rejects an overridden LLVM_CONFIG_PATH' >&2; exit 1; \
	}; \
	${TEST} -x "$$ember_graphics_llvm" || { \
	    echo 'The graphics LLVM helper must be an installed-metadata llvm-config for LLVM 23.1.4' >&2; exit 1; \
	}; \
	if test "$$ember_graphics_llvm" = ${EMBERBSD_CROSS_LLVM_CONFIG:U:Q}; then \
	    ${TEST} "$$($$ember_graphics_llvm --version)" = 23.1.4 || { \
	        echo 'The graphics LLVM helper must report LLVM 23.1.4' >&2; exit 1; \
	    }; \
	else \
	    ${EMBERBSD_CROSS_BUILD_PYTHON:Q} -B ${PKGSRCDIR:Q}/lang/llvm/files/cross-llvm-config.py \
	        --validate "$$ember_graphics_llvm" ${CROSS_DESTDIR:Q}; \
	fi
