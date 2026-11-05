/* Exercise the installed cmark parser with and without an explicit depth cap. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <cmark-gfm.h>

static int
check(cmark_parser *parser, size_t expected)
{
    char input[1202], *html, *p;
    size_t i, count = 0;
    cmark_node *node;

    for (i = 0; i < 600; ++i) {
        input[2 * i] = '>';
        input[2 * i + 1] = ' ';
    }
    input[1200] = 'a';
    input[1201] = '\n';
    cmark_parser_feed(parser, input, sizeof(input));
    node = cmark_parser_finish(parser);
    if (!node)
        return 1;
    html = cmark_render_html(node, CMARK_OPT_DEFAULT, NULL);
    cmark_node_free(node);
    if (!html)
        return 1;
    for (p = html; (p = strstr(p, "<blockquote>")) != NULL; p += 12)
        ++count;
    free(html);
    if (count != expected) {
        fprintf(stderr, "expected %zu blockquotes, got %zu\n", expected, count);
        return 1;
    }
    return 0;
}

int
main(void)
{
    cmark_parser *parser = cmark_parser_new(CMARK_OPT_DEFAULT);
    int failure;
    if (!parser)
        return 1;
    failure = check(parser, 600);
    cmark_parser_set_max_block_quote_depth(parser, 512);
    failure |= check(parser, 511);
    failure |= check(parser, 511); /* finish resets parser but preserves policy */
    cmark_parser_set_max_block_quote_depth(parser, 0);
    failure |= check(parser, 600);
    cmark_parser_free(parser);
    return failure != 0;
}
