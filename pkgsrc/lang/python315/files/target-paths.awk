# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed target compiler inputs.
# Literal matching also handles sysroot names containing regexp characters.
BEGIN { if (sysroot == "" || sysroot == "/") exit 2 }
/CONFIG_ARGS/ { print; next }
{
    rest = $0
    output = ""
    while ((position = index(rest, sysroot "/")) != 0) {
        output = output substr(rest, 1, position - 1)
        rest = substr(rest, position + length(sysroot))
    }
    print output rest
}
