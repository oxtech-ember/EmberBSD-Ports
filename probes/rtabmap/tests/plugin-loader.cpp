// SPDX-License-Identifier: MIT
// AI-assisted regression through the actual OpenCV private DynamicLib API.
#include <opencv2/core.hpp>
#include <opencv2/core/utils/logger.hpp>
#include <opencv2/core/utils/plugin_loader.private.hpp>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>

static void require(bool condition, const char *message)
{
    if (!condition) throw std::runtime_error(message);
}

template<class Function>
static Function function(cv::plugin::impl::DynamicLib &library, const char *name)
{
    void *symbol = library.getSymbol(name);
    require(symbol != nullptr, "plugin symbol is missing");
    Function result = nullptr;
    static_assert(sizeof(result) == sizeof(symbol), "POSIX function address size");
    std::memcpy(&result, &symbol, sizeof(result));
    return result;
}

int main(int argc, char **argv)
{
    try {
        require(argc == 2, "usage: plugin-loader PLUGIN_MODULE");
        const std::string path = argv[1];
        {
            cv::plugin::impl::DynamicLib missing(path + ".missing-emberbsd-plugin");
            require(!missing.isLoaded(), "missing module must fail to load");
            require(missing.getSymbol("emberbsd_plugin_transform") == nullptr,
                    "missing module must not provide a symbol");
        }
        for (int cycle = 0; cycle < 2; ++cycle) {
            cv::plugin::impl::DynamicLib library(path);
            require(library.isLoaded(), "numeric plugin must load");
            require(library.getName() == path, "loaded plugin name");
            require(library.getSymbol("emberbsd_missing_plugin_symbol") == nullptr,
                    "missing symbol must be rejected");
            const auto transform = function<int (*)(int)>(library, "emberbsd_plugin_transform");
            const auto calls = function<int (*)(void)>(library, "emberbsd_plugin_calls");
            // A second load starts with new state only when the prior destructor
            // closed its handle. This also exercises libraryRelease_ in the DSO.
            require(calls() == 0, "plugin state must reset after unload and reopen");
            const int inputs[] = {-5, 0, 1, 17};
            const int expected[] = {-32, 3, 10, 122};
            for (int i = 0; i < 4; ++i)
                require(transform(inputs[i]) == expected[i], "known numeric plugin result");
            require(calls() == 4, "numeric plugin call count");
        }
        std::cout << "PASS OpenCV DynamicLib: load, symbol, missing module/symbol, unload, reopen\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
