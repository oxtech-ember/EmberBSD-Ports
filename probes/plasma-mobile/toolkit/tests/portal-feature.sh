#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise Qt's actual portal feature condition.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 QT_SOURCE NEW_WORK" >&2; exit 2; }
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
awk '/^qt_feature\("xdg-desktop-portal-file-transfer" / { copy=1 }
    copy { print; if ($0 == ")") exit }' "$1/src/gui/configure.cmake" > "$work/feature.cmake"
[ -s "$work/feature.cmake" ]
cat > "$work/check.cmake" <<'CMAKE'
cmake_minimum_required(VERSION 3.19)
function(qt_feature name)
    cmake_parse_arguments(PARSE_ARGV 1 arg "PRIVATE" "LABEL" "CONDITION")
    if(${arg_CONDITION})
        set(actual ON)
    else()
        set(actual OFF)
    endif()
    if(NOT actual STREQUAL expected)
        message(FATAL_ERROR "${name}: expected ${expected}, got ${actual}")
    endif()
endfunction()
set(cases 0)
foreach(TEST_o_path ON OFF)
    foreach(QT_FEATURE_wayland ON OFF)
        foreach(QT_FEATURE_dbus ON OFF)
            foreach(QT_FEATURE_clipboard ON OFF)
                foreach(QT_FEATURE_draganddrop ON OFF)
                    set(expected OFF)
                    if(TEST_o_path AND QT_FEATURE_wayland AND QT_FEATURE_dbus)
                        if(QT_FEATURE_clipboard OR QT_FEATURE_draganddrop)
                            set(expected ON)
                        endif()
                    endif()
                    include("${CMAKE_CURRENT_LIST_DIR}/feature.cmake")
                    math(EXPR cases "${cases} + 1")
                endforeach()
            endforeach()
        endforeach()
    endforeach()
endforeach()
message(STATUS "PASS: ${cases} actual Qt portal feature selection cases")
CMAKE
"${CMAKE:-cmake}" -P "$work/check.cmake"
