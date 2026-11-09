// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <cstddef>
#include <string>
#include <string_view>
#include <UniConversion.h>

extern "C" int scintilla_core_contract()
{
    using namespace Scintilla::Internal;
    const std::string text = "A\xc3\xa9\xf0\x9f\x98\x80"; // A, e acute, grinning face
    if (!UTF8IsValid(text) || UTF32Length(text) != 3 || UTF16Length(text) != 4)
        return 1;
    unsigned int points[3] = {};
    if (UTF32FromUTF8(text, points, 3) != 3 || points[0] != 'A' ||
        points[1] != 0xe9 || points[2] != 0x1f600)
        return 2;
    if (UTF8PositionFromUTF16Position(text, 2) != 3)
        return 3;
    if (UTF8IsValid("\xc0\x80") || UTF8IsValid("\xf0\x9f"))
        return 4;
    if (!UTF8IsValid(FixInvalidUTF8("x\xffy")))
        return 5;
    if (!UTF8IsValid("") || UTF32Length("") != 0 || UTF16Length("") != 0)
        return 6;
    return 0;
}
