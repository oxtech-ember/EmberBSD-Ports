# $NetBSD: vars.mk,v 1.5 2011/10/28 07:41:52 obache Exp $
#
# This Makefile fragment exposes several Perl configuration variables
# to the package Makefiles.  The variables are only defined if the
# ${PERL5} executable exists.

.include "../../mk/bsd.prefs.mk"

_PERL5_VARS=	INSTALLARCHLIB INSTALLSCRIPT				\
		INSTALLVENDORBIN INSTALLVENDORSCRIPT			\
		INSTALLVENDORARCH INSTALLVENDORLIB			\
		INSTALLVENDORMAN1DIR INSTALLVENDORMAN3DIR

# Cross modules inspect the target Config with the selected host Perl; target
# executable and target XS libraries are never loaded on the host.
.if ${USE_CROSS_COMPILE:Uno} == "yes" && defined(EMBERBSD_PERL_TARGET_CONFIG)
_PERL5_VARS_CMD=	${EMBERBSD_CROSS_BUILD_PYTHON:Q} -B ${.PARSEDIR}/files/prepare-build-config.py \
	--metadata-only --host-perl ${EMBERBSD_CROSS_BUILD_PERL:Q} \
	--target-config ${EMBERBSD_PERL_TARGET_CONFIG:Q} --sysroot ${EMBERBSD_CROSS_SYSROOT:Q}
.endif
.if defined(_PERL5_VARS_CMD) || (defined(PERL5) && exists(${PERL5:Q}))
#
# Locate some of the installation prefixes for ${PERL5} that are used to
# define later variables.
#
.  if !defined(_PERL5_VARS_OUT)
_PERL5_VARS_CMD?=	${PERL5:Q} -V:prefix -V:installprefix ${_PERL5_VARS:tl:S/^/-V:/}
_PERL5_VARS_OUT:=	${_PERL5_VARS_CMD:sh:ts,:S/'//g:S/;//g:Q:S/,/ /g}
MAKEVARS+=		_PERL5_VARS_OUT
.  endif

.  if !defined(_PERL5_PREFIX)
_PERL5_PREFIX:=		${_PERL5_VARS_OUT:Mprefix=*:C/^prefix=//}
MAKEVARS+=		_PERL5_PREFIX
.  endif
# Relocatable native Perl reports prefix as .../.., while its installation
# paths remain absolute.  Cross build-tool users also query this native
# Config unless they explicitly select target metadata.
.  if (${USE_CROSS_COMPILE:Uno} != "yes" || !defined(EMBERBSD_PERL_TARGET_CONFIG)) && !empty(_PERL5_PREFIX:M.../*)
_PERL5_PREFIX:=		${_PERL5_VARS_OUT:Minstallprefix=*:C/^installprefix=//}
.  endif
.  if empty(_PERL5_PREFIX:M/*) || ${_PERL5_PREFIX} == "/"
.error Cannot read absolute Perl installation prefix
.  endif
.  for _perl_meta in ${_PERL5_VARS:tl}
.    if empty(_PERL5_VARS_OUT:M${_perl_meta}=${_PERL5_PREFIX}/*)
.error Perl install path ${_perl_meta} is outside its installation prefix
.    endif
.  endfor
.  if ${USE_CROSS_COMPILE:Uno} == "yes" && defined(EMBERBSD_PERL_TARGET_CONFIG)
.    if empty(_PERL5_PREFIX) || empty(_PERL5_VARS_OUT:Mprefix=*)
.error Cannot read target Perl Config metadata
.    endif
.    for _perl_meta in ${_PERL5_VARS:tl}
.      if empty(_PERL5_VARS_OUT:M${_perl_meta}=*)
.error Incomplete target Perl Config metadata: ${_perl_meta}
.      endif
.    endfor
.  endif

#
# Define PERL5_SUB_* as the vendor variables minus the installation prefix
# define later variables.
#
.  for _var_ in ${_PERL5_VARS}
.    if !defined(PERL5_SUB_${_var_})
PERL5_SUB_${_var_}:=	${_PERL5_VARS_OUT:M${_var_:tl}=*:S/^${_var_:tl}=${_PERL5_PREFIX:=/}//}
.    endif
PERL5_${_var_}?=	${PREFIX}/${PERL5_SUB_${_var_}}
MAKEVARS+=		PERL5_SUB_${_var_}
PLIST_SUBST+=		PERL5_SUB_${_var_}=${PERL5_SUB_${_var_}:Q}
PRINT_PLIST_AWK+=	/^${PERL5_SUB_${_var_}:S|/|\\/|g}/ \
			{ gsub(/${PERL5_SUB_${_var_}:S|/|\\/|g}/, \
			  "$${PERL5_SUB_${_var_}}") }
.  endfor
.endif	# PERL5
