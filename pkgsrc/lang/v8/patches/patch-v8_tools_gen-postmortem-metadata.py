$NetBSD$

Export versioned postmortem metadata for the shared V8 layout.
Origin: EmberBSD (AI-assisted).

--- a/tools/gen-postmortem-metadata.py
+++ b/tools/gen-postmortem-metadata.py
@@ -58,6 +58,32 @@
 # enumeration values used as indexes in internal tables, etc..
 #
 consts_misc = [
+    {'name': 'metadata_schema_version', 'value': '2'},
+    {'name': 'shared_function_info_token_out_of_range', 'value': 'SharedFunctionInfo::kFunctionTokenOutOfRange'},
+    {'name': 'sandbox_enabled', 'value': 'V8DBG_SANDBOX_ENABLED'},
+    {'name': 'pointer_compression_enabled', 'value': 'V8DBG_POINTER_COMPRESSION_ENABLED'},
+    {'name': 'prop_first_outobject_offset_words', 'value': 'FieldStorageLocation::kFirstOutOfObjectOffsetInWords'},
+    {'name': 'prop_offset_words_mask', 'value': 'PropertyDetails::OffsetInWordsField::kMask'},
+    {'name': 'prop_offset_words_shift', 'value': 'PropertyDetails::OffsetInWordsField::kShift'},
+    {'name': 'prop_inobject_mask', 'value': 'PropertyDetails::InObjectField::kMask'},
+    {'name': 'prop_inobject_shift', 'value': 'PropertyDetails::InObjectField::kShift'},
+    {'name': 'scopeinfo_flags_offset', 'value': 'offsetof(ScopeInfo, flags_)'},
+    {'name': 'scopeinfo_scope_type_mask', 'value': 'ScopeInfo::ScopeTypeBits::kMask'},
+    {'name': 'scopeinfo_scope_type_shift', 'value': 'ScopeInfo::ScopeTypeBits::kShift'},
+    {'name': 'scopeinfo_module_scope', 'value': 'MODULE_SCOPE'},
+    {'name': 'scopeinfo_max_inlined_names', 'value': 'kScopeInfoMaxInlinedLocalNamesSize'},
+    {'name': 'scopeinfo_position_start_offset', 'value': 'offsetof(ScopeInfo, position_info_start_)'},
+    {'name': 'scopeinfo_position_end_offset', 'value': 'offsetof(ScopeInfo, position_info_end_)'},
+    {'name': 'scopeinfo_parameter_count_offset', 'value': 'offsetof(ScopeInfo, parameter_count_)'},
+    {'name': 'scopeinfo_context_local_count_offset', 'value': 'offsetof(ScopeInfo, context_local_count_)'},
+    {'name': 'scopeinfo_variable_part_offset', 'value': 'OFFSET_OF_DATA_START(ScopeInfo)'},
+    {'name': 'scopeinfo_saved_class_mask', 'value': 'ScopeInfo::HasSavedClassVariableBit::kMask'},
+    {'name': 'scopeinfo_function_variable_mask', 'value': 'ScopeInfo::FunctionVariableBits::kMask'},
+    {'name': 'scopeinfo_function_variable_shift', 'value': 'ScopeInfo::FunctionVariableBits::kShift'},
+    {'name': 'scopeinfo_function_variable_none', 'value': 'static_cast<int>(VariableAllocationInfo::NONE)'},
+    {'name': 'scopeinfo_inferred_name_mask', 'value': 'ScopeInfo::HasInferredFunctionNameBit::kMask'},
+    {'name': 'scopeinfo_function_variable_info_size', 'value': 'sizeof(FunctionVariableInfo)'},
+    {'name': 'scopeinfo_function_variable_name_offset', 'value': 'offsetof(FunctionVariableInfo, name)'},
     {
         'name': 'FirstNonstringType',
         'value': 'FIRST_NONSTRING_TYPE'
@@ -303,14 +329,6 @@
         'value': 'PropertyDetails::AttributesField::kShift'
     },
     {
-        'name': 'prop_index_mask',
-        'value': 'PropertyDetails::FieldIndexField::kMask'
-    },
-    {
-        'name': 'prop_index_shift',
-        'value': 'PropertyDetails::FieldIndexField::kShift'
-    },
-    {
         'name': 'prop_representation_mask',
         'value': 'PropertyDetails::RepresentationField::kMask'
     },
@@ -415,18 +433,6 @@
         'value': 'InterpreterFrameConstants::kBytecodeOffsetFromFp'
     },
     {
-        'name': 'scopeinfo_idx_nparams',
-        'value': 'ScopeInfo::kParameterCount'
-    },
-    {
-        'name': 'scopeinfo_idx_ncontextlocals',
-        'value': 'ScopeInfo::kContextLocalCount'
-    },
-    {
-        'name': 'scopeinfo_idx_first_vars',
-        'value': 'ScopeInfo::kVariablePartIndex'
-    },
-    {
         'name': 'jsarray_buffer_was_detached_mask',
         'value': 'JSArrayBuffer::WasDetachedBit::kMask'
     },
