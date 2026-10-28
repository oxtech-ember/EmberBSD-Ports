# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Rewrite installed ICU metadata only.
# Match literal strings: host paths are not regular expressions.
function replace(text, old, new, pos, out) {
    if (old == "") return text;
    out = "";
    while ((pos = index(text, old)) != 0) {
        out = out substr(text, 1, pos - 1) new;
        text = substr(text, pos + length(old));
    }
    return out text;
}
{
    line = $0;
    line = replace(line, ENVIRON["ICU_BUILD_SHELL"], "/bin/sh");
    line = replace(line, ENVIRON["ICU_BUILD_INSTALL_DATA"], "/usr/bin/install -c -m 644");
    line = replace(line, ENVIRON["ICU_BUILD_INSTALL_PROGRAM"], "/usr/bin/install -c -s -m 755");
    line = replace(line, ENVIRON["ICU_BUILD_INSTALL_SCRIPT"], "/usr/bin/install -c -m 755");
    # The C compiler name can prefix the C++ one (clang, clang++).
    line = replace(line, ENVIRON["ICU_CROSS_CXX"], ENVIRON["ICU_TARGET_CXX"]);
    line = replace(line, ENVIRON["ICU_CROSS_CC"], ENVIRON["ICU_TARGET_CC"]);
    line = replace(line, ENVIRON["ICU_CROSS_TRIPLET"] "-ar", "/usr/bin/ar");
    line = replace(line, ENVIRON["ICU_CROSS_TRIPLET"] "-ranlib", "/usr/bin/ranlib");
    line = replace(line, ENVIRON["ICU_CROSS_SYSROOT"], "");
    print line;
}
