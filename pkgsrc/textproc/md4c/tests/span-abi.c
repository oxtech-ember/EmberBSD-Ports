/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD contributors (AI-assisted); not submitted upstream. */
#include <md4c.h>
#include <string.h>

_Static_assert(MD_SPAN_EM == 0 && MD_SPAN_STRONG == 1 && MD_SPAN_A == 2 &&
    MD_SPAN_IMG == 3 && MD_SPAN_CODE == 4 && MD_SPAN_DEL == 5 &&
    MD_SPAN_LATEXMATH == 6 && MD_SPAN_LATEXMATH_DISPLAY == 7 &&
    MD_SPAN_WIKILINK == 8 && MD_SPAN_U == 9, "pre-0.6 span ABI changed");
_Static_assert(MD_SPAN_INS > MD_SPAN_U, "new span must not reuse old ordinal");

struct seen {
	int strike;
	int insert;
};

static int
block(MD_BLOCKTYPE type, void *detail, void *user)
{
	(void)type;
	(void)detail;
	(void)user;
	return 0;
}

static int
span(MD_SPANTYPE type, void *detail, void *user)
{
	struct seen *s = user;

	(void)detail;
	if (type == MD_SPAN_DEL)
		++s->strike;
	if (type == MD_SPAN_INS)
		++s->insert;
	return 0;
}

static int
text(MD_TEXTTYPE type, const MD_CHAR *value, MD_SIZE size, void *user)
{
	(void)type;
	(void)value;
	(void)size;
	(void)user;
	return 0;
}

int
main(void)
{
	const char input[] = "~~strike~~ ++insert++";
	struct seen seen = { 0, 0 };
	MD_PARSER parser = { 0, MD_FLAG_STRIKETHROUGH | MD_FLAG_INSERT,
	    block, block, span, span, text, NULL, NULL };

	if (md_parse(input, strlen(input), &parser, &seen) != 0)
		return 1;
	return seen.strike == 2 && seen.insert == 2 ? 0 : 2;
}
