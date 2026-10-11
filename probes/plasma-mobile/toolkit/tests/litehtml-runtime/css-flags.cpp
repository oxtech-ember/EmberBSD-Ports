// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted), regression for zero-index CSS flag shifts.
#include <gtest/gtest.h>
#include <litehtml.h>

struct FlagCase {
    const char *css;
    int expected;
};

TEST(LitehtmlCssFlags, TextDecoration)
{
    const FlagCase cases[] = {
        {"none", 0}, {"underline", 1}, {"overline", 2}, {"line-through", 4},
        {"underline overline line-through", 7}
    };
    for (const auto &item : cases) {
        SCOPED_TRACE(item.css);
        litehtml::style style;
        style.add_property(litehtml::_text_decoration_line_, item.css);
        const auto &value = style.get_property(litehtml::_text_decoration_line_);
        ASSERT_TRUE(value.is<int>());
        EXPECT_EQ(item.expected, value.get<int>());
    }
}

TEST(LitehtmlCssFlags, TextEmphasisPosition)
{
    const FlagCase cases[] = {
        {"over", 0}, {"under", 1}, {"left", 2}, {"right", 4},
        {"over right", 4}, {"under left", 3}
    };
    for (const auto &item : cases) {
        SCOPED_TRACE(item.css);
        litehtml::style style;
        style.add_property(litehtml::_text_emphasis_position_, item.css);
        const auto &value = style.get_property(litehtml::_text_emphasis_position_);
        ASSERT_TRUE(value.is<int>());
        EXPECT_EQ(item.expected, value.get<int>());
    }
}
