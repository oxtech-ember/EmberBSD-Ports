# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), shared llama.cpp package features.
foreach(option IN ITEMS LLAMA_BUILD_IS_DEV LLAMA_BUILD_TESTS LLAMA_BUILD_EXAMPLES
    LLAMA_BUILD_APP LLAMA_BUILD_UI LLAMA_USE_PREBUILT_UI LLAMA_OPENSSL
    LLAMA_SUBPROCESS)
    set(${option} OFF CACHE BOOL "Installed CPU execution tools")
endforeach()
set(LLAMA_BUILD_SERVER ON CACHE BOOL "Install the loopback HTTP server")
