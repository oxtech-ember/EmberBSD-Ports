// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD; malformed escaped-string error position regression.
#include <cassert>
#include <stdexcept>
#include <string>
#include <iostream>
#include "Parser.h"
int main()
{
    JSON::Parser parser;
    try {
        parser.parse("{\"name\":[1 \"\\n\"]}");
        return 1;
    } catch (const std::exception &error) {
        assert(std::string(error.what()) == "syntax error in JSON: expected ']'");
    }
    return 0;
}
