# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Baseline shared CPU development profile.
set(NCNN_VERSION 20260526 CACHE STRING "Pinned upstream release" FORCE)
set(CMAKE_BUILD_TYPE Release CACHE STRING "Upstream release configuration" FORCE)
set(NCNN_SHARED_LIB ON CACHE BOOL "Install the shared runtime" FORCE)
set(NCNN_INSTALL_SDK ON CACHE BOOL "Install headers and package metadata" FORCE)
set(NCNN_C_API ON CACHE BOOL "Install the C interface" FORCE)
set(NCNN_THREADS ON CACHE BOOL "Use POSIX synchronization" FORCE)
set(NCNN_OPENMP OFF CACHE BOOL "Serial inference profile" FORCE)
set(NCNN_SIMPLEOMP OFF CACHE BOOL "Do not install an emulated OpenMP runtime" FORCE)
set(NCNN_VULKAN OFF CACHE BOOL "CPU inference only" FORCE)
set(NCNN_RUNTIME_CPU OFF CACHE BOOL "Compile the baseline CPU implementation" FORCE)
foreach(feature ARM82 ARM82DOT ARM82FP16FML ARM84BF16 ARM84I8MM
        ARM86SVE ARM86SVE2 ARM86SVEBF16 ARM86SVEI8MM ARM86SVEF32MM
        AVX FMA XOP F16C AVX2 AVXVNNI AVXVNNIINT8 AVXVNNIINT16
        AVXNECONVERT AVX512 AVX512VNNI AVX512BF16 AVX512FP16)
    set(NCNN_${feature} OFF CACHE BOOL "Keep the baseline CPU instruction set" FORCE)
endforeach()
foreach(feature BUILD_TOOLS BUILD_EXAMPLES BUILD_BENCHMARK BUILD_TESTS PYTHON)
    set(NCNN_${feature} OFF CACHE BOOL "Build the runtime and installed SDK" FORCE)
endforeach()
