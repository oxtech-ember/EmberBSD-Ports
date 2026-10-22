$NetBSD$

Use native GI generators and real EmberBSD queries; preserve the full thumbnailer.
Native and unselected cross builds retain their existing execution paths.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- build-aux/gen-thumbnailer.py.orig
+++ build-aux/gen-thumbnailer.py
@@ -17,6 +17,8 @@
 argparser.add_argument('input', help='Template file')
 argparser.add_argument('output', help='Output file')
 
+argparser.add_argument('--runner', nargs=2, help='Validated target runner and interpreter')
+
 args = argparser.parse_args()
 
 newenv = os.environ.copy()
@@ -27,9 +29,13 @@
     gdk_pixbuf_dll_buildpath = os.path.dirname(args.pixdata)
     newenv['PATH'] = gdk_pixbuf_dll_buildpath + os.pathsep + newenv['PATH']
 
-cmd = args.printer
+cmd = ([args.runner[0], '-E', '-S', args.runner[1], '--mime',
+        args.printer, args.loaders] if args.runner else args.printer)
 
-mimetypes_out = subprocess.Popen(cmd, env=newenv, stdout=subprocess.PIPE).communicate()[0]
+process = subprocess.Popen(cmd, env=newenv, stdout=subprocess.PIPE)
+mimetypes_out = process.communicate()[0]
+if process.returncode != 0:
+    sys.exit(process.returncode)
 if not mimetypes_out:
     sys.exit(1)
 
