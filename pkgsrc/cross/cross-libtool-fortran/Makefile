# $NetBSD: Makefile,v 1.9 2024/04/12 19:54:43 riastradh Exp $

# Adapted from cross/cross-libtool-base and devel/libtool-fortran.
# Origin: EmberBSD (AI-assisted). Generate real FC and F77 target tags.

###########################################################################
###########################################################################
#
# HEADS UP!  DO NOT CHANGE THE VERSION OR PKGREVISION WITHOUT READING THIS:
#
###########################################################################
###########################################################################
#
# This package is maintained specially in order to preserve pkgsrc
# specific OS changes that diverge from the "out of the box" libtool.
# In order to keep this package in a maintainable condition, the .m4 files
# must be manipulated in order to generate the patch-* files.
#
# See devel/libtool/patches/manual.README for instructions on how to make
# these patch files properly; otherwise your changes WILL be lost on the
# next libtool update.
#
# DO NOT MAKE CHANGES TO THESE FILES:
#
#   patches/patch-build-aux_ltmain.sh
#   patches/patch-configure
#   patches/patch-libltdl_configure
#
# WITHOUT FOLLOWING THESE INSTRUCTIONS.  There are no exceptions to this rule.
#
###########################################################################
###########################################################################

LIBTOOL_CROSS_COMPILE=	yes

.include "../../devel/libtool/Makefile.common"

# XXX Tweaked for cross-compilation.
#PKGNAME=	${DISTNAME:S/-/-base-/}
PKGNAME=	${DISTNAME:S/^libtool-/cross-libtool-fortran-${MACHINE_PLATFORM}-/}
PKGREVISION=	1

COMMENT=	Target Libtool Fortran dispatchers for cross builds

CONFLICTS+=	libtool<=1.3.5nb11

TEST_TARGET=	check

OVERRIDE_DIRDEPTH.install-sh=	1

# Always build libraries and executables that use the runtime linker.
# in addition, disable libtool locking, as the test is broken on AIX,
# and results in files being locked indefinitely.
LDFLAGS.AIX+=		-Wl,-brtl
CONFIGURE_ARGS.AIX+=	--disable-libtool-lock

# The MIPSpro compiler doesn't support -c with -o, but the locking
# workaround is itself broken.  Disable it unconditionally.
CONFIGURE_ARGS.IRIX+=	--disable-libtool-lock

CFLAGS.SunOS+=	${_COMPILER_ABI_FLAG.${ABI}}

# We are going to want libtool to find the same versions of the C, C++,
# and Fortran compilers.
#
USE_LANGUAGES=		c c++ fortran
# XXX Added for cross-compilation.  XXX Should be
# ${TARGET_MACHINE_PLATFORM}, but currently we have to
# fake-cross-compile libtool because it's broken upstream.
GNU_CONFIGURE_PREFIX=	${PREFIX}/cross-${MACHINE_PLATFORM}
PLIST_SUBST+=		MACHINE_PLATFORM=${MACHINE_PLATFORM:Q}
CONFIGURE_ARGS+=	--disable-ltdl-install
# Both tag probes must use the real pkgsrc Fortran wrapper.
CONFIGURE_ENV+= FC=${FC:Q} F77=${FC:Q}
CONFIGURE_ARGS+= FC=${FC:Q} F77=${FC:Q}

USE_TOOLS+=		echo

REPLACE_SH+=	libtoolize.in

# XXX Added for cross-compilation.
FILESDIR=	${PKGSRCDIR}/devel/libtool-base/files

# Keep compiler dispatch inside the consumer's active pkgsrc wrapper PATH.
# An absolute configured CC bypasses runtime path rewriting after Libtool
# expands dependency .la files.
.PHONY: fix-libtool
fix-libtool:
	cd ${WRKSRC}; for f in libtool; do				\
		${SED}	-e "s,-L${BUILDLINK_DIR}/lib *,,g"		\
			-e "s,${BUILDLINK_DIR}/lib *,,g"		\
		-e 's|^CC="${CC}"$$|CC="${CC:T}"|'		\
		-e 's|^CC="${CXX}"$$|CC="${CXX:T}"|'		\
		-e 's|^LTCC="${CC}"$$|LTCC="${CC:T}"|'	\
		-e 's|^CC="${FC}"$$|CC="f77"|'		\
			$$f > $$f.new;					\
		if [ -x $$f ]; then ${CHMOD} +x $$f.new; fi;		\
		${MV} -f $$f.new $$f;					\
	done

# Refuse a nominal provider which silently omits either real Fortran tag.
post-build: fix-libtool
	${RUN}${GREP} -q '^# ### BEGIN LIBTOOL TAG CONFIG: FC$$' ${WRKSRC}/libtool
	${RUN}${GREP} -q '^# ### BEGIN LIBTOOL TAG CONFIG: F77$$' ${WRKSRC}/libtool

	# The host dispatcher must use the Libtool configured for the target.
	@${SED}	-e "s|@PREFIX@|"${GNU_CONFIGURE_PREFIX:Q}"|g"				\
		-e "s|@SH@|"${SH:Q}"|g"					\
		${FILESDIR}/shlibtool-fortran.in > ${WRKSRC}/shlibtool-fortran

# Do not install the C/C++ tools, macros or manuals a second time.
INSTALLATION_DIRS+= cross-${MACHINE_PLATFORM}/bin
do-install:
	${INSTALL_SCRIPT} ${WRKSRC}/shlibtool-fortran ${DESTDIR}${PREFIX}/cross-${MACHINE_PLATFORM}/bin/shlibtool-fortran
	${INSTALL_SCRIPT} ${WRKSRC}/libtool ${DESTDIR}${PREFIX}/cross-${MACHINE_PLATFORM}/bin/libtool-fortran

BUILDLINK_DEPMETHOD.dlcompat=	build

.include "../../mk/dlopen.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
