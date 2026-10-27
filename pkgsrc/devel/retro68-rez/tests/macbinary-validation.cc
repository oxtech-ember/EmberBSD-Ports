// SPDX-License-Identifier: GPL-3.0-or-later
#include "ResourceFile.h"
#include <sstream>
#include <string>

int main()
{
    ResourceFile source;
    source.type = ResType("TEST");
    source.creator = ResType("TEST");
    source.resources.addResource(Resource(ResType("TEST"), 1, "payload"));
    std::ostringstream output;
    if (!source.write(output, ResourceFile::Format::macbin)) return 1;
    const std::string bytes = output.str();
    std::istringstream valid(bytes);
    ResourceFile parsed;
    if (!parsed.read(valid, ResourceFile::Format::macbin) ||
        parsed.resources.countResources() != 1) return 2;
    for (size_t i = 0; i < 128; ++i) {
        std::istringstream truncated(bytes.substr(0, i));
        ResourceFile bad;
        if (bad.read(truncated, ResourceFile::Format::macbin)) return 3;
    }
    return 0;
}
