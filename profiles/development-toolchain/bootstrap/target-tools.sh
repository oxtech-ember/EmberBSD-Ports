#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Source with the audited kernel prefix, triplet and fail() function.
# ar and nm do not report a target triplet. Their audited prefix and hashes
# identify the provider; the caller separately checks target ELF inputs.
for bootstrap_tool in ar as ld nm objcopy objdump ranlib readelf strip; do
    bootstrap_executable=$kernel/bin/$triplet-$bootstrap_tool
    [ -x "$bootstrap_executable" ] || fail "Missing target binutils tool: $bootstrap_tool"
    bootstrap_version=$("$bootstrap_executable" --version) || fail "Cannot query target $bootstrap_tool"
    bootstrap_identity=$bootstrap_tool
    [ "$bootstrap_tool" != as ] || bootstrap_identity=assembler
    printf '%s\n' "$bootstrap_version" | grep -Eq "^GNU $bootstrap_identity[ (]" || \
        fail "Target $bootstrap_tool is not the selected GNU binutils tool"
    if [ "$bootstrap_tool" = as ]; then
        case "$bootstrap_version" in
            *"target of "*"$triplet"*) ;;
            *) fail 'GNU assembler target mismatch.';;
        esac
    fi
done
AR_FOR_TARGET=$kernel/bin/$triplet-ar
AS_FOR_TARGET=$kernel/bin/$triplet-as
LD_FOR_TARGET=$kernel/bin/$triplet-ld
NM_FOR_TARGET=$kernel/bin/$triplet-nm
OBJCOPY_FOR_TARGET=$kernel/bin/$triplet-objcopy
OBJDUMP_FOR_TARGET=$kernel/bin/$triplet-objdump
RANLIB_FOR_TARGET=$kernel/bin/$triplet-ranlib
READELF_FOR_TARGET=$kernel/bin/$triplet-readelf
STRIP_FOR_TARGET=$kernel/bin/$triplet-strip
export AR_FOR_TARGET AS_FOR_TARGET LD_FOR_TARGET NM_FOR_TARGET
export OBJCOPY_FOR_TARGET OBJDUMP_FOR_TARGET RANLIB_FOR_TARGET READELF_FOR_TARGET STRIP_FOR_TARGET
# GCC sub-configures can also search for the triplet-prefixed command name.
PATH=$kernel/bin:$PATH
export PATH
