$NetBSD$

Preserve NetBSD and EmberBSD byacc integration changes from the OS source.
Regenerate with the patched skeleton and upstream skel2c.
Origin: NetBSD and EmberBSD (AI-assisted); not submitted upstream.

--- btyaccpar.c.orig
+++ btyaccpar.c
@@ -2,7 +2,7 @@
  * @Id: skel2c,v 1.4 2016/06/07 00:26:09 tom Exp @
  */
 
-/* @Id: btyaccpar.skel,v 1.12 2021/06/19 20:46:31 tom Exp @ */
+/* @Id: btyaccpar.skel,v 1.13 2021/08/08 19:56:28 tom Exp @ */
 
 #include "defs.h"
 
@@ -16,7 +16,7 @@
 
 const char *const banner[] =
 {
-    "/* original parser id follows */",
+    "/* EmberBSD parser skeleton; original parser id follows. */",
     "/* yysccsid[] = \"@(#)yaccpar	1.9 (Berkeley) 02/21/93\" */",
     "/* (use YYMAJOR/YYMINOR for ifdefs dependent on parser version) */",
     "",
@@ -33,14 +33,14 @@
     "#define YYRECOVERING() (yyerrflag != 0)",
     "#define YYENOMEM       (-2)",
     "#define YYEOF          0",
-    NULL
+    0
 };
 
 const char *const xdecls[] =
 {
     "",
     "extern int YYPARSE_DECL();",
-    NULL
+    0
 };
 
 const char *const tables[] =
@@ -72,7 +72,7 @@
     "#if YYDEBUG",
     "extern const char *const yyrule[];",
     "#endif",
-    NULL
+    0
 };
 
 const char *const global_vars[] =
@@ -81,7 +81,7 @@
     "#if YYDEBUG",
     "int      yydebug;",
     "#endif",
-    NULL
+    0
 };
 
 const char *const impure_vars[] =
@@ -97,7 +97,7 @@
     "YYLTYPE  yyloc; /* position returned by actions */",
     "YYLTYPE  yylloc; /* position from the lexer */",
     "#endif",
-    NULL
+    0
 };
 
 const char *const hdr_defs[] =
@@ -178,7 +178,7 @@
     "typedef struct YYParseState_s YYParseState;",
     "#endif /* YYBTYACC */",
 #endif			/* defined(YYBTYACC) */
-    NULL
+    0
 };
 
 const char *const hdr_vars[] =
@@ -189,44 +189,44 @@
     "#if YYBTYACC",
     "",
     "/* Current parser state */",
-    "static YYParseState *yyps = NULL;",
+    "static YYParseState *yyps = 0;",
     "",
     "/* yypath != NULL: do the full parse, starting at *yypath parser state. */",
-    "static YYParseState *yypath = NULL;",
+    "static YYParseState *yypath = 0;",
     "",
     "/* Base of the lexical value queue */",
-    "static YYSTYPE *yylvals = NULL;",
+    "static YYSTYPE *yylvals = 0;",
     "",
     "/* Current position at lexical value queue */",
-    "static YYSTYPE *yylvp = NULL;",
+    "static YYSTYPE *yylvp = 0;",
     "",
     "/* End position of lexical value queue */",
-    "static YYSTYPE *yylve = NULL;",
+    "static YYSTYPE *yylve = 0;",
     "",
     "/* The last allocated position at the lexical value queue */",
-    "static YYSTYPE *yylvlim = NULL;",
+    "static YYSTYPE *yylvlim = 0;",
     "",
     "#if defined(YYLTYPE) || defined(YYLTYPE_IS_DECLARED)",
     "/* Base of the lexical position queue */",
-    "static YYLTYPE *yylpsns = NULL;",
+    "static YYLTYPE *yylpsns = 0;",
     "",
     "/* Current position at lexical position queue */",
-    "static YYLTYPE *yylpp = NULL;",
+    "static YYLTYPE *yylpp = 0;",
     "",
     "/* End position of lexical position queue */",
-    "static YYLTYPE *yylpe = NULL;",
+    "static YYLTYPE *yylpe = 0;",
     "",
     "/* The last allocated position at the lexical position queue */",
-    "static YYLTYPE *yylplim = NULL;",
+    "static YYLTYPE *yylplim = 0;",
     "#endif",
     "",
     "/* Current position at lexical token queue */",
