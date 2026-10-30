$NetBSD$

Use the Qt host tool wrapper for PO to QM conversion.

--- modules/ECMPoQmTools.cmake.orig
+++ modules/ECMPoQmTools.cmake
@@ -168,6 +168,14 @@
             )
     endif()
 
+    # Preserve direct target-name commands when Qt has no tool wrapper.
+    set(lconvert_command ${lconvert_executable})
+    set(lrelease_command Qt${QT_MAJOR_VERSION}::lrelease)
+    if(QT_MAJOR_VERSION EQUAL "6" AND QT_TOOL_COMMAND_WRAPPER_PATH)
+        set(lconvert_command "${QT_TOOL_COMMAND_WRAPPER_PATH}" "$<TARGET_FILE:Qt6::lconvert>")
+        set(lrelease_command "${QT_TOOL_COMMAND_WRAPPER_PATH}" "$<TARGET_FILE:Qt6::lrelease>")
+    endif()
+
     # Create commands to turn po files into qm files
     set(qm_files)
     foreach (po_file ${ARGS_PO_FILES})
@@ -187,9 +195,9 @@
 
         # lconvert from .po to .ts, then lrelease from .ts to .qm.
         add_custom_command(OUTPUT ${qm_file}
-            COMMAND ${lconvert_executable}
+            COMMAND ${lconvert_command}
                 ARGS -i ${po_file} -o ${ts_file} -target-language ${lang}
-            COMMAND Qt${QT_MAJOR_VERSION}::lrelease
+            COMMAND ${lrelease_command}
                 ARGS -removeidentical -nounfinished -silent ${ts_file} -qm ${qm_file}
             DEPENDS ${po_file}
             )
