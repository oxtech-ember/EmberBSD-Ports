# Origin: EmberBSD (AI-assisted).
Use equivalent string indexing for the selected date format.

--- src/rcstime.c.orig
+++ src/rcstime.c
@@ -99,8 +99,8 @@
     continue;
   if (!BE (zone_offset.valid))
     sprintf (datebuf,
-             ("19%.*s/%.2s/%.2s %.2s:%.2s:%s"
-              + (date[2] == '.' && VERSION (5) <= BE (version) ? 0 : 2)),
+             &"19%.*s/%.2s/%.2s %.2s:%.2s:%s"
+              [date[2] == '.' && VERSION (5) <= BE (version) ? 0 : 2],
              (int) (p - date - 1), date, p, p + 3, p + 6, p + 9, p + 12);
   else
     {
