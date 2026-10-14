# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), shared native and cross CPU package policy.
set(CMAKE_BUILD_TYPE Release CACHE STRING "Package build type")
set(BUILD_SHARED_LIBS OFF CACHE BOOL "Keep engine libraries private")
foreach(option IN ITEMS GGML_NATIVE GGML_BACKEND_DL GGML_CCACHE GGML_OPENMP
    GGML_BLAS GGML_ACCELERATE GGML_METAL GGML_CUDA GGML_VULKAN GGML_RPC
    GGML_CPU_KLEIDIAI)
    set(${option} OFF CACHE BOOL "CPU package baseline")
endforeach()
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64)$")
    set(GGML_CPU_ARM_ARCH armv8-a CACHE STRING "Portable AArch64 baseline")
endif()
