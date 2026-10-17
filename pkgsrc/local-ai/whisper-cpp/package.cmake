# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), shared whisper.cpp package features.
foreach(option IN ITEMS WHISPER_BUILD_IS_DEV WHISPER_BUILD_TESTS
    WHISPER_BUILD_SERVER WHISPER_CURL WHISPER_SDL2 WHISPER_COMMON_FFMPEG
    WHISPER_COREML WHISPER_OPENVINO)
    set(${option} OFF CACHE BOOL "Installed CPU execution tools")
endforeach()
set(WHISPER_BUILD_EXAMPLES ON CACHE BOOL "Install the CPU execution tools")
