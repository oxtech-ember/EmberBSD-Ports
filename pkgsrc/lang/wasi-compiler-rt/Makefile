# Origin: EmberBSD (AI-assisted); common compiler-rt source and WASI producer.
FREESTANDING_PACKAGE= wasi-compiler-rt
FREESTANDING_TARGET= wasm32-wasip1
FREESTANDING_RESOURCE_DIR= wasm32-unknown-wasip1
FREESTANDING_RESOURCE_ALIAS= wasm32-unknown-wasi
PKGREVISION= 2
COMMENT= LLVM compiler-rt builtins for the WASI preview1 ABI

# Retain the existing package input while sharing the freestanding producer.
EMBERBSD_WASI_HOST_PREFIX?= ${TOOLBASE}
_FREESTANDING_TOOL_PREFIX= ${EMBERBSD_WASI_HOST_PREFIX}
BUILD_DEFS+= EMBERBSD_WASI_HOST_PREFIX
.include "../../lang/compiler-rt/freestanding.mk"
