# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). These build-host programs are native-only.
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
PLIST_VARS+= hosttools
PLIST.hosttools= yes
INSTALLATION_DIRS+= libexec/perl5/${PKGVERSION_NOREV}

.PHONY: perl5-install-host-tools
post-install: perl5-install-host-tools
perl5-install-host-tools:
	${INSTALL_PROGRAM} ${WRKSRC}/miniperl \
		${DESTDIR}${PREFIX}/libexec/perl5/${PKGVERSION_NOREV}/miniperl
	${INSTALL_PROGRAM} ${WRKSRC}/generate_uudmap \
		${DESTDIR}${PREFIX}/libexec/perl5/${PKGVERSION_NOREV}/generate_uudmap
.endif
