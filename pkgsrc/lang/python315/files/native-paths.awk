# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Publish native Python extension settings.
function replace_literal(line, old, new,    at, result) {
    while ((at = index(line, old)) > 0) {
        result = result substr(line, 1, at - 1) new
        line = substr(line, at + length(old))
    }
    return result line
}
BEGIN {
    if (work !~ /^\/.+/ || source !~ /^\/.+/ || ports !~ /^\/.+/ || prefix !~ /^\/.+/)
        exit 2
}
{
    line = replace_literal($0, work "/.tools/bin/", "")
    line = replace_literal(line, work "/.cwrapper/bin/", "")
    line = replace_literal(line, work "/.buildlink", prefix)
    line = replace_literal(line, source, ".")
    line = replace_literal(line, work, ".")
    line = replace_literal(line, ports, "/usr/pkgsrc")
    if (owner != "" && group != "")
        line = replace_literal(line, " -o " owner " -g " group, "")
    print line
}
