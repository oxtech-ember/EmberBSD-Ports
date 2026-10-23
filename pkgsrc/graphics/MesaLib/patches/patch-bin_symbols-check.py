Origin: EmberBSD; AI-assisted Mesa 26.2.4 test adaptation.
Status: local; not submitted upstream.

Apply the ELF bookkeeping-symbol allowlist to NetBSD. Select the target
system explicitly for cross checks; native invocation retains its default.
Meson passes host_machine.system(), so macOS hosts can inspect NetBSD ELF.
Missing API symbols and unrelated extra exports still fail the check.

--- bin/symbols-check.py.orig
+++ bin/symbols-check.py
@@ -75,26 +75,25 @@
 ]
 
 
-def get_symbols_nm(nm, lib):
+def get_symbols_nm(nm, lib, platform_name):
     '''
     List all the (non platform-specific) symbols exported by the library
     using `nm`
     '''
     symbols = []
-    platform_name = platform.system()
     output = subprocess.check_output([nm, '-gP', lib],
                                      stderr=open(os.devnull, 'w')).decode("ascii")
     for line in output.splitlines():
         if line.startswith(' '):
             continue
         fields = line.split()
-        if len(fields) >= 2 and fields[1] == 'U':
+        if len(fields) >= 2 and fields[1] in ('U', 'w', 'v'):
             continue
         symbol_name = fields[0]
-        if platform_name == 'Linux' or platform_name == 'GNU' or platform_name.startswith('GNU/'):
+        if platform_name in ('linux', 'netbsd') or platform_name == 'gnu' or platform_name.startswith('gnu/'):
             if symbol_name.split('@')[0] in PLATFORM_SYMBOLS:
                 continue
-        elif platform_name == 'Darwin':
+        elif platform_name == 'darwin':
             assert symbol_name[0] == '_'
             symbol_name = symbol_name[1:]
         symbols.append(symbol_name)
@@ -169,9 +168,13 @@
     parser.add_argument('--ignore-symbol',
                         action='append',
                         help='do not process this symbol')
+    parser.add_argument('--target-system',
+                        default=platform.system().lower(),
+                        type=str.lower,
+                        help='target OS (defaults to the build host OS)')
     args = parser.parse_args()
 
-    if platform.system() == 'Windows':
+    if args.target_system == 'windows':
         if args.dumpbin:
             lib_symbols = get_symbols_dumpbin(args.dumpbin, args.lib)
         elif args.gendef:
@@ -181,7 +184,7 @@
     else:
         if not args.nm:
             parser.error('--nm is mandatory')
-        lib_symbols = get_symbols_nm(args.nm, args.lib)
+        lib_symbols = get_symbols_nm(args.nm, args.lib, args.target_system)
 
     mandatory_symbols = []
     optional_symbols = []
--- meson.build.orig
+++ meson.build
@@ -2509,6 +2509,10 @@
   endif
 endif
 
+if with_symbols_check
+  symbols_check_args += ['--target-system', host_machine.system()]
+endif
+
 # This quirk needs to be applied to sources with functions defined in assembly
 # as GCC LTO drops them. See: https://bugs.freedesktop.org/show_bug.cgi?id=109391
 gcc_lto_quirk = (cc.get_id() == 'gcc') ? ['-fno-lto'] : []
