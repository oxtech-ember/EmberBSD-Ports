# $NetBSD$
# Origin: EmberBSD (AI-assisted).
#
# Waf cross configuration for the Samba library recipes (devel/talloc,
# databases/tdb). Include after bsd.prefs.mk in cross builds only.
#
# Waf runs its compiled feature probes through --cross-answers. By default
# (EMBERBSD_WAF_ANSWERS_MODE=replay) the answers come from the stored file
# files/cross-answers/PLATFORM.txt of the recipe, and configure fails on a
# probe without an answer; nothing runs on a target and no target, SSH or
# query configuration is needed.
#
# EMBERBSD_WAF_ANSWERS_MODE=capture runs every probe on an EmberBSD target
# through the shared target executor and stores the normalized answers in
# EMBERBSD_WAF_ANSWERS_CAPTURE_DIR/PLATFORM/<category>_<name>.txt. Copy
# reviewed files to the recipe (profiles/common-media/cross/waf-answers.md).

.if !defined(EMBERBSD_WAF_CROSS_MK)
EMBERBSD_WAF_CROSS_MK=	defined

EMBERBSD_WAF_ANSWERS_MODE?=	replay
_EMBER_WAF_PLATFORM=	${CROSS_OPSYS}-${CROSS_OS_VERSION}-${MACHINE_ARCH}
EMBERBSD_WAF_ANSWERS=	${PKGDIR}/files/cross-answers/${_EMBER_WAF_PLATFORM}.txt
_EMBER_WAF_TOOL=	${.CURDIR}/../../devel/talloc/files/waf_answers.py
_EMBER_WAF_WORK=	${WRKDIR}/.cross-answers.txt
_EMBER_WAF_ID=		${_EMBER_WAF_PLATFORM:Q} ${PKGPATH:Q} ${PKGNAME_NOREV:Q}
_EMBER_WAF_RUN=		${TOOL_PYTHONBIN} -B -E -S ${_EMBER_WAF_TOOL}

CONFIGURE_ARGS+=	--cross-compile --cross-answers=${_EMBER_WAF_WORK:Q}
CONFIGURE_ENV+=		PYTHON=${TOOL_PYTHONBIN:Q}

pre-configure: emberbsd-waf-answers
.PHONY: emberbsd-waf-answers

.if ${EMBERBSD_WAF_ANSWERS_MODE} == "replay"
emberbsd-waf-answers:
	${RUN}${RM} -f ${_EMBER_WAF_WORK:Q}
	${RUN}${_EMBER_WAF_RUN} replay ${_EMBER_WAF_ID} ${EMBERBSD_WAF_ANSWERS:Q} ${_EMBER_WAF_WORK:Q}

