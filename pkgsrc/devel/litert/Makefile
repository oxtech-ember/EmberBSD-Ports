# Origin: EmberBSD contributors (AI-assisted); shared LiteRT source owner.
DISTNAME= LiteRT-2.3.2
PKGNAME= litert-source-2.3.2
PKGREVISION= 2
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=google-ai-edge/}
GITHUB_PROJECT= LiteRT
GITHUB_TAG= v${PKGVERSION_NOREV}
HOMEPAGE= https://github.com/google-ai-edge/LiteRT
COMMENT= Shared LiteRT sources for on-device inference
LICENSE= apache-2.0
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort tar
CHECK_INTERPRETER_SKIP+= share/litert-source/*

# These upstream files are LFS pointers to prebuilt runtime binaries. Keep the
# adjacent source/build metadata, but build runtime code with the selected SDK.
do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/litert-source
	${TAR} --exclude './litert/prebuilt/*/*.so' --exclude './litert/prebuilt/*/*.dylib' --exclude './litert/prebuilt/*/*.dll' -cf ${WRKDIR:Q}/litert-source.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/litert-source.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/litert-source

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/litert-source \( -type f -o -type l \) -print | ${SORT};
.include "../../mk/bsd.pkg.mk"
