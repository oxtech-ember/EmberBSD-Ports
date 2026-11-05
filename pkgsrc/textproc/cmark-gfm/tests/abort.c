#include <cmark-gfm.h>
#include <stddef.h>
#include <stdio.h>

static int parse(cmark_parser *parser, int should_abort)
{
    static const char input[] = "safe **text**\n";
    cmark_node *node;
    cmark_parser_feed(parser, input, sizeof(input) - 1);
    node = cmark_parser_finish(parser);
    if (!!node == !!should_abort) {
        fputs("unexpected parser result\n", stderr);
        if (node) cmark_node_free(node);
        return 1;
    }
    if (node) cmark_node_free(node);
    return 0;
}
int main(void)
{
    int flag = 1, failed = 0;
    cmark_parser *parser = cmark_parser_new(CMARK_OPT_DEFAULT);
    if (!parser) return 1;
    cmark_parser_set_allocation_abort_flag(parser, &flag);
    failed |= parse(parser, 1);
    flag = 0;
    failed |= parse(parser, 0);
    flag = 1;
    failed |= parse(parser, 1); /* reset retains the registered flag */
    cmark_parser_set_allocation_abort_flag(parser, NULL);
    failed |= parse(parser, 0); /* detach while original flag is still set */
    cmark_parser_free(parser);
    return failed != 0;
}
