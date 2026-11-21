$NetBSD: patch-src_pip___internal_commands_install.py,v 1.1 2023/06/14 11:30:54 riastradh Exp $

Allow pip install --executable=/path to set path in script #! lines.
https://github.com/pypa/pip/issues/12087
https://github.com/pypa/pip/pull/12088

--- src/pip/_internal/commands/install.py.orig
+++ src/pip/_internal/commands/install.py
@@ -411,6 +411,14 @@
                 "environment."
             ),
         )
+        self.cmd_opts.add_option(
+            "--executable",
+            dest="executable_path",
+            default=None,
+            help=(
+                "Path to executable for #! lines in scripts."
+            ),
+        )
 
         self.cmd_opts.add_option(cmdoptions.src())
 
@@ -737,6 +745,7 @@
                 root=options.root_path,
                 home=target_temp_dir_path,
                 prefix=options.prefix_path,
+                script_executable=options.executable_path,
                 warn_script_location=warn_script_location,
                 use_user_site=options.use_user_site,
                 pycompile=options.compile,
