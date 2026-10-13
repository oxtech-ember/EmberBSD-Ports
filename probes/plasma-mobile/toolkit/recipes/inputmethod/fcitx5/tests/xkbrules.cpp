// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Exercise the real XKB XML parser and merge.
#include <array>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include "xkbrules.h"

namespace {
void require(bool condition, const std::string &message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        std::exit(1);
    }
}

void writeRules(const std::filesystem::path &path, const std::string &id,
                const std::string &attribute) {
    std::filesystem::create_directories(path.parent_path());
    std::ofstream xml(path);
    xml << "<xkbConfigRegistry version=\"" << id << "\"><modelList>";
    for (const char *suffix : {"a", "b"}) {
        xml << "<model><configItem><name>" << id << '-' << suffix
            << "</name><description>Model " << id << '-' << suffix
            << "</description><vendor>Vendor " << id
            << "</vendor></configItem></model>";
    }
    xml << "</modelList><layoutList><layout><configItem><name>" << id
        << "</name><description>Layout " << id
        << "</description></configItem></layout></layoutList><optionList><group"
        << attribute << "><configItem><name>" << id
        << "</name><description>Group " << id << "</description></configItem>";
    for (const char *suffix : {"a", "b"}) {
        xml << "<option><configItem><name>" << id << ':' << suffix
            << "</name><description>Option " << id << ':' << suffix
            << "</description></configItem></option>";
    }
    xml << "</group></optionList></xkbConfigRegistry>";
    xml.close();
    require(static_cast<bool>(xml), "write fixture " + path.string());
}

void check(const fcitx::XkbRules &rules,
           const std::array<std::string, 5> &ids) {
    require(rules.modelInfos().size() == 10, "missing models after merge");
    require(rules.optionGroupInfos().size() == 5,
            "missing option groups after merge");
    require(rules.layoutInfos().size() == 5, "layout count changed");
    require(rules.version() == ids.back(), "last parsed version changed");
    for (size_t i = 0; i < ids.size(); ++i) {
        const auto &id = ids[i];
        const auto *layout = rules.findByName(id);
        require(layout && layout->description == "Layout " + id,
                "layout content changed: " + id);
        const auto &group = rules.optionGroupInfos()[i];
        require(group.name == id && group.description == "Group " + id,
                "option group order or content: " + id);
        // The final file omits the attribute. Preserve value-initialized false.
        require(group.exclusive == (i == 1 || i == 3),
                "selection attribute changed: " + id);
        require(group.optionInfos.size() == 2, "option count: " + id);
        for (size_t j = 0; j < 2; ++j) {
            const std::string suffix = j == 0 ? "a" : "b";
            const auto &model = rules.modelInfos()[2 * i + j];
            require(model.name == id + '-' + suffix &&
                        model.description == "Model " + id + '-' + suffix &&
                        model.vendor == "Vendor " + id,
                    "model order or content: " + id);
            const auto &option = group.optionInfos[j];
            require(option.name == id + ':' + suffix &&
                        option.description == "Option " + id + ':' + suffix,
                    "option order or content: " + id);
        }
    }
}
} // namespace

int main(int argc, char **argv) {
    require(argc == 2, "provide a private new fixture directory");
    const std::filesystem::path root(argv[1]);
    require(root.is_absolute() && std::filesystem::create_directory(root),
            "fixture directory must be new and absolute");
    const std::array<std::string, 5> ids = {
        "low-main", "low-extras", "high-main", "high-extras", "explicit"};
    const auto low = root / "low";
    const auto high = root / "high";
    const auto extra = root / "explicit.xml";
    writeRules(low / "rules/evdev.xml", ids[0], " allowMultipleSelection=\"true\"");
    writeRules(low / "rules/evdev.extras.xml", ids[1], " allowMultipleSelection=\"false\"");
    writeRules(high / "rules/evdev.xml", ids[2], " allowMultipleSelection=\"true\"");
    writeRules(high / "rules/evdev.extras.xml", ids[3], " allowMultipleSelection=\"false\"");
    writeRules(extra, ids[4], "");
    fcitx::XkbRules rules;
    for (int run = 0; run < 2; ++run) {
        require(rules.read({high, low}, "evdev", extra.string()), "read XML fixtures");
        check(rules, ids);
    }
    rules.clear();
    require(rules.modelInfos().empty() && rules.optionGroupInfos().empty() &&
                rules.layoutInfos().empty() && rules.version().empty(),
            "clear must remove all parsed data");
    std::cout << "PASS: models, groups, options, parse order, attributes and repeat lifecycle\n";
}
