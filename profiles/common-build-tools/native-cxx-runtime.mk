# Record the selected native Darwin C++ runtime in package metadata.
.if !defined(EMBERBSD_NATIVE_CXX_RUNTIME_MK)
EMBERBSD_NATIVE_CXX_RUNTIME_MK:=
.include "bsd.fast.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif
.endif
