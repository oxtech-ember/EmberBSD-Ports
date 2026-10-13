// SPDX-License-Identifier: BSD-2-Clause
// Run the real Enchant discovery routine with a controlled GLib directory API.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#define G_MODULE_SUFFIX "so"

struct GDir { size_t index; };
static GDir directory;
static bool open_directory = true;
static std::vector<std::string> entries;
static std::vector<std::string> selected;

static GDir *g_dir_open(const char *, int, void *)
{
    directory.index = 0;
    return open_directory ? &directory : nullptr;
}

static const char *g_dir_read_name(GDir *dir)
{
    if (dir->index == entries.size())
        return nullptr;
    return entries[dir->index++].c_str();
}

static char *g_build_filename(const char *dir, const char *name, void *)
{
    const std::string joined = std::string(dir) + "/" + name;
    char *result = static_cast<char *>(std::malloc(joined.size() + 1));
    if (!result)
        std::abort();
    std::memcpy(result, joined.c_str(), joined.size() + 1);
    return result;
}

static void g_free(void *value) { std::free(value); }
static void g_dir_close(GDir *) {}

static int Test(char *filename)
{
    selected.emplace_back(filename);
    return selected.back() == "fixture/enchant_fail.so" ? 17 : 0;
}

#include "provider-discovery.inc"

int main()
{
    char dir[] = "fixture";
    entries = {"enchant_hunspell.so", "unrelated.so", "enchant_fake.so.old",
               "enchant_", "x", "enchant_second.so"};
    if (TestProvidersInDirectory(dir) != 0 || selected !=
        std::vector<std::string>{"fixture/enchant_hunspell.so",
                                 "fixture/enchant_second.so"}) {
        std::fprintf(stderr, "FAIL: expected 2 providers, selected %zu\n", selected.size());
        return 1;
    }
    selected.clear();
    entries = {"enchant_fail.so", "enchant_hunspell.so"};
    if (TestProvidersInDirectory(dir) != 17 || selected.size() != 2) {
        std::fputs("FAIL: provider failure was lost\n", stderr);
        return 1;
    }
    selected.clear();
    open_directory = false;
    if (TestProvidersInDirectory(dir) != 0 || !selected.empty()) {
        std::fputs("FAIL: unavailable directory handling changed\n", stderr);
        return 1;
    }
    std::puts("PASS: actual discovery selects providers and propagates failure");

    return 0;
}
