// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted), external-token append regression.
#include <rapidjson/document.h>
#include <rapidjson/pointer.h>
#include <cstdio>

int main() {
    const rapidjson::Pointer::Token tokens[] = {
        {"foo", 3, rapidjson::kPointerInvalidIndex}, {"0", 1, 0}
    };
    rapidjson::Pointer p(tokens, 2);
    rapidjson::Pointer q = p.Append("tail");
    if (!(q == rapidjson::Pointer("/foo/0/tail"))) return 1;
    if (q.GetTokens()[0].name == tokens[0].name) return 2;
    std::puts("PASS: append copies externally owned token names.");
    return 0;
}
