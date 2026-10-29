# SPDX-License-Identifier: BSD-2-Clause
.if empty(_EMBER_TARGET_RUNTIME_VERSION:U) || empty(_EMBER_TARGET_RUNTIME_KIND:U)
.error Prepared target tools must identify their C++ runtime
.endif
EMBERBSD_SDK_SOURCE= ${_EMBER_TARGET_SDK_SOURCE}
EMBER_LLVM_CXX_PYTHON= ${_EMBER_TARGET_NATIVE_PYTHON}
.if ${_EMBER_TARGET_RUNTIME_KIND} == "stage"
EMBER_LLVM_CXX_STAGE= ${_EMBER_TARGET_RUNTIME_ROOT}
EMBER_LLVM_CXX_BASE= ${_EMBER_TARGET_RUNTIME_BASE}
.elif ${_EMBER_TARGET_RUNTIME_KIND} == "sysroot"
EMBER_LLVM_CXX_SYSROOT= ${_EMBER_TARGET_RUNTIME_ROOT}
.else
.error Unsupported target C++ runtime source
.endif
DEPENDS+= libcxx>=${_EMBER_TARGET_RUNTIME_VERSION}nb2:../../lang/libcxx
DEPENDS+= libcxxabi>=${_EMBER_TARGET_RUNTIME_VERSION}nb2:../../lang/libcxxabi
DEPENDS+= libunwind>=${_EMBER_TARGET_RUNTIME_VERSION}nb2:../../lang/libunwind
BUILD_DEPENDS+= libcxx-devel>=${_EMBER_TARGET_RUNTIME_VERSION}nb2:../../lang/libcxx-devel
BUILD_DEPENDS+= libcxxabi-devel>=${_EMBER_TARGET_RUNTIME_VERSION}nb2:../../lang/libcxxabi-devel
BUILD_DEPENDS+= libunwind-devel>=${_EMBER_TARGET_RUNTIME_VERSION}nb2:../../lang/libunwind-devel
