/* SPDX-License-Identifier: BSD-2-Clause */
#define NAPI_EXPERIMENTAL
#include <node_api.h>
static napi_value set_proto(napi_env env, napi_callback_info info) {
  size_t argc = 2; napi_value args[2], result; napi_status s;
  if (napi_get_cb_info(env, info, &argc, args, 0, 0) != napi_ok || argc != 2) return 0;
  s = node_api_set_prototype(env, args[0], args[1]);
  if (s == napi_pending_exception) return 0;
  if (napi_create_int32(env, s, &result) != napi_ok) return 0;
  return result;
}
NAPI_MODULE_INIT() {
  napi_value fn;
  if (napi_create_function(env, "set", NAPI_AUTO_LENGTH, set_proto, 0, &fn) != napi_ok) return 0;
  return fn;
}
