EmberBSD local repair, AI-assisted; not submitted upstream.
The VariablePackage size is a parameter, not a package element.

--- source/components/disassembler/dmopcode.c.orig
+++ source/components/disassembler/dmopcode.c
@@ -859,6 +859,7 @@
         AcpiDmNamestring (Op->Common.Value.Name);
         /* If this namepath is a Package element, emit a separating comma */
         if ((Op->Common.Parent) &&
+            !(Op->Common.DisasmFlags & ACPI_PARSEOP_PARAMETER_LIST) &&
             ((Op->Common.Parent->Common.AmlOpcode == AML_PACKAGE_OP) ||
              (Op->Common.Parent->Common.AmlOpcode == AML_VARIABLE_PACKAGE_OP)))
         {