-    "static YYINT  *yylexp = NULL;",
-    "",
-    "static YYINT  *yylexemes = NULL;",
-    "#endif /* YYBTYACC */",
-#endif			/* defined(YYBTYACC) */
-    NULL
+    "static YYINT  *yylexp = 0;",
+    "",
+    "static YYINT  *yylexemes = 0;",
+    "#endif /* YYBTYACC */",
+#endif			/* defined(YYBTYACC) */
+    0
 };
 
 const char *const body_vars[] =
@@ -248,44 +248,44 @@
     "#if YYBTYACC",
     "",
     "    /* Current parser state */",
-    "    static YYParseState *yyps = NULL;",
+    "    static YYParseState *yyps = 0;",
     "",
     "    /* yypath != NULL: do the full parse, starting at *yypath parser state. */",
-    "    static YYParseState *yypath = NULL;",
+    "    static YYParseState *yypath = 0;",
     "",
     "    /* Base of the lexical value queue */",
-    "    static YYSTYPE *yylvals = NULL;",
+    "    static YYSTYPE *yylvals = 0;",
     "",
     "    /* Current position at lexical value queue */",
-    "    static YYSTYPE *yylvp = NULL;",
+    "    static YYSTYPE *yylvp = 0;",
     "",
     "    /* End position of lexical value queue */",
-    "    static YYSTYPE *yylve = NULL;",
+    "    static YYSTYPE *yylve = 0;",
     "",
     "    /* The last allocated position at the lexical value queue */",
-    "    static YYSTYPE *yylvlim = NULL;",
+    "    static YYSTYPE *yylvlim = 0;",
     "",
     "#if defined(YYLTYPE) || defined(YYLTYPE_IS_DECLARED)",
     "    /* Base of the lexical position queue */",
-    "    static YYLTYPE *yylpsns = NULL;",
+    "    static YYLTYPE *yylpsns = 0;",
     "",
     "    /* Current position at lexical position queue */",
-    "    static YYLTYPE *yylpp = NULL;",
+    "    static YYLTYPE *yylpp = 0;",
     "",
     "    /* End position of lexical position queue */",
-    "    static YYLTYPE *yylpe = NULL;",
+    "    static YYLTYPE *yylpe = 0;",
     "",
     "    /* The last allocated position at the lexical position queue */",
-    "    static YYLTYPE *yylplim = NULL;",
+    "    static YYLTYPE *yylplim = 0;",
     "#endif",
     "",
     "    /* Current position at lexical token queue */",
-    "    static YYINT  *yylexp = NULL;",
-    "",
-    "    static YYINT  *yylexemes = NULL;",
-    "#endif /* YYBTYACC */",
-#endif			/* defined(YYBTYACC) */
-    NULL
+    "    static YYINT  *yylexp = 0;",
+    "",
+    "    static YYINT  *yylexemes = 0;",
+    "#endif /* YYBTYACC */",
+#endif			/* defined(YYBTYACC) */
+    0
 };
 
 const char *const body_1[] =
@@ -326,14 +326,14 @@
     "",
     "    i = (int) (data->s_mark - data->s_base);",
     "    newss = (YYINT *)realloc(data->s_base, newsize * sizeof(*newss));",
-    "    if (newss == NULL)",
+    "    if (newss == 0)",
     "        return YYENOMEM;",
     "",
     "    data->s_base = newss;",
     "    data->s_mark = newss + i;",
     "",
     "    newvs = (YYSTYPE *)realloc(data->l_base, newsize * sizeof(*newvs));",
-    "    if (newvs == NULL)",
+    "    if (newvs == 0)",
     "        return YYENOMEM;",
     "",
     "    data->l_base = newvs;",
@@ -341,7 +341,7 @@
     "",
     "#if defined(YYLTYPE) || defined(YYLTYPE_IS_DECLARED)",
     "    newps = (YYLTYPE *)realloc(data->p_base, newsize * sizeof(*newps));",
-    "    if (newps == NULL)",
+    "    if (newps == 0)",
     "        return YYENOMEM;",
     "",
     "    data->p_base = newps;",
@@ -380,6 +380,7 @@
     "    YYParseState *p = (YYParseState *) malloc(sizeof(YYParseState));",
     "    if (p == NULL) return NULL;",
     "",
+    "    memset(&p->yystack, 0, sizeof(p->yystack));",
     "    p->yystack.stacksize = size;",
     "    if (size == 0)",
     "    {",
@@ -391,17 +392,26 @@
     "        return p;",
     "    }",
     "    p->yystack.s_base    = (YYINT *) malloc(size * sizeof(YYINT));",
