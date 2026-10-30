# $NetBSD: Makefile,v 1.169 2026/03/26 05:41:37 adam Exp $

EMBERBSD_ICU_PKGDIR:= ${.PARSEDIR:tA}

DISTNAME=	icu4c-79.1-sources
PKGNAME=	${DISTNAME:S/4c//:S/-sources//}
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GITHUB:=unicode-org/}
GITHUB_PROJECT=	icu
GITHUB_RELEASE=	release-${PKGVERSION_NOREV}
EXTRACT_SUFX=	.tgz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://icu.unicode.org/
COMMENT=	Robust and full-featured Unicode services
LICENSE=	unicode-v3 AND modified-bsd AND mit

POLICY_UPDATE_LIMITED=	abi

WRKSRC=			${WRKDIR}/icu/source
USE_LANGUAGES=		c c++
USE_CC_FEATURES=	c11
USE_CXX_FEATURES=	c++17
USE_TOOLS+=		gmake pkg-config
TEST_TARGET=		check
UNLIMIT_RESOURCES+=	datasize
GNU_CONFIGURE=		yes
CONFIGURE_ARGS+=	--enable-static
CONFIGURE_ENV+=		U_MAKE=${TOOLS_GMAKE}
# Avoid Python; not really needed for build.
# Fixes circular dependency on Python and Sqlite3 with ICU.
CONFIGURE_ENV+=		ac_cv_prog_PYTHON=""

# Set the supported work-directory policy before prefs derive tool paths.
.if defined(ICU_STAGED_HOST_PREFIX)
_ICU_STAGE_KEY_CMD= ${EMBERBSD_CROSS_BUILD_PYTHON:Q} -c 'import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())' ${ICU_STAGED_HOST_PREFIX:Q}
WRKDIR_BASENAME?= work${_CROSSDIR_SUFFIX}-${ICU_STAGED_HOST_PREFIX:hash}
.endif

.include "../../mk/bsd.prefs.mk"

# The selected native toolset PATH may hold no "ar"; configure takes AR.
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
CONFIGURE_ENV+=		AR=${AR:Q} RANLIB=${RANLIB:Q}
.endif

# The selected Darwin binding links ICU C++ components to the shared runtime.
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && defined(EMBERBSD_NATIVE_CXX_BINDING_RECORD) && !empty(EMBERBSD_NATIVE_CXX_BINDING_RECORD) && ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} != "__ember1"
DEPENDS+= libcxx>=23.1.4:../../lang/libcxx
.endif
.include "../../mk/emberbsd-native-cxx-runtime.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
PKGREVISION= 1
.endif

# The upstream data tests require the explicit development-host Python.
.if defined(EMBERBSD_CROSS_BUILD_PYTHON)
TEST_MAKE_FLAGS+= ICU_TEST_PYTHON=${EMBERBSD_CROSS_BUILD_PYTHON:Q}
.endif

.if defined(EMBERBSD_ICU_DEVEL)
.if ${EMBERBSD_ICU_DEVEL} != "yes" || ${PKGPATH} != "textproc/icu-devel"
PKG_FAIL_REASON+= "The ICU SDK role belongs to textproc/icu-devel"
.endif
PKGNAME= icu-devel-79.1
COMMENT= ICU target SDK for the development-host sysroot
DISTINFO_FILE= ${EMBERBSD_ICU_PKGDIR}/distinfo
PATCHDIR= ${EMBERBSD_ICU_PKGDIR}/patches
FILESDIR= ${EMBERBSD_ICU_PKGDIR}/files
DEPENDS+= icu-${PKGVERSION_NOREV}nb1:../../textproc/icu
CONFLICTS+= icu<${PKGVERSION_NOREV}nb1
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes" || ${OPSYS} != "NetBSD"
PKG_FAIL_REASON+= "The ICU SDK requires a NetBSD cross build; native builds keep the full package"
.endif
.endif

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
PKGREVISION= 1
.if ${MACHINE_ARCH} != "aarch64" && ${MACHINE_ARCH} != "x86_64"
PKG_FAIL_REASON+= "The ICU split requires a common AArch64 or amd64 target"
.endif
LIBTOOLIZE_PLIST= no
ICU_FULL_PLIST= ${EMBERBSD_ICU_PKGDIR}/PLIST.full-cross
ICU_RUNTIME_PLIST= ${EMBERBSD_ICU_PKGDIR}/PLIST.runtime
ICU_DEVEL_PLIST= ${EMBERBSD_ICU_PKGDIR}/../icu-devel/PLIST
.if defined(EMBERBSD_ICU_DEVEL)
ICU_PACKAGE_PART= devel
PLIST_SRC= ${ICU_DEVEL_PLIST}
.else
ICU_PACKAGE_PART= runtime
PLIST_SRC= ${ICU_RUNTIME_PLIST}
.endif
.if !defined(EMBERBSD_SDK_SOURCE) || !defined(EMBERBSD_CROSS_BUILD_PYTHON)
PKG_FAIL_REASON+= "ICU cross packages require EMBERBSD_SDK_SOURCE and EMBERBSD_CROSS_BUILD_PYTHON"
.endif
.endif

