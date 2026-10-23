$NetBSD: patch-mesonbuild_dependencies_dev.py,v 1.8 2026/04/19 17:14:21 wiz Exp $

Honor explicit LLVM selection without alternate config-tool or CMake fallback. Preserve machine-file precedence; native paths do not select cross-target tools.
Origin: pkgsrc adaptation by EmberBSD, AI-assisted.

--- mesonbuild/dependencies/dev.py.orig
+++ mesonbuild/dependencies/dev.py
@@ -182,6 +182,11 @@
         super().__init__(name, environment, kwargs)
 
 
+def _llvm_config_path_applies(env: 'Environment', for_machine: MachineChoice) -> bool:
+    # A native tool must never select the target tool during a cross build.
+    return 'LLVM_CONFIG_PATH' in os.environ and (for_machine is mesonlib.MachineChoice.BUILD or not env.is_cross_build())
+
+
 class LLVMDependencyConfigTool(ConfigToolDependency):
     """
     LLVM uses a special tool, llvm-config, which has arguments for getting
@@ -192,16 +197,21 @@
 
     def __init__(self, name: str, environment: 'Environment', kwargs: DependencyObjectKWs):
         kwargs['language'] = 'cpp'
-        self.tools = get_llvm_tool_names('llvm-config')
-
-        # Fedora starting with Fedora 30 adds a suffix of the number
-        # of bits in the isa that llvm targets, for example, on x86_64
-        # and aarch64 the name will be llvm-config-64, on x86 and arm
-        # it will be llvm-config-32.
-        if environment.machines[kwargs['native']].is_64_bit:
-            self.tools.append('llvm-config-64')
+        for_machine = kwargs['native']
+        if environment.lookup_binary_entry(for_machine, 'llvm-config') is not None:
+            # Keep upstream's machine-file precedence, including failures.
+            self.tools = ['llvm-config']
+        elif _llvm_config_path_applies(environment, for_machine):
+            path = os.environ['LLVM_CONFIG_PATH']
+            if not os.path.isabs(path):
+                raise DependencyException('LLVM_CONFIG_PATH must be an absolute executable path')
+            self.tools = [path]
         else:
-            self.tools.append('llvm-config-32')
+            self.tools = get_llvm_tool_names('llvm-config')
+            if environment.machines[for_machine].is_64_bit:
+                self.tools.append('llvm-config-64')
+            else:
+                self.tools.append('llvm-config-32')
 
         # It's necessary for LLVM <= 3.8 to use the C++ linker. For 3.9 and 4.0
         # the C linker works fine if only using the C API.
@@ -387,6 +397,10 @@
 
 class LLVMDependencyCMake(CMakeDependency):
     def __init__(self, name: str, env: 'Environment', kwargs: DependencyObjectKWs) -> None:
+        for_machine = kwargs['native']
+        if (env.lookup_binary_entry(for_machine, 'llvm-config') is not None or
+                _llvm_config_path_applies(env, for_machine)):
+            raise DependencyException('Explicit llvm-config selection requires the config-tool method')
         kwargs['language'] = 'cpp'
         self.llvm_modules = kwargs.get('modules', [])
         self.llvm_opt_modules = kwargs.get('optional_modules', [])
