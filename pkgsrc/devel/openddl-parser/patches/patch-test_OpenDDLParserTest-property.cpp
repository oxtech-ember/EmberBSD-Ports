$NetBSD$

Exercise truncated and invalid property values (EmberBSD, AI-assisted).

--- test/OpenDDLParserTest.cpp.orig
+++ test/OpenDDLParserTest.cpp
@@ -584,6 +584,16 @@
     delete prop;
 }
 
+TEST_F(OpenDDLParserTest, parseInvalidPropertyBoundaryTest) {
+    char empty[] = { 'k', '=' };
+    Property *prop = nullptr;
+    EXPECT_EQ(empty + sizeof(empty), OpenDDLParser::parseProperty(empty, empty + sizeof(empty), &prop));
+    EXPECT_EQ(nullptr, prop);
+    char invalid[] = { 'k', '=', ' ', '?', 'x' };
+    EXPECT_EQ(invalid + 3, OpenDDLParser::parseProperty(invalid, invalid + sizeof(invalid), &prop));
+    EXPECT_EQ(nullptr, prop);
+}
+
 TEST_F(OpenDDLParserTest, parseDataArrayListTest) {
     char token[] =
             "{\n"
