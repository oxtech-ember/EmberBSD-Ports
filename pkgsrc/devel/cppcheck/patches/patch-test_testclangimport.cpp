# Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
# Verify streamed multi-file AST indices, source identity and language stability.

--- test/testclangimport.cpp.orig
+++ test/testclangimport.cpp
@@ -131,6 +131,7 @@
         TEST_CASE(symbolDatabaseNodeType1);
         TEST_CASE(symbolDatabaseForVariable);
         TEST_CASE(stdinLoc);
+        TEST_CASE(multipleFiles);
 
         TEST_CASE(valueFlow1);
         TEST_CASE(valueFlow2);
@@ -1331,6 +1332,37 @@
         ASSERT_EQUALS("const char *", tok->valueType()->str());
     }
 
+    void multipleFiles() {
+        const Settings settings = settingsBuilder().clang().build();
+        TokenList tokenlist{settings, Standards::Language::CPP};
+        tokenlist.appendFileIfNew("main.cpp");
+        Tokenizer tokenizer(std::move(tokenlist), *this);
+        std::istringstream ast(
+            "|-VarDecl 0x1 <first.c:3:1, col:5> col:5 a 'int'\n"
+            "|-VarDecl 0x2 <second.h:7:1, col:5> col:5 b 'int'\n"
+            "|-VarDecl 0x3 <first.c:9:1, col:5> col:5 c 'int'\n"
+            "`-VarDecl 0x4 <main.cpp:12:1, col:5> col:5 d 'int'\n");
+        clangimport::parseClangAstDump(tokenizer, ast);
+        ASSERT_EQUALS("int a@1 ; int b@2 ; int c@3 ; int d@4 ;",
+                      tokenizer.tokens()->stringifyList(true, false, false, false, false));
+        const std::vector<std::string> expectedFiles = {"main.cpp", "first.c", "second.h"};
+        ASSERT(tokenizer.list.getFiles() == expectedFiles);
+        ASSERT_EQUALS("main.cpp", tokenizer.list.getSourceFilePath());
+        const unsigned int expectedIndex[] = {1, 2, 1, 0};
+        const unsigned int expectedLine[] = {3, 7, 9, 12};
+        const Token* tok = tokenizer.tokens();
+        for (unsigned int i = 0; i != 4; ++i) {
+            for (unsigned int j = 0; j != 3; ++j) {
+                ASSERT(tok);
+                ASSERT_EQUALS(expectedIndex[i], tok->fileIndex());
+                ASSERT_EQUALS(expectedLine[i], tok->linenr());
+                ASSERT(tok->isCpp());
+                tok = tok->next();
+            }
+        }
+        ASSERT(!tok);
+    }
+
     void stdinLoc() {
         // we should never encounter this
         /*
