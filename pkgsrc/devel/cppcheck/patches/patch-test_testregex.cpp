$NetBSD$

Keep Cppcheck capabilities with shared current dependencies.
Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

--- test/testregex.cpp.orig
+++ test/testregex.cpp
@@ -23,6 +23,7 @@
 
 #include <list>
 #include <memory>
+#include <stdexcept>
 #include <string>
 #include <utility>
 
@@ -41,6 +42,13 @@
         TEST_CASE(multimatch);
         TEST_CASE(partialmatch);
         TEST_CASE(exactmatch);
+        TEST_CASE(emptyMatch);
+        TEST_CASE(emptySubject);
+        TEST_CASE(lookAround);
+        TEST_CASE(manyCaptures);
+        TEST_CASE(utfEmptyMatch);
+        TEST_CASE(matchError);
+        TEST_CASE(callbackException);
     }
 
 #define assertRegex(...) assertRegex_(__FILE__, __LINE__, __VA_ARGS__)
@@ -193,7 +201,59 @@
         ASSERT_EQUALS(3, e);
     }
 
-    // TODO: how to provoke a match() error?
+
+    void emptyMatch() const {
+        const auto r = assertRegex("a*");
+        std::string spans;
+        ASSERT_EQUALS("", r->match("b", [&](int s, int e) { spans += std::to_string(s) + ":" + std::to_string(e) + ","; }));
+        ASSERT_EQUALS("0:0,1:1,", spans);
+    }
+
+    void emptySubject() const {
+        const auto r = assertRegex("");
+        int called = 0;
+        ASSERT_EQUALS("", r->match("", [&](int s, int e) { ++called; ASSERT_EQUALS(0, s); ASSERT_EQUALS(0, e); }));
+        ASSERT_EQUALS(1, called);
+    }
+
+    void lookAround() const {
+        const auto r = assertRegex("(?<=foo)bar(?=!)");
+        int called = 0;
+        ASSERT_EQUALS("", r->match("foobar!", [&](int s, int e) { ++called; ASSERT_EQUALS(3, s); ASSERT_EQUALS(6, e); }));
+        ASSERT_EQUALS(1, called);
+    }
+
+    void manyCaptures() const {
+        std::string pattern;
+        for (int i = 0; i < 20; ++i) pattern += "(a)";
+        const auto r = assertRegex(pattern);
+        int called = 0;
+        ASSERT_EQUALS("", r->match(std::string(20, 'a'), [&](int s, int e) { ++called; ASSERT_EQUALS(0, s); ASSERT_EQUALS(20, e); }));
+        ASSERT_EQUALS(1, called);
+    }
+
+    void utfEmptyMatch() const {
+        const auto r = assertRegex("(*UTF)(?=.)");
+        std::string spans;
+        ASSERT_EQUALS("", r->match("\xc3\xa9x", [&](int s, int e) { spans += std::to_string(s) + ":" + std::to_string(e) + ","; }));
+        ASSERT_EQUALS("0:0,2:2,", spans);
+    }
+
+    void matchError() const {
+        const auto r = assertRegex("(*UTF).");
+        int called = 0;
+        ASSERT(!r->match(std::string(1, '\xff'), [&](int, int) { ++called; }).empty());
+        ASSERT_EQUALS(0, called);
+    }
+
+    void callbackException() const {
+        const auto r = assertRegex("a");
+        auto callback = [](int, int) { throw std::runtime_error("callback"); };
+        ASSERT_THROW_EQUALS(r->match("a", callback), std::runtime_error, "callback");
+        int called = 0;
+        ASSERT_EQUALS("", r->match("a", [&](int, int) { ++called; }));
+        ASSERT_EQUALS(1, called);
+    }
 
 #undef assertRegex
 };
