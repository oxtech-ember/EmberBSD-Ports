/* Exercise the installed Gumbo parser interface with ordinary HTML inputs. */
#include <gumbo.h>
#include <assert.h>
#include <stdint.h>
#include <string.h>

static void
check(const char *html, const GumboLimits *limits, bool truncated)
{
    GumboOutput *out = gumbo_parse_with_limits(&kGumboDefaultOptions, html,
        strlen(html), limits);
    assert(out && out->document && out->root);
    assert(out->truncated == truncated);
    gumbo_destroy_output(&kGumboDefaultOptions, out);
}

static GumboNode *
child_tag(GumboNode *parent, GumboTag tag)
{
    for (unsigned int i = 0; i < parent->v.element.children.length; ++i) {
        GumboNode *child = parent->v.element.children.data[i];
        if (child->type == GUMBO_NODE_ELEMENT && child->v.element.tag == tag)
            return child;
    }
    assert(0 && "expected an element in the parsed tree");
    return NULL;
}

static void
check_selectedcontent(const GumboLimits *limits, bool truncated)
{
    const char html[] = "<select><button><selectedcontent></button>"
        "<option><span>one</span></option></select>";
    GumboOutput *out = gumbo_parse_with_limits(&kGumboDefaultOptions, html,
        sizeof(html) - 1, limits);
    assert(out && out->root && out->truncated == truncated);
    GumboNode *select = child_tag(child_tag(out->root, GUMBO_TAG_BODY), GUMBO_TAG_SELECT);
    GumboNode *selected = child_tag(child_tag(select, GUMBO_TAG_BUTTON), GUMBO_TAG_SELECTEDCONTENT);
    if (!truncated) {
        GumboNode *span = child_tag(selected, GUMBO_TAG_SPAN);
        GumboNode *original = child_tag(child_tag(select, GUMBO_TAG_OPTION), GUMBO_TAG_SPAN);
        assert(span != original && span->v.element.children.length == 1);
        GumboNode *text = span->v.element.children.data[0];
        assert(text->type == GUMBO_NODE_TEXT && strcmp(text->v.text.text, "one") == 0);
    }
    gumbo_destroy_output(&kGumboDefaultOptions, out);
}

int
main(void)
{
    /* html/body and this nested list coexist on the parser's stack. */
    const char list[] = "<ul><li><p>one</p></li></ul>";
    /* HTML reconstructs the active <b> in the next paragraph. */
    const char format[] = "<p><b>x</p><p>y</p>";
    const GumboLimits normal = {400, 1U << 20};
    const GumboLimits shallow = {2, SIZE_MAX};
    const GumboLimits no_extra_clone_bytes = {400, 0};
    const GumboLimits large = {400, SIZE_MAX};
    check(list, &normal, false);
    check(list, &shallow, true);
    check(format, &normal, false);
    check(format, &no_extra_clone_bytes, true);
    check(format, &large, false);
    check(format, NULL, false);
    check_selectedcontent(&normal, false);
    check_selectedcontent(&no_extra_clone_bytes, true);
    GumboOutput *legacy = gumbo_parse(list);
    assert(legacy && legacy->root && !legacy->truncated);
    gumbo_destroy_output(&kGumboDefaultOptions, legacy);
    return 0;
}
