#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Use the SDK's selected target definition.
import sys

if len(sys.argv) != 3:
    sys.exit('expected SDK source and target name')
sys.path.insert(0, sys.argv[1] + '/src')
from emberbsd_sdk.targets import target_definition
print(target_definition(sys.argv[2])['machine'])
