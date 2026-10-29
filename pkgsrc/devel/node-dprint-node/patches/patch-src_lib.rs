$NetBSD$

Origin: EmberBSD contributors (AI-assisted); not submitted upstream.

--- src/lib.rs.orig
+++ src/lib.rs
@@ -1,15 +1,11 @@
-#[cfg(target_os = "macos")]
-#[global_allocator]
-static GLOBAL: jemallocator::Jemalloc = jemallocator::Jemalloc;
-
 use dprint_core::configuration::{
-    resolve_global_config, ConfigKeyMap, ConfigKeyValue, ResolveGlobalConfigOptions,
+    resolve_global_config, ConfigKeyMap, ConfigKeyValue, 
 };
 use dprint_plugin_typescript::{
     configuration::{resolve_config, ConfigurationBuilder},
-    format_text,
+    format_text, FormatTextOptions,
 };
-use napi::{JsBoolean, JsNumber, JsObject, JsString, JsUnknown, Result, ValueType};
+use napi::{JsNumber, JsObject, JsString, Unknown, Result, ValueType};
 use napi_derive::napi;
 use std::path::Path;
 
@@ -30,17 +26,17 @@
                 let property = properties.get_element::<JsString>(i)?;
                 let property_str = property.into_utf8()?;
                 let k = property_str.into_owned()?;
-                let value: JsUnknown = obj.get_property(property)?;
+                let value: Unknown = obj.get_property(property)?;
                 let v = match value.get_type()? {
                     ValueType::String => {
-                        let s = unsafe { value.cast::<JsString>() }.into_utf8()?;
+                        let s = unsafe { value.cast::<JsString>() }?.into_utf8()?;
                         ConfigKeyValue::String(s.into_owned()?)
                     }
                     ValueType::Number => {
-                        ConfigKeyValue::Number(unsafe { value.cast::<JsNumber>() }.get_int32()?)
+                        ConfigKeyValue::Number(unsafe { value.cast::<JsNumber>() }?.get_int32()?)
                     }
                     ValueType::Boolean => {
-                        ConfigKeyValue::Bool(unsafe { value.cast::<JsBoolean>() }.get_value()?)
+                        ConfigKeyValue::Bool(unsafe { value.cast::<bool>() }?)
                     }
                     _ => {
                         return Err(napi::Error::new(
@@ -54,7 +50,7 @@
             }
             let res = resolve_config(
                 c,
-                &resolve_global_config(ConfigKeyMap::new(), &ResolveGlobalConfigOptions::default())
+                &resolve_global_config(&mut ConfigKeyMap::new())
                     .config,
             );
             if !res.diagnostics.is_empty() {
@@ -74,7 +70,7 @@
         _ => ConfigurationBuilder::new().deno().build(),
     };
 
-    match format_text(&path, &code, &config) {
+    match format_text(FormatTextOptions { path, extension: None, text: code.clone().into(), config: &config, external_formatter: None }) {
         Ok(res) => Ok(res.unwrap_or(code)),
         Err(e) => Err(napi::Error::new(
             napi::Status::GenericFailure,
