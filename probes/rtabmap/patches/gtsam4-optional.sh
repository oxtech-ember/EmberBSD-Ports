#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). GTSAM 4.3 returns std::optional,
# not boost::optional; RTAB-Map calls the boost-specific is_initialized().
set -eu
cd "$1"
sed -i 's/\.is_initialized()/.has_value()/g' corelib/src/optimizer/OptimizerGTSAM.cpp
