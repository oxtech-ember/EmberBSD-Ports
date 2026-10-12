#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted source-derived generated-header PLIST contract.
set -eu
[ "$#" = 3 ] || {
    echo "Usage: $0 VERIFIED_LLVM_SOURCE RECIPE_ROOT NEW_WORK" >&2; exit 2;
}
source=$(CDPATH= cd -- "$1" && pwd)
recipes=$(CDPATH= cd -- "$2" && pwd)
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
llvm=$source/llvm/CMakeLists.txt
clang=$source/clang/CMakeLists.txt
basic=$source/clang/include/clang/Basic/CMakeLists.txt
analysis=$source/llvm/include/llvm/Analysis/CMakeLists.txt
extensions=$source/llvm/cmake/modules/AddLLVM.cmake

# Prove the binary-tree install scope before interpreting generation declarations.
# This is a release-specific source contract, not a general CMake interpreter.
sed -n '/install(DIRECTORY ${LLVM_INCLUDE_DIR}\/llvm /,/^    )/p' "$llvm" > "$work/llvm-install"
sed -n '/install(DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}\/include\/clang$/,/^    )/p' "$clang" > "$work/clang-install"
for suffix in def h inc; do
    grep -Fq "PATTERN \"*.$suffix\"" "$work/llvm-install"
done
grep -Fq 'PATTERN "config.h" EXCLUDE' "$work/llvm-install"
grep -Fq 'PATTERN "*.inc"' "$work/clang-install"
grep -Fq 'process_llvm_pass_plugins(GEN_CONFIG)' "$llvm"
grep -Fq '"${ExtensionDef}")' "$extensions"
grep -Fq 'file(WRITE "${ExtensionDef}.tmp"' "$extensions"

# Config outputs survive the source-only header refresh; config.h is excluded.
awk '/\$\{LLVM_INCLUDE_DIR\}\/llvm\/Config\// {
    path=$1; sub(/^\$\{LLVM_INCLUDE_DIR\}\//, "include/", path);
    sub(/\)$/, "", path); if (path !~ /\/config\.h$/) { print path; n++ }
} END { if (!n) exit 1
}' "$llvm" > "$work/llvm-expected"
awk '/^tablegen\(LLVM / {
    path=$2; if (path ~ /\.inc$/) { print "include/llvm/Analysis/" path; n++ }
} END { if (!n) exit 1
}' "$analysis" >> "$work/llvm-expected"
awk '/set\(ExtensionDef / {
    path=$2; sub(/^"\$\{LLVM_BINARY_DIR\}\//, "", path);
    sub(/"\)$/, "", path); print path; n++
} END { if (!n) exit 1
}' "$extensions" >> "$work/llvm-expected"

# Include every directly related Basic output, including diagnostic macro calls.
# JSON is generated but deliberately outside the upstream *.inc install rule.
awk '
    /clang_tablegen\(/ {
        path=$1; sub(/^clang_tablegen\(/, "", path);
        if (path ~ /\.inc$/ && path !~ /\$/) {
            print "include/clang/Basic/" path; tables++
        } else if (path ~ /\$\{component\}/) {
            diagnostic_template[++templates]=path
        }
    }
    /^clang_diag_gen\(/ {
        component=$1; sub(/^clang_diag_gen\(/, "", component); sub(/\)$/, "", component);
        diagnostics++;
        for (i=1; i<=templates; i++) {
            path=diagnostic_template[i]; gsub(/\$\{component\}/, component, path);
            print "include/clang/Basic/" path
        }
    }
    END { if (!tables || !diagnostics || !templates) exit 1 }
' "$basic" > "$work/clang-expected"

# LLVM 23 moved driver options and added Sema-generated attribute metadata.
for directory in Options Sema; do
    awk -v directory="$directory" '
        /clang_tablegen\(/ || /^tablegen\(LLVM / {
            path=$1; sub(/^clang_tablegen\(/, "", path);
            if ($1 == "tablegen(LLVM") path=$2;
            if (path ~ /\.inc$/ && path !~ /\$/) {
                print "include/clang/" directory "/" path; n++
            }
        }
        END { if (!n) exit 1 }
    ' "$source/clang/include/clang/$directory/CMakeLists.txt" >> "$work/clang-expected"
done
! grep -Fxq 'include/clang/Driver/Options.inc' "$recipes/lang/clang/PLIST"
# The upstream offload alias belongs to LLVM, not to a second Clang package.
grep -Fq 'add_llvm_tool_symlink(clang-offload-packager' \
    "$source/llvm/tools/llvm-offload-binary/CMakeLists.txt"
grep -Fxq 'bin/clang-offload-packager' "$recipes/lang/llvm/PLIST"
! grep -Fxq 'bin/clang-offload-packager' "$recipes/lang/clang/PLIST"

failed=0
for project in llvm clang; do
    LC_ALL=C sort -u "$work/$project-expected" > "$work/$project-outputs"
    [ -s "$work/$project-outputs" ]
    while IFS= read -r output; do
        if ! grep -Fxq "$output" "$recipes/lang/$project/PLIST"; then
            echo "FAIL: $project PLIST missing generated $output"
            failed=1
        fi
    done < "$work/$project-outputs"
    printf '%s: %s source-declared installed outputs checked\n' "$project" \
        "$(wc -l < "$work/$project-outputs" | tr -d ' ')"
done
[ "$failed" = 0 ] || exit 1
echo 'PASS: related generated-header PLIST declarations; native staging/check-files pending'
