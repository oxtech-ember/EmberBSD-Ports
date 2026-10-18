# Origin: EmberBSD (AI-assisted); official target data for the shared Rust host.
DISTNAME= rust-std-1.99.1-x86_64-unknown-netbsd
PKGNAME= rust-std-x86_64-netbsd-1.99.1
CATEGORIES= lang
MASTER_SITES= https://static.rust-lang.org/dist/2026-10-15/
EXTRACT_SUFX= .tar.xz

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://www.rust-lang.org/
COMMENT= Official NetBSD/x86_64 standard library for the shared Rust compiler
LICENSE= mit OR apache-2.0

ONLY_FOR_PLATFORM= Darwin-*-aarch64 Darwin-*-x86_64
USE_LANGUAGES= # none: this package installs foreign target data
USE_TOOLS+= pax
NO_BUILD= yes
NO_CONFIGURE= yes
DEPENDS+= rust-bin-1.99.1{,nb[0-9]*}:../../lang/rust-bin

# Foreign ELF libraries cannot pass the native Mach-O loader check.
# The mandatory helper verifies their complete payload and target identity.
CHECK_SHLIBS_SUPPORTED= no
STD_SUBDIR= lib/rustlib/x86_64-unknown-netbsd
STD_COMPONENT= ${WRKSRC}/rust-std-x86_64-unknown-netbsd
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX} && find ${STD_SUBDIR} -type f -print | ${SORT};
INSTALLATION_DIRS= ${STD_SUBDIR} share/licenses/${PKGBASE}

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno} == "yes"
PKG_FAIL_REASON+= "Install this target-data package with the native host MAKECONF."
.endif
.if empty(EMBERBSD_RUST_CROSS_TOOLS:U)
PKG_FAIL_REASON+= "Set EMBERBSD_RUST_CROSS_TOOLS to the verified x86_64 tools prefix."
.endif
BUILD_DEFS+= EMBERBSD_RUST_CROSS_TOOLS

do-install:
	cd ${STD_COMPONENT} && ${PAX} -rw lib ${DESTDIR}${PREFIX}
	${INSTALL_DATA} ${WRKSRC}/LICENSE-APACHE ${WRKSRC}/LICENSE-MIT ${WRKSRC}/COPYRIGHT \
	    ${DESTDIR}${PREFIX}/share/licenses/${PKGBASE}
	${SH} ${FILESDIR}/check.sh ${PREFIX:Q} ${WRKSRC:Q} ${DESTDIR}${PREFIX:Q} \
	    ${WRKDIR:Q}/std-check ${EMBERBSD_RUST_CROSS_TOOLS:Q}/bin/x86_64--netbsd-readelf

.include "../../mk/bsd.pkg.mk"