.elif ${EMBERBSD_WAF_ANSWERS_MODE} == "capture"
# Capture inputs are checked when configure starts, not while the recipe is
# parsed, so fetch, checksum and extract work without a target.
_EMBER_WAF_INPUT_ERRORS=
.for _input in EMBERBSD_CROSS_BUILD_PYTHON EMBERBSD_GI_QUERY_CONFIG
.  if empty(${_input}:M/*) || !empty(${_input}:C/[A-Za-z0-9_.\/-]//g) || !exists(${${_input}})
_EMBER_WAF_INPUT_ERRORS+= ${_input}
.  endif
.endfor
.if empty(EMBERBSD_SDK_SOURCE:M/*) || !empty(EMBERBSD_SDK_SOURCE:C/[A-Za-z0-9_.\/-]//g) || !exists(${EMBERBSD_SDK_SOURCE}/src/emberbsd_sdk/__init__.py)
_EMBER_WAF_INPUT_ERRORS+= EMBERBSD_SDK_SOURCE
.endif
.if empty(EMBERBSD_WAF_ANSWERS_CAPTURE_DIR:M/*) || !empty(EMBERBSD_WAF_ANSWERS_CAPTURE_DIR:C/[A-Za-z0-9_.\/-]//g) || !exists(${EMBERBSD_WAF_ANSWERS_CAPTURE_DIR}/.)
_EMBER_WAF_INPUT_ERRORS+= EMBERBSD_WAF_ANSWERS_CAPTURE_DIR
.endif
.PHONY: emberbsd-waf-inputs
emberbsd-waf-inputs:
.for _input in ${_EMBER_WAF_INPUT_ERRORS}
.  if ${_input} == "EMBERBSD_SDK_SOURCE"
	@${ERROR_MSG} "EMBERBSD_SDK_SOURCE must name an absolute SDK source directory without shell metacharacters"
.  elif ${_input} == "EMBERBSD_WAF_ANSWERS_CAPTURE_DIR"
	@${ERROR_MSG} "EMBERBSD_WAF_ANSWERS_CAPTURE_DIR must name an existing absolute directory without shell metacharacters"
.  else
	@${ERROR_MSG} "${_input} must name an existing absolute file without shell metacharacters"
.  endif
.endfor
.if !empty(_EMBER_WAF_INPUT_ERRORS)
	@${FALSE}
.endif
_EMBER_WAF_QUERY=	${.CURDIR}/../../devel/gobject-introspection/files/target-query.py
_EMBER_WAF_EXECUTOR=	${EMBERBSD_CROSS_BUILD_PYTHON} -E -S ${_EMBER_WAF_QUERY} --execute
_EMBER_WAF_FAILURE=	${WRKDIR}/.waf-query-failure
# Waf answers from the file first and asks the target for every other probe.
# Parallel configure mutates provider files while a query walks them.
CONFIGURE_ARGS+=	--jobs=1
CONFIGURE_ARGS+=	--cross-execute=${_EMBER_WAF_EXECUTOR:Q}
CONFIGURE_ENV+=		EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q}
CONFIGURE_ENV+=		EMBERBSD_GI_TARGET=${MACHINE_ARCH:S/x86_64/amd64/}
CONFIGURE_ENV+=		EMBERBSD_GI_QUERY_CONFIG=${EMBERBSD_GI_QUERY_CONFIG:Q}
CONFIGURE_ENV+=		EMBERBSD_GI_FAILURE_MARKER=${_EMBER_WAF_FAILURE:Q}
emberbsd-waf-answers: emberbsd-waf-inputs
	${RUN}${SETENV} EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q} EMBERBSD_GI_TARGET=${MACHINE_ARCH:S/x86_64/amd64/:Q} EMBERBSD_GI_QUERY_CONFIG=${EMBERBSD_GI_QUERY_CONFIG:Q} ${EMBERBSD_CROSS_BUILD_PYTHON} -E -S ${_EMBER_WAF_QUERY} --check ${WRKDIR} ${CROSS_DESTDIR} ${TOOLDIR}/bin/${MACHINE_GNU_PLATFORM}-readelf ${MACHINE_ARCH:S/x86_64/amd64/:Q}
	${RUN}${RM} -f ${_EMBER_WAF_FAILURE:Q} ${_EMBER_WAF_WORK:Q}
	${RUN}${TOUCH} ${_EMBER_WAF_WORK:Q}
post-configure: emberbsd-waf-capture
.PHONY: emberbsd-waf-capture
emberbsd-waf-capture:
	${RUN}${TEST} ! -e ${_EMBER_WAF_FAILURE:Q} || { ${CAT} ${_EMBER_WAF_FAILURE:Q}; exit 1; }
	${RUN}${_EMBER_WAF_RUN} store ${_EMBER_WAF_ID} ${_EMBER_WAF_WORK:Q} ${EMBERBSD_WAF_ANSWERS_CAPTURE_DIR:Q} ${WRKDIR:Q} ${CROSS_DESTDIR:Q}

.else
emberbsd-waf-answers:
	@${ERROR_MSG} "EMBERBSD_WAF_ANSWERS_MODE must be replay or capture"
	@${FALSE}
.endif

.endif	# EMBERBSD_WAF_CROSS_MK
