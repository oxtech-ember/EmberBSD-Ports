# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), macOS -> EmberBSD Perl 5.44.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if ${OPSYS} != "NetBSD" || (${MACHINE_ARCH} != "aarch64" && ${MACHINE_ARCH} != "x86_64")
PKG_FAIL_REASON+= "The Perl cross recipe requires EmberBSD/aarch64 or EmberBSD/x86_64"
.endif
.for _perl_input in EMBERBSD_PERL_HOST_MINIPERL EMBERBSD_PERL_HOST_GENERATE EMBERBSD_CROSS_BUILD_PERL
.if empty(${_perl_input}:M/*) || !exists(${${_perl_input}})
PKG_FAIL_REASON+= "${_perl_input} must select a matching Perl 5.44 build-host executable"
.endif
.endfor
.for _perl_interpreter in EMBERBSD_PERL_HOST_MINIPERL EMBERBSD_CROSS_BUILD_PERL
_EMBERBSD_PERL_VERSION!= if test -x ${${_perl_interpreter}:Q}; then \
    ${${_perl_interpreter}:Q} -e 'print $$]'; fi
.if ${_EMBERBSD_PERL_VERSION:U} != "5.044000"
PKG_FAIL_REASON+= "${_perl_interpreter} must execute on the host and report Perl 5.44.0"
.endif
.endfor
.for _perl_remote in EMBERBSD_PERL_TARGET_HOST EMBERBSD_PERL_TARGET_USER EMBERBSD_PERL_TARGET_DIR
.if empty(${_perl_remote})
PKG_FAIL_REASON+= "Set ${_perl_remote} for the existing upstream SSH probe runner"
.endif
.endfor
USE_TOOLS+= perl gmake
TOOLS_IGNORE.perl=
TOOLS_PATH.perl= ${EMBERBSD_CROSS_BUILD_PERL}
# Keep the generated dependency makefile distinct on case-insensitive hosts.
MAKE_FILE= GNUmakefile
CONFIGURE_ARGS+= -Dfirstmakefile=GNUmakefile
CONFIGURE_ARGS+= -Dusecrosscompile -Dosname=netbsd -Dosvers=${OS_VERSION:Q}
CONFIGURE_ARGS+= -Dtargetarch=${MACHINE_ARCH}-netbsd -Darchname=${MACHINE_ARCH}-netbsd
CONFIGURE_ARGS+= -Dtargethost=${EMBERBSD_PERL_TARGET_HOST:Q}
CONFIGURE_ARGS+= -Dtargetuser=${EMBERBSD_PERL_TARGET_USER:Q}
CONFIGURE_ARGS+= -Dtargetdir=${EMBERBSD_PERL_TARGET_DIR:Q}
CONFIGURE_ARGS+= -Dsysroot=${CROSS_DESTDIR:Q}
CONFIGURE_ARGS+= -Dhostperl=${EMBERBSD_PERL_HOST_MINIPERL:Q}
CONFIGURE_ARGS+= -Dhostgenerate=${EMBERBSD_PERL_HOST_GENERATE:Q}
CONFIGURE_ARGS+= -Dperl=${EMBERBSD_CROSS_BUILD_PERL:Q}
CONFIGURE_ARGS+= -Dar=${TOOLDIR:Q}/bin/${MACHINE_ARCH}--netbsd-ar
CONFIGURE_ARGS+= -Dnm=${TOOLDIR:Q}/bin/${MACHINE_ARCH}--netbsd-nm
CONFIGURE_ARGS+= -Dranlib=${TOOLDIR:Q}/bin/${MACHINE_ARCH}--netbsd-ranlib
PERLLINK_SH= /bin/sh

post-install: ember-perl-target-config
.PHONY: ember-perl-target-config
ember-perl-target-config:
	${EMBERBSD_CROSS_BUILD_PERL:Q} ${FILESDIR}/target-config.pl \
	    ${WRKSRC:Q} ${CROSS_DESTDIR:Q} ${WRKDIR}/target-config
	${INSTALL_DATA} ${WRKDIR}/target-config/lib/Config.pm \
	    ${DESTDIR}${PERL5_PACKLIST_DIR}/Config.pm
	${INSTALL_DATA} ${WRKDIR}/target-config/lib/Config_heavy.pl \
	    ${DESTDIR}${PERL5_PACKLIST_DIR}/Config_heavy.pl
	${INSTALL_DATA} ${WRKDIR}/target-config/config.h \
	    ${DESTDIR}${PERL5_PACKLIST_DIR}/CORE/config.h
.endif
