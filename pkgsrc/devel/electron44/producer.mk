# Draft producer binding: inputs are explicitly prepared source trees.
# build-electron.py owns source verification, locks, tool selection and GN.

EMBERBSD_ELECTRON_SDK_SOURCE?=	${EMBERBSD_SDK_SOURCE:U}
EMBERBSD_ELECTRON_HOST_PREFIX?=	${EMBERBSD_HOST_PREFIX:U}
EMBERBSD_ELECTRON_PYTHON?=	${EMBERBSD_CROSS_BUILD_PYTHON:U}
EMBERBSD_ELECTRON_SYSROOT?=	${EMBERBSD_CROSS_SYSROOT:U}
EMBERBSD_ELECTRON_TARGET?=	${EMBERBSD_CROSS_TARGET:U}
EMBERBSD_ELECTRON_JOBS?=	${MAKE_JOBS:U}

# Required paths are deliberately not guessed from the package work directory.
# The selected workspace and work tree may be reused by the caller.
_EMBER_ELECTRON_REQUIRED= WORKSPACE PORTS_SOURCE SDK_SOURCE HOST_PREFIX \
	COMPILER_PREFIX SYSROOT WORK GIT LOCK_ROOT LINK_CONTEXT TARGET PYTHON \
	NODE_SOURCE NODE_PKGSRC V8_SOURCE V8_PORTS_SOURCE V8_PKGSRC

_EMBER_ELECTRON_ARGS= \
	--workspace ${EMBERBSD_ELECTRON_WORKSPACE:Q} \
	--ports-source ${EMBERBSD_ELECTRON_PORTS_SOURCE:Q} \
	--sdk-source ${EMBERBSD_ELECTRON_SDK_SOURCE:Q} \
	--host-prefix ${EMBERBSD_ELECTRON_HOST_PREFIX:Q} \
	--compiler-prefix ${EMBERBSD_ELECTRON_COMPILER_PREFIX:Q} \
	--sysroot ${EMBERBSD_ELECTRON_SYSROOT:Q} \
	--work ${EMBERBSD_ELECTRON_WORK:Q} \
	--git ${EMBERBSD_ELECTRON_GIT:Q} \
	--lock-root ${EMBERBSD_ELECTRON_LOCK_ROOT:Q} \
	--link-context ${EMBERBSD_ELECTRON_LINK_CONTEXT:Q} \
	--target ${EMBERBSD_ELECTRON_TARGET:Q} \
	--node-source ${EMBERBSD_ELECTRON_NODE_SOURCE:Q} \
	--node-pkgsrc ${EMBERBSD_ELECTRON_NODE_PKGSRC:Q} \
	--v8-source ${EMBERBSD_ELECTRON_V8_SOURCE:Q} \
	--v8-ports-source ${EMBERBSD_ELECTRON_V8_PORTS_SOURCE:Q} \
	--v8-pkgsrc ${EMBERBSD_ELECTRON_V8_PKGSRC:Q}

# Omission delegates the default to the SDK's shared CPU resolver.
.if !empty(EMBERBSD_ELECTRON_JOBS:U)
_EMBER_ELECTRON_ARGS+= --jobs ${EMBERBSD_ELECTRON_JOBS:Q}
.endif

# Names match the controller CLI, with underscores translated to hyphens.
.for _ember_key in \
	COMPILER_FAMILY HOST_COMPILER_FAMILY MACOS_SDK XCODE_VERSION_PLIST \
	GCC_OS_TOOLS TARGET_RUNTIME_STAGE TARGET_RUNTIME_BASE \
	HOST_RUNTIME_ROOT PROTOC_RUNTIME_VIEW HOST_BUILDLINK_PKGSRC \
	HOST_BUILDLINK_STAGE_ROOT HOST_BUILDLINK_BASE_MAKECONF \
	HOST_BUILDLINK_BMAKE_MK PROTOBUF_SOURCE PROTOBUF_PORTS_SOURCE \
	PROTOBUF_ARCHIVE PROTOBUF_PATCH GYP_SOURCE GYP_PKGSRC \
	PERFETTO_SOURCE PERFETTO_PORTS_SOURCE PERFETTO_ARCHIVE \
	PERFETTO_PATCH V8_METAGEN_LIBCLANG_SO V8_METAGEN_BINDINGS_DIR \
	V8_METAGEN_RUNTIME_VIEW HOST_TOOL_RUNTIME_VIEW MACOS_MINIMUM \
	GCC_PLATFORM_REASON
