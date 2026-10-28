# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Target Perl data for host build tools.
.if !defined(_EMBER_PERL_BUILD_CONTEXT_MK)
_EMBER_PERL_BUILD_CONTEXT_MK= yes
.if ${USE_CROSS_COMPILE:Uno} == "yes"
.  if !defined(EMBERBSD_PERL_TARGET_CONFIG) || !defined(EMBERBSD_CROSS_BUILD_PERL)
PKG_FAIL_REASON+= "Cross Perl builds require selected host Perl and target Config.pm."
.  else
_PERL5_BUILD_CONFIG= ${WRKDIR}/ember-perl-build-config.json
_PERL5_CONFIG_HELPER:= ${.PARSEDIR}/files/prepare-build-config.py
CONFIGURE_ENV+= EMBERBSD_PERL_BUILD_CONFIG=${_PERL5_BUILD_CONFIG:Q}
.PHONY: ember-perl-build-config
ember-perl-build-config:
	${RUN}${EMBERBSD_CROSS_BUILD_PYTHON:Q} -B ${_PERL5_CONFIG_HELPER:Q} \
	    --host-perl ${EMBERBSD_CROSS_BUILD_PERL:Q} --target-config ${EMBERBSD_PERL_TARGET_CONFIG:Q} \
	    --sysroot ${EMBERBSD_CROSS_SYSROOT:Q} --cc ${WRAPPER_BINDIR:Q}/${CC:Q} \
	    --ld ${WRAPPER_BINDIR:Q}/${CC:Q} --ar ${AR:Q} --ranlib ${RANLIB:Q} \
	    --cflags ${CFLAGS:Q} --ldflags ${LDFLAGS:Q} --output ${_PERL5_BUILD_CONFIG:Q}
pre-configure: ember-perl-build-config
.  endif
.endif
.endif
