Origin: EmberBSD (AI-assisted), fix dictionary suffix lengths reported by Cppcheck.
Both .spcl and .special contain multi-dictionary directives. Comparing six
characters with these five/eight-character suffixes always rejected them.
The installed regression loads both extensions and rejects an unknown format.

--- modules/speller/default/data.cpp.orig
+++ modules/speller/default/data.cpp
@@ -375,14 +375,14 @@
     }
     DataType actual_type;
     if ((true_file_name.size() > 5
-	 && true_file_name.substr(true_file_name.size() - 6, 6) == ".spcl") 
+	 && true_file_name.substr(true_file_name.size() - 5, 5) == ".spcl") 
 	||
 	(true_file_name.size() > 6 
 	 && (true_file_name.substr(true_file_name.size() - 6, 6) == ".multi" 
 	     || true_file_name.substr(true_file_name.size() - 6, 6) == ".alias")) 
 	||
 	(true_file_name.size() > 8
-	 && true_file_name.substr(true_file_name.size() - 6, 6) == ".special")) 
+	 && true_file_name.substr(true_file_name.size() - 8, 8) == ".special")) 
     {
 
       actual_type = DT_Multi;
