// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors. Prepared with AI assistance.
#include "contract.pb.h"
#include <google/protobuf/io/gzip_stream.h>
#include <google/protobuf/io/zero_copy_stream_impl_lite.h>
#include <google/protobuf/unknown_field_set.h>
#include <array>
#include <cstdio>
#include <string>

namespace {
int failures;

void check(bool condition, const char* description)
{
    if (!condition) {
        std::fprintf(stderr, "FAIL: %s\n", description);
        ++failures;
    }
}

void exercise()
{
    // Independent wire bytes: field 1 varint 150; field 2 UTF-8 "KiCad";
    // field 3 packed zigzag -1, 0, 42.
    const std::array<unsigned char, 15> expected = {
        0x08, 0x96, 0x01, 0x12, 0x05, 'K', 'i', 'C', 'a', 'd',
        0x1a, 0x03, 0x01, 0x00, 0x54
    };
    const std::string wire(reinterpret_cast<const char*>(expected.data()),
                           expected.size());
    emberbsd::kicad::Contract message;
    message.set_revision(150);
    message.set_label("KiCad");
    message.add_samples(-1);
    message.add_samples(0);
    message.add_samples(42);
    std::string encoded;
    check(message.SerializeToString(&encoded), "serialize succeeds");
    check(encoded == wire, "serialization has exact known bytes");

    std::string compressed;
    {
        google::protobuf::io::StringOutputStream output(&compressed);
        google::protobuf::io::GzipOutputStream gzip(&output);
        check(message.SerializeToZeroCopyStream(&gzip), "serialize through gzip");
        check(gzip.Close(), "finish the gzip stream");
    }
    {
        google::protobuf::io::ArrayInputStream input(compressed.data(),
                                                    compressed.size());
        google::protobuf::io::GzipInputStream gzip(&input);
        emberbsd::kicad::Contract inflated;
        check(inflated.ParseFromZeroCopyStream(&gzip) &&
                  inflated.SerializeAsString() == wire,
              "gzip stream preserves independent known wire bytes");
    }

    emberbsd::kicad::Contract decoded;
    check(decoded.ParseFromString(wire), "parse independent known bytes");
    check(decoded.revision() == 150 && decoded.label() == "KiCad" &&
              decoded.samples_size() == 3 && decoded.samples(0) == -1 &&
              decoded.samples(1) == 0 && decoded.samples(2) == 42,
          "all decoded fields agree");
    const std::string future = wire + std::string("\x78\x07", 2);
    check(decoded.ParseFromString(future), "accept unknown field");
    const auto& unknown = decoded.GetReflection()->GetUnknownFields(decoded);
    check(unknown.field_count() == 1 && unknown.field(0).number() == 15 &&
              unknown.field(0).type() == google::protobuf::UnknownField::TYPE_VARINT &&
              unknown.field(0).varint() == 7,
          "preserve unknown field value");
    check(decoded.SerializeAsString() == future, "preserve unknown wire bytes");
    check(!decoded.ParseFromString(wire.substr(0, wire.size() - 1)),
          "reject truncated packed field");
    check(!decoded.ParseFromString(std::string("\x12\x02\xc0\xaf", 4)),
          "reject overlong UTF-8");
    check(!decoded.ParseFromString(std::string("\x08\x80", 2)),
          "reject incomplete varint");
    decoded.Clear();
    check(decoded.ByteSizeLong() == 0 && decoded.SerializeAsString().empty(),
          "clear resets all fields");
}
}

int main()
{
    GOOGLE_PROTOBUF_VERIFY_VERSION;
    exercise();
    google::protobuf::ShutdownProtobufLibrary();
    if (failures == 0)
        std::puts("PASS: protobuf installed C++ contract (14 checks)");
    return failures == 0 ? 0 : 1;
}
