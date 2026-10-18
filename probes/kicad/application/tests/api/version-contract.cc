// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors. Prepared with AI assistance.
#include <sys/types.h>
#include <import_export.h>
#include <api/common/types/base_types.pb.h>
#include <google/protobuf/message_lite.h>
#include <iostream>
#include <string>

static bool CheckVersion()
{
    const std::string wire("\x08\x0a\x18\x07", 4);
    kiapi::common::types::KiCadVersion version;
    version.set_major(10);
    version.set_minor(0);
    version.set_patch(7);
    std::string encoded;
    if (!version.SerializeToString(&encoded) || encoded != wire)
        return false;
    version.set_minor(99);
    if (!version.ParseFromString(wire) || version.major() != 10 ||
        version.minor() != 0 || version.patch() != 7)
        return false;
    const auto* descriptor = version.GetDescriptor();
    const char* names[] = {"major", "minor", "patch"};
    for (int i = 0; i != 3; ++i) {
        const auto* field = descriptor->FindFieldByNumber(i + 1);
        if (field == nullptr || field->name() != names[i] ||
            field->json_name() != names[i])
            return false;
    }
    return true;
}

int main()
{
    const bool ok = CheckVersion();
    google::protobuf::ShutdownProtobufLibrary();
    if (!ok) {
        std::cerr << "FAIL: KiCadVersion wire and field names\n";
        return 1;
    }
    std::cout << "PASS: KiCadVersion major/minor accessors, known wire and field names\n";
    return 0;
}