-    "    if (p->yystack.s_base == NULL) return NULL;",
+    "    if (p->yystack.s_base == NULL) goto fail;",
     "    p->yystack.l_base    = (YYSTYPE *) malloc(size * sizeof(YYSTYPE));",
-    "    if (p->yystack.l_base == NULL) return NULL;",
+    "    if (p->yystack.l_base == NULL) goto fail;",
     "    memset(p->yystack.l_base, 0, size * sizeof(YYSTYPE));",
     "#if defined(YYLTYPE) || defined(YYLTYPE_IS_DECLARED)",
     "    p->yystack.p_base    = (YYLTYPE *) malloc(size * sizeof(YYLTYPE));",
-    "    if (p->yystack.p_base == NULL) return NULL;",
+    "    if (p->yystack.p_base == NULL) goto fail;",
     "    memset(p->yystack.p_base, 0, size * sizeof(YYLTYPE));",
     "#endif",
     "",
     "    return p;",
+    "",
+    "fail:",
+    "    free(p->yystack.s_base);",
+    "    free(p->yystack.l_base);",
+    "#if defined(YYLTYPE) || defined(YYLTYPE_IS_DECLARED)",
+    "    free(p->yystack.p_base);",
+    "#endif",
+    "    free(p);",
+    "    return NULL;",
     "}",
     "",
     "static void",
@@ -428,7 +438,7 @@
     "int",
     "YYPARSE_DECL()",
     "{",
-    NULL
+    0
 };
 
 const char *const body_2[] =
@@ -446,7 +456,7 @@
     "#if YYDEBUG",
     "    const char *yys;",
     "",
-    "    if ((yys = getenv(\"YYDEBUG\")) != NULL)",
+    "    if ((yys = getenv(\"YYDEBUG\")) != 0)",
     "    {",
     "        yyn = *yys;",
     "        if (yyn >= '0' && yyn <= '9')",
@@ -459,7 +469,7 @@
     "    memset(yyerror_loc_range, 0, sizeof(yyerror_loc_range));",
     "#endif",
     "",
-    NULL
+    0
 };
 
 const char *const init_vars[] =
@@ -473,27 +483,28 @@
     "    memset(&yylloc, 0, sizeof(yylloc));",
     "#endif",
     "",
-    NULL
+    0
 };
 
 const char *const body_3[] =
 {
-#if defined(YYBTYACC)
-    "#if YYBTYACC",
-    "    yyps = yyNewState(0); if (yyps == NULL) goto yyenomem;",
-    "    yyps->save = NULL;",
+    "#if YYPURE",
+    "    memset(&yystack, 0, sizeof(yystack));",
+    "#endif",
+    "",
+#if defined(YYBTYACC)
+    "#if YYBTYACC",
+    "    yyps = yyNewState(0); if (yyps == 0) goto yyenomem;",
+    "    yyps->save = 0;",
     "#endif /* YYBTYACC */",
 #endif			/* defined(YYBTYACC) */
     "    yym = 0;",
     "    /* yyn is set below */",
     "    yynerrs = 0;",
+    "    (void)yynerrs; /* User actions may omit the error count. */",
     "    yyerrflag = 0;",
     "    yychar = YYEMPTY;",
     "    yystate = 0;",
-    "",
-    "#if YYPURE",
-    "    memset(&yystack, 0, sizeof(yystack));",
-    "#endif",
     "",
     "    if (yystack.s_base == NULL && yygrowstack(&yystack) == YYENOMEM) goto yyoverflow;",
     "    yystack.s_mark = yystack.s_base;",
@@ -528,20 +539,29 @@
     "            {   /* Enlarge lexical value queue */",
     "                size_t p = (size_t) (yylvp - yylvals);",
     "                size_t s = (size_t) (yylvlim - yylvals);",
+    "                YYINT *new_lexemes;",
+    "                YYSTYPE *new_vals;",
+    "#if defined(YYLTYPE) || defined(YYLTYPE_IS_DECLARED)",
+    "                YYLTYPE *new_psns;",
+    "#endif",
     "",
     "                s += YYLVQUEUEGROWTH;",
-    "                if ((yylexemes = (YYINT *)realloc(yylexemes, s * sizeof(YYINT))) == NULL) goto yyenomem;",
-    "                if ((yylvals   = (YYSTYPE *)realloc(yylvals, s * sizeof(YYSTYPE))) == NULL) goto yyenomem;",
-    "#if defined(YYLTYPE) || defined(YYLTYPE_IS_DECLARED)",
-    "                if ((yylpsns   = (YYLTYPE *)realloc(yylpsns, s * sizeof(YYLTYPE))) == NULL) goto yyenomem;",
-    "#endif",
+    "                new_lexemes = (YYINT *)realloc(yylexemes, s * sizeof(YYINT));",
+    "                if (new_lexemes == NULL) goto yyenomem;",
+    "                yylexemes = new_lexemes;",
+    "                yylexp = yylexemes + p;",
+    "                new_vals = (YYSTYPE *)realloc(yylvals, s * sizeof(YYSTYPE));",
+    "                if (new_vals == NULL) goto yyenomem;",
+    "                yylvals = new_vals;",
     "                yylvp   = yylve = yylvals + p;",
     "                yylvlim = yylvals + s;",
     "#if defined(YYLTYPE) || defined(YYLTYPE_IS_DECLARED)",
+    "                new_psns = (YYLTYPE *)realloc(yylpsns, s * sizeof(YYLTYPE));",
+    "                if (new_psns == NULL) goto yyenomem;",
+    "                yylpsns = new_psns;",
     "                yylpp   = yylpe = yylpsns + p;",
     "                yylplim = yylpsns + s;",
     "#endif",
-    "                yylexp  = yylexemes + p;",
     "            }",
     "            *yylexp = (YYINT) YYLEX;",
     "            *yylvp++ = yylval;",
@@ -1011,7 +1031,7 @@
     "",
     "    switch (yyn)",
     "    {",
-    NULL
+    0
 };
 
 const char *const trailer[] =
