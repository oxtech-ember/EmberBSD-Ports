// SPDX-License-Identifier: 0BSD
// Origin: EmberBSD contributors (AI-assisted).
#include <simplecpp.h>
#ifndef __GLIBCXX__
#error This regression requires the selected GCC libstdc++ provider
#endif
#ifndef _GLIBCXX_DEBUG
#error The common SimpleCpp target must propagate the checked ABI
#endif

int main()
{
    std::vector<std::string> files;
    simplecpp::TokenList tokens(files);
    return tokens.cfront() != nullptr;
}
