/* SPDX-License-Identifier: MIT
 * AI-assisted numeric plugin fixture for the actual OpenCV DynamicLib API.
 */
#if defined(_WIN32)
#define PLUGIN_EXPORT __declspec(dllexport)
#elif defined(__GNUC__)
#define PLUGIN_EXPORT __attribute__((visibility("default")))
#else
#define PLUGIN_EXPORT
#endif

static int calls;

PLUGIN_EXPORT int emberbsd_plugin_transform(int value)
{
    ++calls;
    return value * 7 + 3;
}

PLUGIN_EXPORT int emberbsd_plugin_calls(void)
{
    return calls;
}