.if ${USE_CROSS_COMPILE:tl} == "yes"

# Host tools must match the ICU release; target-only metadata revisions
# do not change its data format or require rebuilding identical host tools.
_ICU_HOST_PATTERN=	icu-${PKGVERSION_NOREV}{,nb[0-9]*}
# A staged replacement package can supply the matching native generators while
# the previous ICU remains installed. Normal builds use the installed package.
.if defined(ICU_STAGED_HOST_PREFIX)
.  if empty(ICU_STAGED_HOST_PREFIX) || empty(ICU_STAGED_HOST_PREFIX:M/*)
PKG_FAIL_REASON+= "ICU_STAGED_HOST_PREFIX must be an absolute staged package path"
.  endif
.  if ${NATIVE_OPSYS} != "Darwin"
PKG_FAIL_REASON+= "Staged ICU host tools currently require a Darwin host"
.  endif
USE_TOOLS+= find
_ICU_STAGED_ENV= ${TOOLBASE:Q}/bin/genv DYLD_LIBRARY_PATH=${ICU_STAGED_HOST_PREFIX:Q}/lib
.else
TOOL_DEPENDS+=		${_ICU_HOST_PATTERN}:../../textproc/icu
.endif

.if defined(ICU_STAGED_HOST_PREFIX)
# Keep metadata for distinct explicit stages apart when a work tree is reused.
_ICU_STAGE_KEY:= ${_ICU_STAGE_KEY_CMD:sh}
.if empty(WRKDIR_BASENAME:M*-${ICU_STAGED_HOST_PREFIX:hash}) || "${WRKDIR}" != "${BUILD_DIR}/${WRKDIR_BASENAME}"
.error Staged ICU tools require a stage-keyed work directory under WRKOBJDIR
.endif
# The short directory hash is guarded by the complete selected-path digest.
_ICU_STAGE_MARKER= ${WRKDIR}/.icu-host-stage-key
.if exists(${WRKDIR}/.configure_done) && !exists(${_ICU_STAGE_MARKER}) && !${_CLEANING}
.error ICU configured work tree lacks host-tool identity; clean this package work tree
.endif
.if exists(${_ICU_STAGE_MARKER}) && !${_CLEANING}
_ICU_RECORDED_STAGE_CMD= ${EMBERBSD_CROSS_BUILD_PYTHON:Q} -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_text().strip())' ${_ICU_STAGE_MARKER:Q}
_ICU_RECORDED_STAGE:= ${_ICU_RECORDED_STAGE_CMD:sh}
.  if ${_ICU_RECORDED_STAGE} != ${_ICU_STAGE_KEY}
.error ICU stage hash collision; use a fresh WRKOBJDIR or clean this package work tree
.  endif
.endif
ICU_CROSS_DIR= ${WRKDIR}/.icu_cross
.else
ICU_CROSS_DIR=		${WRKDIR}/.icu_cross
.endif
ICU_CROSS_COOKIE=	${ICU_CROSS_DIR}/.cookie

CONFIGURE_ARGS+=	--with-cross-build=${ICU_CROSS_DIR}
pre-configure: ${ICU_CROSS_COOKIE}
.if defined(ICU_STAGED_HOST_PREFIX)
pre-configure: icu-staged-tools-verify
icu-staged-tools-verify: .PHONY
	${RUN}case ${ICU_STAGED_HOST_PREFIX:Q} in /*) ;; *) ${ECHO_MSG} "Staged ICU prefix must be absolute"; exit 1;; esac
	${RUN}${TEST} "$$(${_ICU_STAGED_ENV} ${ICU_STAGED_HOST_PREFIX:Q}/bin/icu-config --version)" = ${PKGVERSION_NOREV:Q} || { ${ECHO_MSG} "Staged ICU host tools have a different release"; exit 1; }
	${RUN}${_ICU_STAGED_ENV} ${ICU_STAGED_HOST_PREFIX:Q}/bin/icuinfo >/dev/null
.endif

.if defined(ICU_STAGED_HOST_PREFIX)
ICU_CROSS_TOOLS= ${FIND} ${ICU_STAGED_HOST_PREFIX:Q}/bin ${ICU_STAGED_HOST_PREFIX:Q}/sbin \
	-maxdepth 1 \( -type f -o -type l \) -print
.else
ICU_CROSS_TOOLS=	\
	${HOST_PKG_INFO} -qL ${_ICU_HOST_PATTERN:Q} \
	| ${GREP} -e '^'${TOOLBASE}/bin -e '^'${TOOLBASE}/sbin
.endif

show-icu-cross-tools: .PHONY
	@${ICU_CROSS_TOOLS}

icu-cross-clean: .PHONY
	${RUN}${RM} -f ${ICU_CROSS_COOKIE}
icu-cross-tools: .PHONY ${ICU_CROSS_COOKIE}
.if defined(ICU_STAGED_HOST_PREFIX)
icu-cross-tools: icu-staged-tools-verify
.endif
${ICU_CROSS_COOKIE}:
	@${STEP_MSG} Faking ICU cross-build directory
.if defined(ICU_STAGED_HOST_PREFIX)
	${RUN}case ${ICU_STAGED_HOST_PREFIX:Q} in /*) ;; *) ${ECHO_MSG} "Staged ICU prefix must be absolute"; exit 1;; esac
	${RUN}${TEST} "$$(${_ICU_STAGED_ENV} ${ICU_STAGED_HOST_PREFIX:Q}/bin/icu-config --version)" = ${PKGVERSION_NOREV:Q} || { ${ECHO_MSG} "Staged ICU host tools have a different release"; exit 1; }
	${RUN}${_ICU_STAGED_ENV} ${ICU_STAGED_HOST_PREFIX:Q}/bin/icuinfo >/dev/null
.endif
	${RUN}${TEST} -d ${ICU_CROSS_DIR} || ${MKDIR} ${ICU_CROSS_DIR}
.  for d in bin config lib
	${RUN}${TEST} -d ${ICU_CROSS_DIR}/${d} || \
		${MKDIR} ${ICU_CROSS_DIR}/${d}
.  endfor
	${RUN}cd ${ICU_CROSS_DIR} && ${ICU_CROSS_TOOLS} \
	| while read f; do \
		${LN} -sfn "$$f" bin/; \
	done
	${RUN} {							\
		${ECHO} CROSS_ICU_VERSION=${PKGVERSION_NOREV};		\
		${ECHO} TOOLEXEEXT=;					\
		${ECHO} TOOLBINDIR='$$(cross_buildroot)/bin';		\
		${ECHO} TOOLLIBDIR='$$(cross_buildroot)/lib';		\
		${ECHO} INVOKE=${_ICU_STAGED_ENV:U:Q};		\
		${ECHO} PKGDATA_INVOKE=${_ICU_STAGED_ENV:U:Q};	\
	} >${ICU_CROSS_DIR}/config/icucross.mk
	${RUN}${ECHO} 'CURR_FULL_DIR?=$$(shell pwd | sed "s/ /\\\\\\\\ /g")' \
		>${ICU_CROSS_DIR}/config/icucross.inc
	${RUN}${ECHO} > ${.TARGET}

.endif

CHECK_SSP_SKIP=		lib/libicudata.so*

.include "../../mk/pthread.buildlink3.mk"

.if defined(PTHREAD_TYPE) && ${PTHREAD_TYPE} != "native"
CONFIGURE_ARGS+=	--disable-threads
.endif

.include "../../mk/compiler.mk"

# from ICU_CHECK_MH_FRAG in source/acinclude.m4
.if ${OPSYS} == "SunOS"
.  if ${PKGSRC_COMPILER:Mclang} || ${PKGSRC_COMPILER:Mgcc}
PLIST_SUBST+=		MH_NAME=mh-solaris-gcc
.  else
PLIST_SUBST+=		MH_NAME=mh-solaris
.  endif
.  if ${CC_VERSION:Mgcc-4.[6-9].*}
BUILDLINK_TRANSFORM+=	rm:-D__STDC__=0
.  endif
BUILDLINK_TRANSFORM+=	rm:-ansi
.elif ${MACHINE_PLATFORM:MLinux-*-alpha}
.  if ${CC_VERSION:Mgcc*}
PLIST_SUBST+=		MH_NAME=mh-alpha-linux-gcc
.  else
PLIST_SUBST+=		MH_NAME=mh-alpha-linux-cc
.  endif
.elif ${MACHINE_PLATFORM:MLinux-*-powerpc*}
.  if ${CC_VERSION:Mgcc*}
PLIST_SUBST+=		MH_NAME=mh-linux
.  else
PLIST_SUBST+=		MH_NAME=mh-linux-va
.  endif
.elif ${OPSYS} == "Linux"
PLIST_SUBST+=		MH_NAME=mh-linux
.elif ${OPSYS} == "Cygwin"
PLIST_SUBST+=		MH_NAME=mh-cygwin
.elif ${OPSYS:M*BSD*} || ${OPSYS} == "DragonFly"
PLIST_SUBST+=		MH_NAME=mh-bsd-gcc
.elif ${OPSYS} == "AIX"
.  if ${CC_VERSION:Mgcc*}
PLIST_SUBST+=		MH_NAME=mh-aix-gcc
.  else
PLIST_SUBST+=		MH_NAME=mh-aix-va
.  endif
.elif ${OPSYS} == "HPUX"
.  if ${CC_VERSION:Mgcc*}
PLIST_SUBST+=		MH_NAME=mh-hpux-gcc
.  else
PLIST_SUBST+=		MH_NAME=mh-hpux-acc
.  endif
.elif ${OPSYS} == "Darwin"
PLIST_SUBST+=		MH_NAME=mh-darwin
.elif ${OPSYS} == "Haiku"
PLIST_SUBST+=		MH_NAME=mh-haiku
.elif ${OPSYS} == "IRIX"
PLIST_SUBST+=		MH_NAME=mh-irix
.elif ${OPSYS} == "Cygwin"
PLIST_SUBST+=		MH_NAME=mh-cygwin
.elif ${OS_VARIANT} == "SCOOSR5"
PLIST_SUBST+=		MH_NAME=mh-scoosr5
.elif ${OPSYS} == "OSF1"
PLIST_SUBST+=		MH_NAME=mh-alpha-osf
.elif ${OPSYS} == "QNX"
PLIST_SUBST+=		MH_NAME=mh-qnx
.else
# For unknown systems, set the filename to mh-unknown so that the user
# gets a warning about missing files.
PLIST_SUBST+=		MH_NAME=mh-unknown
.endif

PKGCONFIG_OVERRIDE+=		config/icu*.pc
PKGCONFIG_OVERRIDE_STAGE=	post-build

REPLACE_SH=	config/icu-config-top

# work around ICU-20533 (build failure on big endian machines)
post-configure:
	${MKDIR} ${WRKSRC}/data/out
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && defined(ICU_STAGED_HOST_PREFIX)
	${ECHO} ${_ICU_STAGE_KEY:Q} > ${_ICU_STAGE_MARKER:Q}
.endif

.if ${OPSYS} == "Cygwin"
INSTALL_UNSTRIPPED=	yes
SO_MAJOR=		${PKGVERSION_NOREV:R}
.  for l in data i18n io le lx test tu uc
GENERATE_PLIST+=	${ECHO} bin/cygicu${l}${SO_MAJOR}.dll;
GENERATE_PLIST+=	${ECHO} lib/libicu${l}${SO_MAJOR}.dll.a;
.  endfor

post-install:
	mv ${DESTDIR}${PREFIX}/lib/cygicu*.dll ${DESTDIR}${PREFIX}/bin/
.  for l in data i18n io le lx test tu uc
	${LN} -s libicu${l}${SO_MAJOR}.dll.a ${DESTDIR}${PREFIX}/lib/libicu${l}.dll.a
.  endfor

SUBST_CLASSES+=		icu-config
SUBST_STAGE.icu-config=	post-install
SUBST_FILES.icu-config=	${DESTDIR}${PREFIX}/bin/icu-config
SUBST_SED.icu-config+=	-e '/^ICUUC_FILE=/ s/libdir/bindir/'
SUBST_SED.icu-config+=	-e 's/l$${LIBICU}/l$${ICUPREFIX}/g'
SUBST_SED.icu-config+=	-e '/l$${ICUPREFIX}/ s/$${ICULIBSUFFIX_VERSION}//g'
.endif

# Keep build-host commands out of the installed development interface.
# Point it at the native compiler of the same family (lang/clang by default).
.if ${USE_CROSS_COMPILE:tl} == "yes" && (${OPSYS} == "NetBSD" || ${EMBERBSD_COMMON_TOOLS:Uno} == "yes")
post-install: ember-icu-cross-metadata
.PHONY: ember-icu-cross-metadata
ember-icu-cross-metadata:
	${RUN} set -e; for file in \
	    ${DESTDIR}${PREFIX}/bin/icu-config \
	    ${DESTDIR}${PREFIX}/lib/icu/${PKGVERSION_NOREV}/Makefile.inc \
	    ${DESTDIR}${PREFIX}/lib/icu/${PKGVERSION_NOREV}/pkgdata.inc; do \
		${CP} -p "$$file" "$$file.ember"; \
		${SETENV} ICU_BUILD_SHELL=${CONFIG_SHELL:Q} \
		    ICU_BUILD_INSTALL_DATA=${INSTALL_DATA:Q} \
		    ICU_BUILD_INSTALL_PROGRAM=${INSTALL_PROGRAM:Q} \
		    ICU_BUILD_INSTALL_SCRIPT=${INSTALL_SCRIPT:Q} \
		    ICU_CROSS_TRIPLET=${MACHINE_GNU_PLATFORM:Q} \
		    ICU_CROSS_SYSROOT=${CROSS_DESTDIR:Q} \
		    ICU_CROSS_CC=${CC:T:Q} ICU_CROSS_CXX=${CXX:T:Q} \
		    ICU_TARGET_CC=${PREFIX:Q}/bin/${CC:T:S/^${MACHINE_GNU_PLATFORM}-//:Q} \
		    ICU_TARGET_CXX=${PREFIX:Q}/bin/${CXX:T:S/^${MACHINE_GNU_PLATFORM}-//:Q} \
		    ${AWK} -f ${FILESDIR}/cross-metadata.awk "$$file" > "$$file.ember"; \
		${MV} -f "$$file.ember" "$$file"; \
	done
.endif

.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
post-install: ember-icu-select-stage
.PHONY: ember-icu-select-stage
ember-icu-select-stage: ember-icu-cross-metadata
.for _icu_part in FULL RUNTIME DEVEL
	${MAKE} ${WRKDIR:Q}/.icu-${_icu_part:tl}-plist \
	    PLIST=${WRKDIR:Q}/.icu-${_icu_part:tl}-plist \
	    PLIST_SRC=${ICU_${_icu_part}_PLIST:Q}
.endfor
	${EMBERBSD_CROSS_BUILD_PYTHON} -B ${FILESDIR}/select-stage.py \
	    --sdk-source ${EMBERBSD_SDK_SOURCE:Q} ${ICU_PACKAGE_PART:Q} \
	    ${DESTDIR:Q}${PREFIX:Q} ${WRKDIR:Q}/.icu-full-plist \
	    ${WRKDIR:Q}/.icu-runtime-plist ${WRKDIR:Q}/.icu-devel-plist
.endif
