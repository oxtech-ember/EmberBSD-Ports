/* SPDX-License-Identifier: BSD-2-Clause */
#include <node_api.h>

static napi_value
initialize(napi_env env, napi_value exports)
{
    (void)env;
    return exports;
}
NAPI_MODULE(NODE_GYP_MODULE_NAME, initialize)
