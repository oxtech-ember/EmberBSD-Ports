# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Native GCC16 selection for host generators.
# Source this file, then call: ember_require_host_gcc16 VARIABLE c|c++
# The variable must name an absolute native GCC16 driver. There is no
# /usr/bin/cc, PATH or Clang fallback. See host-gcc16.md.
ember_require_host_gcc16() {
    _ember_name=$1 _ember_lang=$2
    eval "_ember_tool=\${$_ember_name:-}"
    [ -n "$_ember_tool" ] || {
        echo "$_ember_name is required: select the native GCC16 driver (no /usr/bin/cc or Clang fallback)" >&2; exit 2; }
    case "$_ember_tool" in /*) ;; *) echo "$_ember_name must be an absolute path: $_ember_tool" >&2; exit 2;; esac
    [ -f "$_ember_tool" ] && [ -x "$_ember_tool" ] || {
        echo "$_ember_name is not an executable file: $_ember_tool" >&2; exit 2; }
    _ember_real=$(CDPATH= cd -- "$(dirname -- "$_ember_tool")" && pwd -P)/$(basename -- "$_ember_tool")
    for _ember_path in "$_ember_tool" "$_ember_real"; do
        case "$_ember_path" in
        /usr/bin/*|/usr/local/*|/opt/homebrew/*|/opt/local/*|/Library/Developer/*|/Applications/Xcode*)
            echo "$_ember_name selects a system or package-manager compiler: $_ember_path" >&2; exit 2;;
        esac
    done
    _ember_macros=$("$_ember_tool" -x "$_ember_lang" -dM -E /dev/null) || {
        echo "$_ember_name cannot preprocess $_ember_lang: $_ember_tool" >&2; exit 2; }
    case "$_ember_macros" in *"#define __clang__ "*)
        echo "$_ember_name is Clang, not native GCC16: $_ember_tool" >&2; exit 2;;
    esac
    case "$_ember_macros" in *"#define __GNUC__ 16"*) ;; *)
        echo "$_ember_name is not GCC16: $_ember_tool" >&2; exit 2;;
    esac
    case "$("$_ember_tool" --version 2>&1)" in *[Cc]lang*|*LLVM*|*Apple*)
        echo "$_ember_name reports Clang, LLVM or Apple: $_ember_tool" >&2; exit 2;;
    esac
}
