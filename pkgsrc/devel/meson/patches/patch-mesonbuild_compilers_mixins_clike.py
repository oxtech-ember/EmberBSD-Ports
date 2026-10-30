$NetBSD$

Use the selected native lipo for Darwin architecture checks.

--- mesonbuild/compilers/mixins/clike.py.orig
+++ mesonbuild/compilers/mixins/clike.py
@@ -1106,7 +1106,11 @@
 
                 if env.machines.host.is_darwin() and env.machines.build.is_darwin():
                     # Run `lipo` and check if the library supports the arch we want
-                    archs = mesonlib.darwin_get_object_archs(p)
+                    selected_lipo = env.lookup_binary_entry(mesonlib.MachineChoice.BUILD, 'lipo')
+                    if selected_lipo is None and 'lipo' in env.binaries[mesonlib.MachineChoice.BUILD].binaries:
+                        raise mesonlib.MesonException('The selected lipo command is empty')
+                    lipo = ('lipo',) if selected_lipo is None else tuple(selected_lipo)
+                    archs = mesonlib.darwin_get_object_archs(p, lipo)
                     if not archs or env.machines.host.cpu_family not in archs:
                         mlog.debug(f'Rejected {p}, supports {archs} but need {env.machines.host.cpu_family}')
                         continue