.if !empty(EMBERBSD_ELECTRON_${_ember_key}:U)
_EMBER_ELECTRON_ARGS+= --${_ember_key:tl:S/_/-/g} ${EMBERBSD_ELECTRON_${_ember_key}:Q}
.endif
.endfor

.for _ember_key in \
	PERFETTO_SCOPED_RUNTIME NODE_SCOPED_RUNTIME SHARED_UNDICI \
	SHARED_ABSEIL SHARED_ICU SHARED_RE2
.if ${EMBERBSD_ELECTRON_${_ember_key}:Uno} == "yes"
_EMBER_ELECTRON_ARGS+= --${_ember_key:tl:S/_/-/g}
.elif ${EMBERBSD_ELECTRON_${_ember_key}:Uno} != "no"
.error EMBERBSD_ELECTRON_${_ember_key} must be yes or no
.endif
.endfor

.if !empty(EMBERBSD_ELECTRON_KEEP_GOING:U)
_EMBER_ELECTRON_BUILD_ARGS+= --keep-going ${EMBERBSD_ELECTRON_KEEP_GOING:Q}
.endif

.PHONY: ember-electron-check-inputs
ember-electron-check-inputs:
.for _ember_input in ${_EMBER_ELECTRON_REQUIRED}
.if empty(EMBERBSD_ELECTRON_${_ember_input}:U)
	${FAIL_MSG} "Set EMBERBSD_ELECTRON_${_ember_input}"
.endif
.endfor

# A partial configuration is not removed or silently regenerated.
do-configure: ember-electron-check-inputs
	${RUN}if ${TEST} -f ${EMBERBSD_ELECTRON_WORK:Q}/configuration.json; then \
		:; \
	elif ${TEST} -e ${EMBERBSD_ELECTRON_WORK:Q}; then \
		${ERROR_MSG} "Electron work exists without configuration.json; preserve it for diagnosis"; exit 1; \
	else \
		${EMBERBSD_ELECTRON_PYTHON:Q} -B -S ${FILESDIR:Q}/build-electron.py configure ${_EMBER_ELECTRON_ARGS}; \
	fi

do-build: ember-electron-check-inputs
	${RUN}${EMBERBSD_ELECTRON_PYTHON:Q} -B -S ${FILESDIR:Q}/build-electron.py build ${_EMBER_ELECTRON_ARGS} ${_EMBER_ELECTRON_BUILD_ARGS}

# Installation is a separate operation on the producer's own out/dist.zip.
_EMBER_ELECTRON_INSTALL_ARGS= \
	--sdk-source ${EMBERBSD_ELECTRON_SDK_SOURCE:Q} \
	--work ${EMBERBSD_ELECTRON_WORK:Q} \
	--destdir ${DESTDIR:Q} \
	--prefix ${PREFIX:Q} \
	--target ${EMBERBSD_ELECTRON_TARGET:Q} \
	--lock-root ${EMBERBSD_ELECTRON_LOCK_ROOT:Q}

INSTALLATION_DIRS+= bin lib
GENERATE_PLIST= ${EMBERBSD_ELECTRON_PYTHON:Q} -B -S ${FILESDIR:Q}/install-runtime.py plist ${_EMBER_ELECTRON_INSTALL_ARGS};

do-install: ember-electron-check-inputs
	${RUN}${EMBERBSD_ELECTRON_PYTHON:Q} -B -S ${FILESDIR:Q}/install-runtime.py install ${_EMBER_ELECTRON_INSTALL_ARGS}
