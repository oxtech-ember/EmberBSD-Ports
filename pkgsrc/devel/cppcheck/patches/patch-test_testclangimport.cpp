# Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
# Verify multi-file AST indices, language and pseudo-file coordinate boundaries.

--- test/testclangimport.cpp.orig
+++ test/testclangimport.cpp
@@ -131,6 +131,11 @@
         TEST_CASE(symbolDatabaseNodeType1);
         TEST_CASE(symbolDatabaseForVariable);
         TEST_CASE(stdinLoc);
+        TEST_CASE(pseudoFileLocations);
+        TEST_CASE(physicalFileLocations);
+        TEST_CASE(secondPseudoFileLocation);
+        TEST_CASE(invalidLocations);
+        TEST_CASE(multipleFiles);
 
         TEST_CASE(valueFlow1);
         TEST_CASE(valueFlow2);
@@ -1331,14 +1336,88 @@
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
+    void pseudoFileLocations() {
+        for (const std::string file : {"<built-in>", "<stdin>", "<scratch space>"}) {
+            const Settings settings = settingsBuilder().clang().build();
+            TokenList tokenlist{settings, Standards::Language::CPP};
+            tokenlist.appendFileIfNew("main.cpp");
+            Tokenizer tokenizer(std::move(tokenlist), *this);
+            std::istringstream ast("`-VarDecl 0x1 <" + file + ":42:1, col:5> col:5 value 'int'\n");
+            clangimport::parseClangAstDump(tokenizer, ast);
+            ASSERT_EQUALS(2U, tokenizer.list.getFiles().size());
+            ASSERT_EQUALS(file, tokenizer.list.getFiles()[1]);
+            ASSERT_EQUALS("main.cpp", tokenizer.list.getSourceFilePath());
+            ASSERT_EQUALS("int value@1 ;", tokenizer.tokens()->stringifyList(true, false, false, false, false));
+            for (const Token* tok = tokenizer.tokens(); tok; tok = tok->next()) {
+                ASSERT_EQUALS(1U, tok->fileIndex());
+                ASSERT_EQUALS(42U, tok->linenr());
+            }
+        }
+    }
+
+    void physicalFileLocations() {
+        for (const std::string file : {"/tmp/first<part.h", "<relative.h"}) {
+            const Settings settings = settingsBuilder().clang().build();
+            TokenList tokenlist{settings, Standards::Language::CPP};
+            tokenlist.appendFileIfNew("main.cpp");
+            Tokenizer tokenizer(std::move(tokenlist), *this);
+            std::istringstream ast("`-VarDecl 0x1 <" + file + ":42:1, col:5> col:5 value 'int'\n");
+            clangimport::parseClangAstDump(tokenizer, ast);
+            ASSERT_EQUALS(file, tokenizer.list.getFiles()[1]);
+            ASSERT_EQUALS("int value@1 ;", tokenizer.tokens()->stringifyList(true, false, false, false, false));
+            ASSERT_EQUALS(42U, tokenizer.tokens()->linenr());
+        }
+    }
+
+    void secondPseudoFileLocation() {
+        ASSERT_EQUALS("int value@1 ;", parse("`-VarDecl 0x1 <main.cpp:3:1, <scratch space>:42:5> col:5 value 'int'\n"));
+    }
+
+    void invalidLocations() {
+        ASSERT_THROW_INTERNAL_EQUALS(parse("`-VarDecl 0x1 <invalid> col:5 value 'int'\n"), AST,
+                                     "invalid AST location: <invalid>");
+        ASSERT_THROW_INTERNAL_EQUALS(parse("`-VarDecl 0x1 <<built-in>:42:1, col:5 col:5 value 'int'\n"), AST,
+                                     "unterminated AST location: <<built-in>:42:1, col:5 col:5 value 'int'");
+    }
+
     void stdinLoc() {
-        // we should never encounter this
         /*
            int i;
          */
         const char clang[] = "`-VarDecl 0x5776bb240470 <<stdin>:1:1, col:5> col:5 i 'int'\n";
 
-        ASSERT_THROW_INTERNAL_EQUALS(parse(clang), AST, "invalid AST location: <<stdin>");
+        ASSERT_EQUALS("int i@1 ;", parse(clang));
     }
 
     void crash() {
