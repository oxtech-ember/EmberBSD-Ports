$NetBSD$

Use the matching buffer end when testing an invalid primitive.

--- test/OpenDDLParserTest.cpp.orig
+++ test/OpenDDLParserTest.cpp
@@ -311,7 +311,7 @@
     EXPECT_EQ(1U, len);
 
     size_t len2(0);
-    char invalidToken[] = "foat", *end2(findEnd(token1, len2));
+    char invalidToken[] = "foat", *end2(findEnd(invalidToken, len2));
     in = OpenDDLParser::parsePrimitiveDataType(invalidToken, end2, type, len);
     EXPECT_EQ(Value::ValueType::ddl_none, type);
     EXPECT_EQ(0U, len);
