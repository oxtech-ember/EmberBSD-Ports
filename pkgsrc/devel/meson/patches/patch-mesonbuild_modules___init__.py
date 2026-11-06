$NetBSD$

Select binary overrides from the requested Meson machine.

--- mesonbuild/modules/__init__.py.orig
+++ mesonbuild/modules/__init__.py
@@ -101,7 +101,7 @@ class ModuleState:
         if progobj is not None:
             return progobj
 
         # Look in machine file
-        prog_list = self.environment.lookup_binary_entry(MachineChoice.HOST, name)
+        prog_list = self.environment.lookup_binary_entry(for_machine, name)
         if prog_list is not None:
             return ExternalProgram.from_entry(name, prog_list)
