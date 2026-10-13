// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Exercise the actual Library API.
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include "fcitx-utils/library.h"

#define MAGIC "FCITX_DATA_MAGIC"
#define PAYLOAD "payload"
extern "C" {
__attribute__((visibility("default"))) char ember_fcitx_test_data[] =
    MAGIC PAYLOAD;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        return 2;
    }
    const std::filesystem::path root(argv[1]);
    const auto present = root / "present.bin";
    const auto missing = root / "missing.bin";
    const auto missingLong = root / "missing-long.bin";
    {
        std::ofstream file(present, std::ios::binary);
        file.write(ember_fcitx_test_data, sizeof(ember_fcitx_test_data));
        if (!file) {
            return 2;
        }
    }
    {
        std::ofstream file(missing, std::ios::binary);
        file.write("missing", 7);
        if (!file) {
            return 2;
        }
    }
    {
        std::ofstream file(missingLong, std::ios::binary);
        file << "This file is longer than the signature, but has no match.";
        if (!file) {
            return 2;
        }
    }
    int failures = 0;

    bool called = false;
    bool correct = false;
    fcitx::Library dataFile(present);
    bool result = dataFile.findData("unused", MAGIC, std::strlen(MAGIC),
        [&](const char *value) { called = true; correct = std::strcmp(value, PAYLOAD) == 0; });
    if (!result || !called || !correct) {
        std::cerr << "FAIL: file with magic\n";
        ++failures;
    }
    fcitx::Library self;
    called = false;
    correct = false;
    if (!self.load(fcitx::LibraryLoadHint::DefaultHint) ||
        !self.findData("ember_fcitx_test_data", MAGIC, std::strlen(MAGIC),
            [&](const char *value) { called = true; correct = std::strcmp(value, PAYLOAD) == 0; }) ||
        !called || !correct || !self.unload()) {
        std::cerr << "FAIL: loaded symbol\n";
        ++failures;
    }
    for (const auto &path : {missing, missingLong}) {
        fcitx::Library missingFile(path);
        called = false;
        result = missingFile.findData("unused", MAGIC, std::strlen(MAGIC),
                                      [&](const char *) { called = true; });
        if (result || called) {
            std::cerr << "FAIL: missing magic result=" << result
                      << " callback=" << called << " file=" << path.filename()
                      << '\n';
            ++failures;
        }
    }
    if (failures == 0) {
        std::cout << "PASS: file magic, loaded symbol, missing magic\n";
    }
    return failures == 0 ? 0 : 1;
}
