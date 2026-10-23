# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); use the matching generator on the build host.
# Consumers include this file only when they generate protobuf source files.
.if !defined(PROTOBUF_HOST_PROTOC_MK)
PROTOBUF_HOST_PROTOC_MK:=

.include "../../mk/bsd.prefs.mk"
USE_TOOLS+=	digest

.if defined(EMBERBSD_BUILD_PROTOC)
.  if empty(EMBERBSD_BUILD_PROTOC:M/*) || !exists(${EMBERBSD_BUILD_PROTOC})
PKG_FAIL_REASON+= "EMBERBSD_BUILD_PROTOC must name an existing absolute host executable"
.  endif
.  if !defined(EMBERBSD_BUILD_PROTOC_SHA256)
PKG_FAIL_REASON+= "Set EMBERBSD_BUILD_PROTOC_SHA256 to the verified host executable hash"
.  endif
PROTOC_FOR_BUILD=	${EMBERBSD_BUILD_PROTOC}
.else
.  if defined(EMBERBSD_BUILD_PROTOC_SHA256)
PKG_FAIL_REASON+= "EMBERBSD_BUILD_PROTOC_SHA256 requires EMBERBSD_BUILD_PROTOC"
.  endif
TOOL_DEPENDS+=	protobuf-36.2{,nb[0-9]*}:../../devel/protobuf
PROTOC_FOR_BUILD=	${TOOLBASE}/bin/protoc
.endif

# Dependencies provide the default native generator before this check runs.
# The explicit provider is never represented as a registered package.
pre-configure: protobuf-host-tool-check
.PHONY: protobuf-host-tool-check
protobuf-host-tool-check:
.if defined(EMBERBSD_BUILD_PROTOC)
	${RUN} ember_protoc_expected=${EMBERBSD_BUILD_PROTOC_SHA256:U:Q}; \
	    case "$$ember_protoc_expected" in *[!0-9a-f]*|'') exit 1;; esac; \
	    test "$${#ember_protoc_expected}" -eq 64 && \
	    test "$$(${TOOLS_DIGEST} SHA256 < ${PROTOC_FOR_BUILD:Q})" = "$$ember_protoc_expected"
.endif
	${RUN} test -x ${PROTOC_FOR_BUILD:Q} && \
	    ember_protoc_version=$$(${PROTOC_FOR_BUILD:Q} --version) && \
	    test "$$ember_protoc_version" = 'libprotoc 36.2'

CONFIGURE_ENV+=	PROTOC=${PROTOC_FOR_BUILD:Q}
MAKE_ENV+=	PROTOC=${PROTOC_FOR_BUILD:Q}
CMAKE_CONFIGURE_ARGS+=	-DProtobuf_PROTOC_EXECUTABLE=${PROTOC_FOR_BUILD:Q}
.endif
