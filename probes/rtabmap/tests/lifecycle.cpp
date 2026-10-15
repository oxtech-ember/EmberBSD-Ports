// SPDX-License-Identifier: MIT
// Origin: EmberBSD (AI-assisted). Installed RTAB-Map ownership regression.
#include <rtabmap/core/Rtabmap.h>
#include <rtabmap/core/Optimizer.h>
#include <rtabmap/core/Parameters.h>
#include <iostream>
#include <stdexcept>
#include <string>

static void require(bool condition, const char *message)
{
    if (!condition) throw std::runtime_error(message);
}

int main(int argc, char **argv)
{
    try {
        require(argc == 2, "usage: lifecycle default|gtsam");
        const std::string mode = argv[1];
        require(mode == "default" || mode == "gtsam", "known lifecycle mode");
        rtabmap::ParametersMap parameters;
        if (mode == "gtsam") {
            require(rtabmap::Optimizer::isAvailable(rtabmap::Optimizer::kTypeGTSAM),
                    "selected shared GTSAM backend is available");
            parameters[rtabmap::Parameters::kOptimizerStrategy()] = "2";
        }
        constexpr int scopes = 4;
        constexpr int cycles = 3;
        for (int scope = 0; scope < scopes; ++scope) {
            rtabmap::Rtabmap mapper;
            for (int cycle = 0; cycle < cycles; ++cycle) {
                mapper.init(parameters, "", false);
                require(mapper.getMemory() != nullptr, "init creates owned memory");
                mapper.close(false);
                require(mapper.getMemory() == nullptr, "close releases owned memory");
            }
            // Final destruction must free the reusable strategies that the
            // last close() restored. Each scope also tests repeated re-init.
        }
        std::cout << "PASS RTAB-Map lifecycle: mode=" << mode
                  << " scopes=" << scopes << " init-close-cycles=" << scopes * cycles << '\n';
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
