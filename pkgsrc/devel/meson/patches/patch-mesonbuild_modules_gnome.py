$NetBSD$

Resolve introspection executables on the build machine while keeping the
introspection dependency itself selected for the target machine.

--- mesonbuild/modules/gnome.py.orig
+++ mesonbuild/modules/gnome.py
@@ -323,4 +323,9 @@
         }
         depname = tool_map[tool]
         varname = tool.replace('-', '_')
+        if tool in ('g-ir-scanner', 'g-ir-compiler'):
+            # These are executable build tools. The introspection dependency
+            # is resolved separately by _get_gir_dep() for the host/target ABI.
+            return state.find_program(tool, required=required,
+                                      for_machine=MachineChoice.BUILD)
         return state.find_tool(tool, depname, varname, required=required, native=depname != "gobject-introspection-1.0")
