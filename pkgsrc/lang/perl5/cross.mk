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
# An unset input already fails above; do not run an empty command.
.if !empty(${_perl_interpreter}:M/*)
_EMBERBSD_PERL_VERSION!= if test -x ${${_perl_interpreter}:Q}; then \
    ${${_perl_interpreter}:Q} -e 'print $$]'; fi
.else
_EMBERBSD_PERL_VERSION=
.endif
.if ${_EMBERBSD_PERL_VERSION:U} != "5.044000"
PKG_FAIL_REASON+= "${_perl_interpreter} must execute on the host and report Perl 5.44.0"
.endif
.endfor
EMBERBSD_PERL_HOST_PYTHON?= ${EMBERBSD_CROSS_BUILD_PYTHON:U}
.if empty(EMBERBSD_PERL_HOST_PYTHON:M/*) || !exists(${EMBERBSD_PERL_HOST_PYTHON})
PKG_FAIL_REASON+= "Set EMBERBSD_PERL_HOST_PYTHON to the native Python 3 interpreter"
.endif

USE_TOOLS+= perl gmake printf
TOOLS_IGNORE.perl=
TOOLS_PATH.perl= ${EMBERBSD_CROSS_BUILD_PERL}
# Keep the generated dependency makefile distinct on case-insensitive hosts.
MAKE_FILE= GNUmakefile
CONFIGURE_ARGS+= -Dfirstmakefile=GNUmakefile
CONFIGURE_ARGS+= -Dusecrosscompile -Dosname=netbsd -Dosvers=${OS_VERSION:Q}
CONFIGURE_ARGS+= -Dtargetarch=${MACHINE_ARCH}-netbsd -Darchname=${MACHINE_ARCH}-netbsd
CONFIGURE_ARGS+= -Dsysroot=${CROSS_DESTDIR:Q}
CONFIGURE_ARGS+= -Dhostperl=${EMBERBSD_PERL_HOST_MINIPERL:Q}
CONFIGURE_ARGS+= -Dhostgenerate=${EMBERBSD_PERL_HOST_GENERATE:Q}
CONFIGURE_ARGS+= -Dperl=${EMBERBSD_CROSS_BUILD_PERL:Q}
CONFIGURE_ARGS+= -Dar=${TOOLDIR:Q}/bin/${MACHINE_ARCH}--netbsd-ar
CONFIGURE_ARGS+= -Dnm=${TOOLDIR:Q}/bin/${MACHINE_ARCH}--netbsd-nm
CONFIGURE_ARGS+= -Dranlib=${TOOLDIR:Q}/bin/${MACHINE_ARCH}--netbsd-ranlib
PERLLINK_SH= /bin/sh

# Target Configure answers come from a config.sh measured once per platform on
# a target and stored with build paths as placeholders (cross/perl.md). An
# ordinary build therefore needs no target. EMBERBSD_PERL_CAPTURE_CONFIG=yes
# runs the upstream probes over SSH instead and stores a new template in WRKDIR.
EMBERBSD_PERL_STORED_CONFIG?= ${FILESDIR}/config/${MACHINE_PLATFORM}.sh
_PERL5_CONFIG_TEMPLATE= ${FILESDIR}/config-template.py
_PERL5_CONFIG_ID= ${DISTNAME} PKG_OPTIONS=${PKG_OPTIONS:O:ts,}
_PERL5_CONFIG_SET= --set WRKSRC=${WRKSRC:Q} --set WRKDIR=${WRKDIR:Q} \
    --set SYSROOT=${CROSS_DESTDIR:Q} --set TOOLDIR=${TOOLDIR:Q} \
    --set TOOLBASE=${TOOLBASE:Q} --set HOST_MINIPERL=${EMBERBSD_PERL_HOST_MINIPERL:Q} \
    --set HOST_GENERATE=${EMBERBSD_PERL_HOST_GENERATE:Q} \
    --set CROSS_BUILD_PERL=${EMBERBSD_CROSS_BUILD_PERL:Q}
.if ${EMBERBSD_PERL_CAPTURE_CONFIG:Uno:tl} == "yes"
.for _perl_transport in EMBERBSD_PERL_SSH EMBERBSD_PERL_SCP
.if empty(${_perl_transport}:M/*) || !exists(${${_perl_transport}})
PKG_FAIL_REASON+= "${_perl_transport} must select an absolute host transport executable"
.endif
.endfor
.for _perl_remote in EMBERBSD_PERL_TARGET_HOST EMBERBSD_PERL_TARGET_USER EMBERBSD_PERL_TARGET_DIR
.if empty(${_perl_remote})
PKG_FAIL_REASON+= "Set ${_perl_remote} for the existing upstream SSH probe runner"
.endif
.endfor
.if defined(EMBERBSD_PERL_SSH_CONFIG)
CONFIGURE_ENV+= EMBERBSD_PERL_SSH_CONFIG=${EMBERBSD_PERL_SSH_CONFIG:Q}
.endif
CONFIGURE_ENV+= EMBERBSD_PERL_PROBE_SHELL=${CONFIG_SHELL:Q}
CONFIGURE_ENV+= EMBERBSD_PERL_SSH=${EMBERBSD_PERL_SSH:Q} EMBERBSD_PERL_SCP=${EMBERBSD_PERL_SCP:Q}
CONFIGURE_ENV+= EMBERBSD_PERL_PROBE_PYTHON=${EMBERBSD_PERL_HOST_PYTHON:Q}
CONFIGURE_ENV+= EMBERBSD_PERL_PROBE_TRANSPORT=${FILESDIR}/probe-transport.py
EMBERBSD_PERL_TARGET_PORT?= 22
CONFIGURE_ARGS+= -Dtargetport=${EMBERBSD_PERL_TARGET_PORT:Q}
CONFIGURE_ARGS+= -Dtargethost=${EMBERBSD_PERL_TARGET_HOST:Q}
CONFIGURE_ARGS+= -Dtargetuser=${EMBERBSD_PERL_TARGET_USER:Q}
CONFIGURE_ARGS+= -Dtargetdir=${EMBERBSD_PERL_TARGET_DIR:Q}

# Configure may interpret a failed probe as an absent feature. Transport
# failures must invalidate the whole configure result before compilation.
post-configure: ember-perl-probe-transport-check ember-perl-capture-config
.PHONY: ember-perl-probe-transport-check ember-perl-capture-config
ember-perl-probe-transport-check:
	${RUN} if ${TEST} -e ${WRKSRC}/Cross/transport-failed; then \
	    ${CAT} ${WRKSRC}/Cross/transport-failed >&2; exit 1; fi
ember-perl-capture-config: ember-perl-probe-transport-check
	${RUN} ${RM} -f ${WRKDIR}/${MACHINE_PLATFORM}.sh
	${RUN} ${EMBERBSD_PERL_HOST_PYTHON:Q} -B ${_PERL5_CONFIG_TEMPLATE:Q} capture \
	    --identity ${_PERL5_CONFIG_ID:Q} ${_PERL5_CONFIG_SET} \
	    ${WRKSRC}/config.sh ${WRKDIR}/${MACHINE_PLATFORM}.sh
	@${ECHO_MSG} "=> Captured ${WRKDIR}/${MACHINE_PLATFORM}.sh; store it as files/config/${MACHINE_PLATFORM}.sh"
.else
.  if !exists(${EMBERBSD_PERL_STORED_CONFIG})
PKG_FAIL_REASON+= "No stored Perl config.sh for ${MACHINE_PLATFORM}; capture one on a target (profiles/common-build-tools/cross/perl.md)"
.  else
_PERL5_STORED_ID!= ${SED} -n 's/^\# pkgsrc recipe: //p' ${EMBERBSD_PERL_STORED_CONFIG:Q}
.    if "${_PERL5_STORED_ID}" != "${_PERL5_CONFIG_ID}"
PKG_FAIL_REASON+= "Stored Perl config.sh for ${MACHINE_PLATFORM} records ${_PERL5_STORED_ID}, not ${_PERL5_CONFIG_ID}; capture it again (cross/perl.md)"
.    endif
.  endif
# Write the stored answers for this build and let Configure only extract the
# .SH files from them. No probe runs; the runner scripts refuse to start.
do-configure:
	${RUN} ${RM} -f ${WRKSRC}/config.sh
	${RUN} ${EMBERBSD_PERL_HOST_PYTHON:Q} -B ${_PERL5_CONFIG_TEMPLATE:Q} fill \
	    ${_PERL5_CONFIG_SET} ${EMBERBSD_PERL_STORED_CONFIG:Q} ${WRKSRC}/config.sh
	${RUN} ${MKDIR} ${WRKSRC}/Cross && \
	    ${PRINTF} '#!/bin/sh\necho "lang/perl5: stored config.sh; no target runner" >&2\nexit 1\n' \
	    > ${WRKSRC}/Cross/no-target && ${CHMOD} +x ${WRKSRC}/Cross/no-target
	${RUN} cd ${WRKSRC} && ${PKGSRC_SETENV} ${CONFIGURE_ENV} ${CONFIG_SHELL} ./Configure -S
	${RUN} cd ${WRKSRC} && ${PKGSRC_SETENV} ${MAKE_ENV} ${MAKE_PROGRAM} depend
.endif


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
