# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Preserve a caller's existing Qt tool wrapper.
if(NOT DEFINED QT_TOOL_COMMAND_WRAPPER_PATH)
    if(NOT DEFINED ENV{QT_NATIVE_RUNTIME_WRAPPER} OR "$ENV{QT_NATIVE_RUNTIME_WRAPPER}" STREQUAL "")
        message(FATAL_ERROR "Missing the selected Qt native tool wrapper")
    endif()
    set(QT_TOOL_COMMAND_WRAPPER_PATH "$ENV{QT_NATIVE_RUNTIME_WRAPPER}" CACHE FILEPATH
        "Wrapper for Qt host tools")
endif()
