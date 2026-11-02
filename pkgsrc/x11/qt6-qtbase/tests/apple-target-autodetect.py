#!/usr/bin/env python3
"""Check that pre-project Qt Apple autodetection follows the explicit target."""

from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} CMAKE QTBASE_SOURCE", file=sys.stderr)
        return 2

    cmake = sys.argv[1]
    source = Path(sys.argv[2]).resolve()
    helpers = source / "cmake/QtAutoDetectHelpers.cmake"
    apple_helpers = source / "cmake/QtPublicAppleHelpers.cmake"
    if not helpers.is_file() or not apple_helpers.is_file():
        raise SystemExit("QtBase CMake helper files are missing")

    cases = {
        "": True,
        "Darwin": True,
        "iOS": True,
        "tvOS": True,
        "watchOS": True,
        "visionOS": True,
        "NetBSD": False,
        "Linux": False,
        "Windows": False,
    }
    with tempfile.TemporaryDirectory(prefix="qt-apple-target-") as tmp:
        script = Path(tmp) / "probe.cmake"
        for system, expect_xcrun in cases.items():
            target = (
                f'set(CMAKE_SYSTEM_NAME "{system}")\n'
                if system
                else "unset(CMAKE_SYSTEM_NAME)\n"
            )
            script.write_text(
                "cmake_minimum_required(VERSION 3.16)\n"
                "set(APPLE TRUE)\n"
                "set(QT_NO_XCODE_MIN_VERSION_CHECK TRUE)\n"
                f'include("{helpers.as_posix()}")\n'
                f'include("{apple_helpers.as_posix()}")\n'
                "function(_qt_internal_execute_xcrun out_var)\n"
                "  set_property(GLOBAL APPEND PROPERTY qt_test_xcrun_calls stub)\n"
                "  set(${out_var} stub-result PARENT_SCOPE)\n"
                "endfunction()\n"
                f"{target}"
                "qt_auto_detect_apple()\n"
                "get_property(calls GLOBAL PROPERTY qt_test_xcrun_calls)\n"
                f"if({str(expect_xcrun).upper()} AND NOT calls)\n"
                f'  message(FATAL_ERROR "{system or "native Darwin"}: expected xcrun stub call")\n'
                f"elseif(NOT {str(expect_xcrun).upper()} AND calls)\n"
                f'  message(FATAL_ERROR "{system}: unexpected xcrun stub call")\n'
                "endif()\n"
            )
            result = subprocess.run(
                [cmake, "-P", str(script)], capture_output=True, text=True
            )
            if result.returncode:
                sys.stderr.write(result.stdout)
                sys.stderr.write(result.stderr)
                return result.returncode
            print(f"{system or 'native Darwin'}: {'Apple path' if expect_xcrun else 'cross skip'} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
