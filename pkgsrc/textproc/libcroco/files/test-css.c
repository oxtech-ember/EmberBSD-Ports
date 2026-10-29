/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted); upstream status: not submitted. */
#include <string.h>
#include <libcroco/libcroco.h>
static gboolean handler(CRSelEng *engine, CRAdditionalSel *sel, xmlNode *node) {
    (void)engine; (void)sel; (void)node; return TRUE;
}
int main(void) {
    const char *css = "p { color: red; background-color: white; }";
    CRStyleSheet *sheet = NULL;
    CRSelEng *engine;
    guchar name[] = "ember-test";
    if (cr_om_parser_simply_parse_buf((const guchar *)css, strlen(css), CR_UTF_8, &sheet) != CR_OK || sheet == NULL)
        return 1;
    cr_stylesheet_destroy(sheet);
    engine = cr_sel_eng_new();
    if (!engine || cr_sel_eng_register_pseudo_class_sel_handler(engine, name, IDENT_PSEUDO, handler) != CR_OK ||
        cr_sel_eng_unregister_pseudo_class_sel_handler(engine, name, IDENT_PSEUDO) != CR_OK)
        return 2;
    cr_sel_eng_destroy(engine);
    return 0;
}
