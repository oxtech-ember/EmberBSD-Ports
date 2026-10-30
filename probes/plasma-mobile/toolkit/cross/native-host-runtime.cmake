# SPDX-License-Identifier: BSD-2-Clause
# Route native custom commands through the selected Darwin stage runtime.
foreach(name QT_NATIVE_RUNTIME_PYTHON QT_NATIVE_RUNTIME_LAUNCHER QT_NATIVE_RUNTIME_VIEW)
    if(NOT DEFINED ENV{${name}} OR "$ENV{${name}}" STREQUAL "")
        message(FATAL_ERROR "Missing ${name} for the selected native runtime")
    endif()
endforeach()
set_property(GLOBAL PROPERTY RULE_LAUNCH_CUSTOM
    "$ENV{QT_NATIVE_RUNTIME_PYTHON} -I -S $ENV{QT_NATIVE_RUNTIME_LAUNCHER} --runtime-view $ENV{QT_NATIVE_RUNTIME_VIEW} --")
