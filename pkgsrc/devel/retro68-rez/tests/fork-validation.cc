// SPDX-License-Identifier: GPL-3.0-or-later
#include "ResourceFork.h"
#include <sstream>
#include <string>

int main()
{
    Resources empty;
    std::ostringstream emptyOut;
    empty.writeFork(emptyOut);
    Resources emptyParsed;
    if (!emptyParsed.readChecked(emptyOut.str()) || emptyParsed.countResources() != 0)
        return 5;
    Resources original;
    original.addResource(Resource(ResType("TEST"), 42, "payload", "name", 32));
    std::ostringstream out;
    original.writeFork(out);
    std::string fork = out.str();
    Resources parsed;
    if (!parsed.readChecked(fork) || parsed.countResources() != 1)
        return 1;
    const Resource& item = parsed.resources.begin()->second;
    if (item.getData() != "payload" || item.getName() != "name" || item.getAttr() != 32)
        return 4;
    for (size_t i = 0; i < fork.size(); ++i) {
        Resources truncated;
        if (truncated.readChecked(fork.substr(0, i)))
            return 2;
    }
    fork[4] = static_cast<char>(0x7f);
    Resources invalid;
    return invalid.readChecked(fork) ? 3 : 0;
}
