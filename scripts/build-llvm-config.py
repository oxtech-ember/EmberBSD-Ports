#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Build and test the real upstream cross LLVM metadata query tool."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
cross = Path(__file__).resolve().parents[1] / 'profiles/common-graphics/cross'
sys.path.insert(0, str(cross))
import llvm_sdk as sdk


def build(args):
    from emberbsd_sdk.process import ContextLocks
    if len(args) != 6:
        raise ValueError('usage: build-llvm-config.py --sdk-source SDK LLVM_SOURCE TARGET_BUILD NATIVE_BUILD SYSROOT TARGET_PREFIX NEW_WORK')
    inputs = [sdk.existing_directory(p) for p in args[:5]]
    destination = sdk.new_destination(args[5], inputs)
    with ContextLocks([destination], str(Path(destination).parent)):
        sdk.new_destination(destination, inputs)
        work = Path(sdk.stage_for(destination))
        print('Retained partial work on failure: ' + str(work), file=sys.stderr, flush=True)
        source = sdk.sdk_source.load()
        common = [sys.executable, '-B']
        builder = [*common, str(cross / 'build-llvm-config.py'), '--sdk-source', source, *inputs, str(work / 'helper')]
        sdk.command_file(work / 'build.command', builder)
        sdk.produce(builder, work / 'build.log')
        test = [*common, str(cross / 'test-llvm-config.py'), '--sdk-source', source, str(work / 'helper'), str(work / 'tests')]
        sdk.command_file(work / 'test.command', test)
        sdk.produce(test, work / 'test.log')
        sdk.publish(str(work), destination)
    print('Set EMBERBSD_GRAPHICS_LLVM_CONFIG=' + destination + '/helper/bin/llvm-config in the cross MAKECONF.')
    return 0


if __name__ == '__main__':
    sys.exit(sdk.main(build))
