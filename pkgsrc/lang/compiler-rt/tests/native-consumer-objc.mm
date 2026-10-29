// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#import <Foundation/Foundation.h>
#include <cassert>
#include <sstream>
#include <string>

int main() {
  @autoreleasepool {
    NSString *value = @"objc";
    std::ostringstream stream;
    stream << [value UTF8String] << ':' << 42;
    assert(stream.str() == "objc:42");
  }
}
