#!@PREFIX@/bin/mksh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Native assembler entry point for interfaces that accept one executable path.
exec @PREFIX@/bin/clang -c -x assembler "$@"
