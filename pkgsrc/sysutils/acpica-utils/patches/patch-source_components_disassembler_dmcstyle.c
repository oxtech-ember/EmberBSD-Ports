EmberBSD local repair, AI-assisted; not submitted upstream.
Preserve logical-not and Store grouping and valid Index source syntax.

--- source/components/disassembler/dmcstyle.c.orig
+++ source/components/disassembler/dmcstyle.c
@@ -184,9 +184,10 @@
 
         default:
 
-            /* Unary LNOT case, emit "!" immediately */
-
-            AcpiOsPrintf ("!");
+            /* Group the operand to preserve its AML nesting. */
+
+            AcpiOsPrintf ("!(");
+            Op->Common.DisasmFlags |= ACPI_PARSEOP_CLOSING_PAREN;
             return (TRUE);
         }
 
@@ -206,15 +207,14 @@
 
     case AML_INDEX_OP:
         /*
-         * Check for constant source operand. Note: although technically
-         * legal syntax, the iASL compiler does not support this with
-         * the symbolic operators for Index(). It doesn't make sense to
-         * use Index() with a constant anyway.
+         * iASL symbolic Index requires a SuperName source. Constants and
+         * Store expressions must use the legacy Index() form.
          */
         if ((Argument1->Common.AmlOpcode == AML_STRING_OP)  ||
             (Argument1->Common.AmlOpcode == AML_BUFFER_OP)  ||
             (Argument1->Common.AmlOpcode == AML_PACKAGE_OP) ||
-            (Argument1->Common.AmlOpcode == AML_VARIABLE_PACKAGE_OP))
+            (Argument1->Common.AmlOpcode == AML_VARIABLE_PACKAGE_OP) ||
+            (Argument1->Common.AmlOpcode == AML_STORE_OP))
         {
             Op->Common.DisasmFlags |= ACPI_PARSEOP_CLOSING_PAREN;
             return (FALSE);
@@ -510,6 +510,8 @@
             return (FALSE);
         }
 
+        AcpiOsPrintf ("(");
+        Op->Common.DisasmFlags |= ACPI_PARSEOP_CLOSING_PAREN;
         AcpiDmPromoteTarget (Op, Target);
         if (!Target->Common.OperatorSymbol)
         {
@@ -754,13 +756,27 @@
         ASL_CV_PRINT_ONE_COMMENT (Op, AML_COMMENT_END_NODE, NULL, 0);
         return;
 
+    case AML_LOGICAL_NOT_OP:
+        if (Op->Common.DisasmFlags & ACPI_PARSEOP_CLOSING_PAREN)
+        {
+            AcpiOsPrintf (")");
+        }
+        ASL_CV_PRINT_ONE_COMMENT (Op, AML_COMMENT_END_NODE, NULL, 0);
+        return;
+
+    case AML_STORE_OP:
+        if (Op->Common.DisasmFlags & ACPI_PARSEOP_CLOSING_PAREN)
+        {
+            AcpiOsPrintf (")");
+        }
+        ASL_CV_PRINT_ONE_COMMENT (Op, AML_COMMENT_END_NODE, NULL, 0);
+        return;
+
     /* No need for parens for these */
 
     case AML_DECREMENT_OP:
     case AML_INCREMENT_OP:
-    case AML_LOGICAL_NOT_OP:
     case AML_BIT_NOT_OP:
-    case AML_STORE_OP:
         ASL_CV_PRINT_ONE_COMMENT (Op, AML_COMMENT_END_NODE, NULL, 0);
         return;
 
