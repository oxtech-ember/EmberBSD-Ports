# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Finite selected-shell routing controls.
# The caller supplies route.mk from the checked policy and tool-map source.
.include "route.mk"

EMPTY=
NONEMPTY= plain value
OPTION= -n
BACKSLASH= first\nsecond
QUERY_EMPTY=
QUERY_WORD= plain
QUERY_SPACE= space value
QUERY_BACKSLASH= first\nsecond
QUERY_QUOTE= double"quote'single
QUERY_OPTION= -n

.PHONY: old-empty reference-empty reference-word reference-option reference-backslash
.PHONY: new-empty new-word new-option new-backslash nested-empty show-var
.PHONY: new-true new-false new-test new-test-false new-bracket
old-empty:
	@echo ${EMPTY:Q}
reference-empty:
	@echo ${EMPTY:Q};
reference-word:
	@echo ${NONEMPTY:Q};
reference-option:
	@echo ${OPTION:Q};
reference-backslash:
	@echo ${BACKSLASH:Q};
new-empty:
	@${ECHO} ${EMPTY:Q}
new-word:
	@${ECHO} ${NONEMPTY:Q}
new-option:
	@${ECHO} ${OPTION:Q}
new-backslash:
	@${ECHO} ${BACKSLASH:Q}
nested-empty:
	@+${BOUND_MAKE} -f echo.mk show-var VARNAME=EMPTY
show-var:
	@${ECHO} ${${VARNAME}:Q}
new-true:
	@${TOOLS_PLATFORM.true}
new-false:
	@${TOOLS_PLATFORM.false}
new-test:
	@${TOOLS_PLATFORM.test} -n value
new-test-false:
	@${TOOLS_PLATFORM.test} -n ""
new-bracket:
	@${TOOLS_PLATFORM.[} -n value ]

# Preserve the canonical pkgsrc show-vars-eval recipe for the diagnostic.
# The caller supplies fixed NAME:NAME pairs. Never source its output.
# This legacy echo recipe is a causal negative for literal backslash data.
.PHONY: show-vars-eval
show-vars-eval:
.for var in ${VARS}
	@${ECHO} ${var:C/^.*://}="${${var:C/:.*$//}:Q}"
.endfor
