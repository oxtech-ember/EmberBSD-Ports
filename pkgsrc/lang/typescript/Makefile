# $NetBSD$

DISTNAME=	typescript-7.0.2
PKGREVISION=	3
CATEGORIES=	lang
TYPESCRIPT_REVISION=	2bd066d87f5bafd315be9f40889d0a60b9e58e0b
DISTFILES=	typescript-go-${TYPESCRIPT_REVISION}.tar.gz ${DISTNAME}.tgz
SITES.typescript-go-${TYPESCRIPT_REVISION}.tar.gz= -https://github.com/microsoft/typescript-go/archive/${TYPESCRIPT_REVISION}.tar.gz
SITES.${DISTNAME}.tgz=	https://registry.npmjs.org/typescript/-/
WRKSRC=		${WRKDIR}/typescript-go-${TYPESCRIPT_REVISION}
EXTRACT_DIR.${DISTNAME}.tgz=	${WRKSRC}/npm
EXTRACT_ONLY=	typescript-go-${TYPESCRIPT_REVISION}.tar.gz ${DISTNAME}.tgz

MAINTAINER=	oxtech-ember@users.noreply.github.com
HOMEPAGE=	https://www.typescriptlang.org/
COMMENT=	TypeScript compiler with a source-built native backend
LICENSE=	apache-2.0 AND modified-bsd AND 2-clause-bsd AND mit AND unicode AND w3c AND cc-by-v4.0

DEPENDS+=	nodejs>=26.13.0<27:../../lang/nodejs
USE_LANGUAGES=	# none
REPLACE_NODEJS=	npm/package/bin/tsc
GO_BUILD_PATTERN=	./cmd/tsgo
GOFLAGS+=	-tags=noembed
GO_LDFLAGS=	-X github.com/microsoft/typescript-go/internal/core.version=${PKGVERSION_NOREV}
GOFLAGS+=	-ldflags=${GO_LDFLAGS:Q}
MAKE_ENV+=	CGO_ENABLED=0

.include "../../lang/go/go-vars.mk"
.include "../../mk/bsd.prefs.mk"

_TYPESCRIPT_NODE_ARCH.aarch64=	arm64
_TYPESCRIPT_NODE_ARCH.x86_64=	x64
_TYPESCRIPT_NODE_ARCH.i386=	ia32
_TYPESCRIPT_NODE_ARCH.earmv6hf=	arm
_TYPESCRIPT_NODE_ARCH.earmv7hf=	arm
_TYPESCRIPT_NODE_ARCH.powerpc64le=	ppc64
TYPESCRIPT_NODE_ARCH?=	${_TYPESCRIPT_NODE_ARCH.${MACHINE_ARCH}:U${MACHINE_ARCH}}
TYPESCRIPT_NPM_PLATFORM=	${LOWER_OPSYS}-${TYPESCRIPT_NODE_ARCH}
TYPESCRIPT_PLATFORM_DIR=	lib/node_modules/@typescript/typescript-${TYPESCRIPT_NPM_PLATFORM}
PLIST_SUBST+=	TYPESCRIPT_NPM_PLATFORM=${TYPESCRIPT_NPM_PLATFORM}
INSTALLATION_DIRS=	bin lib/node_modules/typescript ${TYPESCRIPT_PLATFORM_DIR}/lib

# Match upstream's native npm layout. Node locates this source-built binary
# through the ordinary platform package; no optional binary is downloaded.
do-test:
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
	${FAIL_MSG} "Run the TypeScript CLI on its selected target; target binaries do not run on the build host"
.else
	${SETENV} ${TEST_ENV} ${TOOL_PYTHONBIN} -B -I -S ${FILESDIR}/smoke.py \
	    --module ${WRKSRC:Q}/npm/package \
	    --binary ${WRKDIR:Q}/.gopath/${GOPATH_BIN}/tsgo \
	    --libs ${WRKSRC:Q}/internal/bundled/libs \
	    --node ${PREFIX:Q}/bin/node --platform ${TYPESCRIPT_NPM_PLATFORM:Q} \
	    --work ${WRKDIR:Q}/cli-test
.endif

do-install:
	${CP} -R ${WRKSRC}/npm/package/. ${DESTDIR}${PREFIX}/lib/node_modules/typescript/
	${INSTALL_PROGRAM} ${WRKDIR}/.gopath/${GOPATH_BIN}/tsgo \
	    ${DESTDIR}${PREFIX}/${TYPESCRIPT_PLATFORM_DIR}/lib/tsc
	${INSTALL_DATA} ${WRKSRC}/internal/bundled/libs/*.d.ts \
	    ${DESTDIR}${PREFIX}/${TYPESCRIPT_PLATFORM_DIR}/lib/
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${WRKSRC}/NOTICE.txt \
	    ${DESTDIR}${PREFIX}/${TYPESCRIPT_PLATFORM_DIR}/
	${PRINTF} '%s\n' '{"name":"@typescript/typescript-${TYPESCRIPT_NPM_PLATFORM}","version":"${PKGVERSION_NOREV}","exports":{"./package.json":"./package.json"}}' \
	    > ${DESTDIR}${PREFIX}/${TYPESCRIPT_PLATFORM_DIR}/package.json
	${LN} -sf ../lib/node_modules/typescript/bin/tsc ${DESTDIR}${PREFIX}/bin/tsc

.include "go-modules.mk"
.include "../../lang/go/go-module.mk"
.include "../../lang/python/tool.mk"
.include "../../lang/nodejs/application.mk"
.include "../../mk/bsd.pkg.mk"