@@ -1071,23 +1091,32 @@
     "                {   /* Enlarge lexical value queue */",
     "                    size_t p = (size_t) (yylvp - yylvals);",
     "                    size_t s = (size_t) (yylvlim - yylvals);",
+    "                    YYINT *new_lexemes;",
+    "                    YYSTYPE *new_vals;",
+    "#if defined(YYLTYPE) || defined(YYLTYPE_IS_DECLARED)",
+    "                    YYLTYPE *new_psns;",
+    "#endif",
     "",
     "                    s += YYLVQUEUEGROWTH;",
-    "                    if ((yylexemes = (YYINT *)realloc(yylexemes, s * sizeof(YYINT))) == NULL)",
+    "                    new_lexemes = (YYINT *)realloc(yylexemes, s * sizeof(YYINT));",
+    "                    if (new_lexemes == NULL)",
     "                        goto yyenomem;",
-    "                    if ((yylvals   = (YYSTYPE *)realloc(yylvals, s * sizeof(YYSTYPE))) == NULL)",
+    "                    yylexemes = new_lexemes;",
+    "                    yylexp = yylexemes + p;",
+    "                    new_vals = (YYSTYPE *)realloc(yylvals, s * sizeof(YYSTYPE));",
+    "                    if (new_vals == NULL)",
     "                        goto yyenomem;",
-    "#if defined(YYLTYPE) || defined(YYLTYPE_IS_DECLARED)",
-    "                    if ((yylpsns   = (YYLTYPE *)realloc(yylpsns, s * sizeof(YYLTYPE))) == NULL)",
-    "                        goto yyenomem;",
-    "#endif",
+    "                    yylvals = new_vals;",
     "                    yylvp   = yylve = yylvals + p;",
     "                    yylvlim = yylvals + s;",
     "#if defined(YYLTYPE) || defined(YYLTYPE_IS_DECLARED)",
+    "                    new_psns = (YYLTYPE *)realloc(yylpsns, s * sizeof(YYLTYPE));",
+    "                    if (new_psns == NULL)",
+    "                        goto yyenomem;",
+    "                    yylpsns = new_psns;",
     "                    yylpp   = yylpe = yylpsns + p;",
     "                    yylplim = yylpsns + s;",
     "#endif",
-    "                    yylexp  = yylexemes + p;",
     "                }",
     "                *yylexp = (YYINT) YYLEX;",
     "                *yylvp++ = yylval;",
@@ -1266,7 +1295,7 @@
     "    yyfreestack(&yystack);",
     "    return (yyresult);",
     "}",
-    NULL
+    0
 };
 
 void
@@ -1275,7 +1304,7 @@
     int i;
     const char *s;
 
-    for (i = 0; (s = section[i]) != NULL; ++i)
+    for (i = 0; (s = section[i]) != 0; ++i)
     {
 	if (fp == code_file)
 	    ++outline;
