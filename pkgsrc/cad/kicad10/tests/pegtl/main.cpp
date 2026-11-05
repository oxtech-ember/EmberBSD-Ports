// SPDX-License-Identifier: ISC
// Exercise KiCad's real grammars and input/error policy against the shared PEGTL.
#undef NDEBUG
#include <kicad_pegtl.h>
#include <libraries/library_table_grammar.h>
#include <common/io/cadstar/cadstar_parts_lib_grammar.h>
#include <cassert>
#include <iostream>

namespace peg = tao::pegtl;
struct LETTER : peg::one<'a'> {};
struct LINE : peg::must<LETTER, peg::eol, LETTER, peg::eof> {};
template<typename Rule>
using SELECTOR = peg::parse_tree::selector<Rule, peg::parse_tree::store_content::on<LETTER>>;
struct CUSTOM_NODE : peg::parse_tree::basic_node<CUSTOM_NODE, KICAD_PEGTL::TEXT_INPUT::error_position_t> {};

template<typename Input>
void check_error(Input& input)
{
    bool caught = false;
    try {
        (void) peg::parse<LINE>(input);
    } catch (const peg::parse_error<typename Input::error_position_t>& error) {
        const auto& position = error.position_object();
        assert(position.line == 2 && position.column == 1);
        assert(position.source == "board.lib");
        assert(input.line_view_at(position) == "b");
        caught = true;
    }
    assert(caught);
}

int main()
{
    for (const std::string newline : {"\n", "\r\n"}) {
        std::string invalid = "a" + newline + "b";
        KICAD_PEGTL::TEXT_INPUT copy("board.lib", invalid);
        check_error(copy);
        KICAD_PEGTL::TEXT_VIEW view("board.lib", invalid);
        check_error(view);
        KICAD_PEGTL::TEXT_INPUT valid("board.lib", "a" + newline + "a");
        auto tree = peg::parse_tree::parse<LINE, CUSTOM_NODE, SELECTOR>(valid);
        assert(tree && tree->children.size() == 2);
        assert(tree->children[0]->string() == "a");
        assert(tree->children[1]->begin.line == 2);
    }
    KICAD_PEGTL::TEXT_INPUT table("sym-lib-table",
        "(sym_lib_table (version 7) (lib (name \"Device\")(type \"KiCad\")(uri \"Device.kicad_sym\")))");
    assert(peg::parse<LIBRARY_TABLE_GRAMMAR::LIB_TABLE_FILE>(table));
    KICAD_PEGTL::TEXT_INPUT broken("sym-lib-table", "(sym_lib_table (lib (name \"unterminated");
    bool rejected = false;
    try {
        (void) peg::parse<LIBRARY_TABLE_GRAMMAR::LIB_TABLE_FILE>(broken);
    } catch (const peg::parse_error_base&) {
        rejected = true;
    }
    assert(rejected);
    KICAD_PEGTL::TEXT_INPUT header("parts.lib", ".FORMAT 32\n");
    assert(peg::parse<CADSTAR_PARTS_LIB::VALID_HEADER>(header));
    KICAD_PEGTL::TEXT_INPUT diagnostic("parts.lib", "invalid");
    try {
        peg::throw_parse_error("Duplicate attribute name", diagnostic);
    } catch (const peg::parse_error<KICAD_PEGTL::TEXT_INPUT::error_position_t>& error) {
        assert(error.position_object().line == 1);
        assert(error.message() == "Duplicate attribute name");
    }
    std::cout << "KiCad PEGTL: library and CADSTAR grammars, parse trees, LF/CRLF diagnostics passed\n";
}
