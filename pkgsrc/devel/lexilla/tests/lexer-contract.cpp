// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <cstring>
#include <initializer_list>
#include <memory>
#include <string>
#include <string_view>
#include <vector>
#include <ILexer.h>
#include <Lexilla.h>
#include <LexillaAccess.h>

struct ReleaseLexer {
    void operator()(Scintilla::ILexer5 *lexer) const { lexer->Release(); }
};

int main()
{
    if (GetLexerCount() <= 0 || CreateLexer("emberbsd-not-a-lexer") != nullptr)
        return 1;
    bool python = false, cpp = false, json = false;
    for (int i = 0; i < GetLexerCount(); ++i) {
        char name[128] = {};
        GetLexerName(i, name, sizeof(name));
        if (!name[0] || name[sizeof(name) - 1] != '\0')
            return 2;
        python |= std::strcmp(name, "python") == 0;
        cpp |= std::strcmp(name, "cpp") == 0;
        json |= std::strcmp(name, "json") == 0;
    }
    if (!python || !cpp || !json)
        return 3;
    for (const char *name : {"python", "cpp", "json"}) {
        std::unique_ptr<Scintilla::ILexer5, ReleaseLexer> lexer(Lexilla::MakeLexer(name));
        if (!lexer || std::strcmp(lexer->GetName(), name) != 0)
            return 4;
        if (lexer->Version() < Scintilla::lvRelease5)
            return 5;
    }
    return 0;
}