@@ -482,10 +488,6 @@
         'name': 'simplenumberdictionaryshape_entry_size',
         'value': 'SimpleNumberDictionaryShape::kEntrySize'
     },
-    {
-        'name': 'type_JSError__JS_ERROR_TYPE',
-        'value': 'JS_ERROR_TYPE'
-    },
 ]
 
 #
@@ -497,41 +499,47 @@
 # in this "extras_accessors" table.
 #
 extras_accessors = [
-    'JSFunction, context, Context, kContextOffset',
-    'JSFunction, shared, SharedFunctionInfo, kSharedFunctionInfoOffset',
-    'HeapObject, map, Map, kMapOffset',
-    'JSObject, elements, Object, kElementsOffset',
+    'SharedFunctionInfo, raw_trusted_function_data, TrustedPointer, offsetof(SharedFunctionInfo, trusted_function_data_)',
+    'SharedFunctionInfo, name_or_scope_info, Object, offsetof(SharedFunctionInfo, name_or_scope_info_)',
+    'SharedFunctionInfo, script, Object, offsetof(SharedFunctionInfo, script_)',
+    'Map, constructor_or_back_pointer_or_native_context, Object, offsetof(Map, constructor_or_back_pointer_or_native_context_)',
+    'JSReceiver, properties_or_hash, Object, offsetof(JSReceiver, properties_or_hash_)',
+    'Script, line_offset, SMI, offsetof(Script, line_offset_)',
+    'JSFunction, context, Context, offsetof(JSFunction, context_)',
+    'JSFunction, shared, SharedFunctionInfo, offsetof(JSFunction, shared_function_info_)',
+    'HeapObject, map, Map, offsetof(HeapObject, map_)',
+    'JSObject, elements, Object, offsetof(JSObject, elements_)',
     'JSObject, internal_fields, uintptr_t, kHeaderSize',
     'FixedArray, data, uintptr_t, OFFSET_OF_DATA_START(FixedArray)',
     'BytecodeArray, data, uintptr_t, kHeaderSize',
-    'JSArrayBuffer, backing_store, uintptr_t, kBackingStoreOffset',
-    'JSArrayBuffer, byte_length, size_t, kRawByteLengthOffset',
-    'JSArrayBufferView, byte_length, size_t, kRawByteLengthOffset',
-    'JSArrayBufferView, byte_offset, size_t, kRawByteOffsetOffset',
-    'JSDate, value, Object, kValueOffset',
-    'JSTypedArray, external_pointer, uintptr_t, kExternalPointerOffset',
-    'Map, instance_size_in_words, char, kInstanceSizeInWordsOffset',
-    'Map, inobject_properties_start_or_constructor_function_index, char, kInobjectPropertiesStartOrConstructorFunctionIndexOffset',
-    'Map, instance_type, uint16_t, kInstanceTypeOffset',
-    'Map, bit_field, char, kBitFieldOffset',
-    'Map, bit_field2, char, kBitField2Offset',
-    'Map, bit_field3, int, kBitField3Offset',
-    'Map, prototype, Object, kPrototypeOffset',
+    'JSArrayBuffer, raw_backing_store, uintptr_t, offsetof(JSArrayBuffer, backing_store_)',
+    'JSArrayBuffer, raw_byte_length, size_t, offsetof(JSArrayBuffer, raw_byte_length_)',
+    'JSArrayBufferView, raw_byte_length, size_t, offsetof(JSArrayBufferView, raw_byte_length_)',
+    'JSArrayBufferView, raw_byte_offset, size_t, offsetof(JSArrayBufferView, raw_byte_offset_)',
+    'JSDate, value, double, offsetof(JSDate, value_)',
+    'JSTypedArray, raw_external_pointer, uintptr_t, offsetof(JSTypedArray, external_pointer_)',
+    'Map, instance_size_in_words, char, offsetof(Map, instance_size_in_words_)',
+    'Map, inobject_properties_start_or_constructor_function_index, char, offsetof(Map, inobject_properties_start_or_constructor_function_index_)',
+    'Map, instance_type, uint16_t, offsetof(Map, instance_type_)',
+    'Map, bit_field, char, offsetof(Map, bit_field_)',
+    'Map, bit_field2, char, offsetof(Map, bit_field2_)',
+    'Map, bit_field3, int, offsetof(Map, bit_field3_)',
+    'Map, prototype, Object, offsetof(Map, prototype_)',
     'Oddball, kind, int, offsetof(Oddball, kind_)',
     'HeapNumber, value, double, offsetof(HeapNumber, value_)',
-    'ExternalString, resource, Object, offsetof(ExternalString, resource_)',
+    'ExternalString, raw_resource, ExternalPointer, offsetof(ExternalString, resource_)',
     'SeqOneByteString, chars, char, OFFSET_OF_DATA_START(SeqOneByteString)',
     'SeqTwoByteString, chars, char, OFFSET_OF_DATA_START(SeqTwoByteString)',
     'UncompiledData, inferred_name, String, offsetof(UncompiledData, inferred_name_)',
     'UncompiledData, start_position, int32_t, offsetof(UncompiledData, start_position_)',
     'UncompiledData, end_position, int32_t, offsetof(UncompiledData, end_position_)',
-    'Script, source, Object, kSourceOffset',
-    'Script, name, Object, kNameOffset',
-    'Script, line_ends, Object, kLineEndsOffset',
-    'SharedFunctionInfo, raw_function_token_offset, int16_t, kFunctionTokenOffsetOffset',
-    'SharedFunctionInfo, internal_formal_parameter_count, uint16_t, kFormalParameterCountOffset',
-    'SharedFunctionInfo, flags, int, kFlagsOffset',
-    'SharedFunctionInfo, length, uint16_t, kLengthOffset',
+    'Script, source, Object, offsetof(Script, source_)',
+    'Script, name, Object, offsetof(Script, name_)',
+    'Script, line_ends, Object, offsetof(Script, line_ends_)',
+    'SharedFunctionInfo, raw_function_token_offset, uint16_t, offsetof(SharedFunctionInfo, function_token_offset_)',
+    'SharedFunctionInfo, internal_formal_parameter_count, uint16_t, offsetof(SharedFunctionInfo, formal_parameter_count_)',
+    'SharedFunctionInfo, flags, int, offsetof(SharedFunctionInfo, flags_)',
+    'SharedFunctionInfo, length, uint16_t, offsetof(SharedFunctionInfo, length_)',
     'SlicedString, parent, String, offsetof(SlicedString, parent_)',
     'Code, flags, uint32_t, kFlagsOffset',
     'Code, instruction_start, Address, kInstructionStartOffset',
@@ -959,6 +967,17 @@
   out = open(sys.argv[1], 'w');
 
   out.write(header);
+  out.write("""#if defined(V8_ENABLE_SANDBOX)
+#define V8DBG_SANDBOX_ENABLED 1
+#else
+#define V8DBG_SANDBOX_ENABLED 0
+#endif
+#if defined(V8_COMPRESS_POINTERS)
+#define V8DBG_POINTER_COMPRESSION_ENABLED 1
+#else
+#define V8DBG_POINTER_COMPRESSION_ENABLED 0
+#endif
+""")
 
   out.write("struct OffsetsForDebug {\n")
   for (klass, field, offset) in offsetof_fields:
