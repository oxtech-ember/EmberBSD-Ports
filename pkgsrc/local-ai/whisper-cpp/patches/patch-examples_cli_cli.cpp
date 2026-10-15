$NetBSD$

Report output stream errors through the existing input failure status.
Check open, write, flush, and close errors for every selected format.
Let the shared output factory close the karaoke stream too.

--- examples/cli/cli.cpp.orig	2026-10-15 00:00:00.000000000 +0000
+++ examples/cli/cli.cpp
@@ -927,8 +927,6 @@ static bool output_wts(struct whisper_context * ctx,
     fout << "echo \"  ffplay " << fname_inp << ".mp4\"\n";
     fout << "\n";
 
-    fout.close();
-
     fprintf(stderr, "# %s: run 'source %s' to generate karaoke video\n", __func__, fname_out);
 
     return true;
@@ -1159,6 +1157,11 @@ int main(int argc, char ** argv) {
 #endif
                     // Not using fprintf stderr here because it might equal stdout
                     // Also assuming /dev is mounted
+                    if (!fout.is_open()) {
+                        fprintf(stderr, "%s: failed to open standard output for writing\n", function);
+                        failed = true;
+                        return false;
+                    }
                     return true;
                 }
 
@@ -1173,6 +1176,16 @@ int main(int argc, char ** argv) {
                 fprintf(stderr, "%s: saving output to '%s'\n", function, fname_out.c_str());
                 return true;
             }
+
+            void close(const char * function) {
+                fout.flush();
+                fout.close();
+                if (fout.fail()) {
+                    fprintf(stderr, "%s: failed to write '%s'\n", function,
+                            is_stdout ? "standard output" : fname_out.c_str());
+                    failed = true;
+                }
+            }
         } fout_factory{f < (int) params.fname_out.size() ? params.fname_out[f] : "", fname_inp, params};
 
         std::vector<float> pcmf32;               // mono-channel F32 PCM
@@ -1341,6 +1354,7 @@ int main(int argc, char ** argv) {
             // macros to stringify function name
 #define output_func(func, ext, param, ...) if (param && fout_factory.open(ext, #func)) {\
     func(ctx, fout_factory.fout, params, __VA_ARGS__); \
+    fout_factory.close(#func); \
 }
 #define output_ext(ext, ...) output_func(output_##ext, "." #ext, params.output_##ext, __VA_ARGS__)
 
