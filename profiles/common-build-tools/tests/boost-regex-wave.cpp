// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.
// Origin: EmberBSD (AI-assisted).
#include <boost/regex.hpp>
#include <boost/wave.hpp>
#include <boost/wave/cpplexer/cpp_lex_iterator.hpp>
#include <boost/wave/cpplexer/cpp_lex_token.hpp>
#include <string>

int main()
{
    boost::regex expression("[a-z]+[0-9]+");
    if (!boost::regex_match(std::string("abc42"), expression) ||
        boost::regex_match(std::string("abc"), expression))
        return 1;
    std::string source = "#define VALUE 42\nVALUE\n";
    using token = boost::wave::cpplexer::lex_token<>;
    using lexer = boost::wave::cpplexer::lex_iterator<token>;
    boost::wave::context<std::string::iterator, lexer> context(
        source.begin(), source.end(), "test.cpp");
    std::string result;
    for (auto it = context.begin(); it != context.end(); ++it)
        result += (*it).get_value().c_str();
    return result.find("42") == std::string::npos;
}
