#include <ada.h>
#include <optional>
#include <regex>
#include <string>
#include <vector>

// An explicit provider for this test only; applications supply their own.
struct provider {
  using regex_type = std::regex;
  static std::optional<regex_type> create_instance(std::string_view pattern, bool ignore_case) {
    try { return regex_type(std::string(pattern), ignore_case ? std::regex::icase : std::regex::ECMAScript); }
    catch (const std::regex_error&) { return std::nullopt; }
  }
  static bool regex_match(std::string_view input, const regex_type& re) {
    return std::regex_match(input.begin(), input.end(), re);
  }
  static std::optional<std::vector<std::optional<std::string>>> regex_search(std::string_view input, const regex_type& re) {
    std::match_results<std::string_view::const_iterator> match;
    if (!std::regex_search(input.begin(), input.end(), match, re)) return std::nullopt;
    std::vector<std::optional<std::string>> result;
    for (const auto& group : match) result.emplace_back(group.matched ? std::optional<std::string>(group.str()) : std::nullopt);
    return result;
  }
};
int main() {
  std::string_view base = "https://example.com";
  auto pattern = ada::parse_url_pattern<provider>("/foo", &base);
  if (!pattern) return 1;
  auto yes = pattern->test("https://example.com/foo", nullptr);
  auto no = pattern->test("https://example.com/bar", nullptr);
  return !yes || !*yes || !no || *no;
}
