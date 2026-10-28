#include <simdjson.h>
#include <string>
#include <string_view>

int main() {
  simdjson::ondemand::parser parser;
  simdjson::ondemand::document document;
  simdjson::ondemand::object object;
  std::string raw = R"({"name":"example","version":"1.0.0"})";
  auto json = simdjson::pad(raw);
  if (parser.iterate(json).get(document) || document.get_object().get(object)) return 1;
  std::string_view value;
  if (object["name"].get_string().get(value) || value != "example") return 2;
  simdjson::ondemand::parser invalid_parser;
  std::string bad = "not-json";
  auto invalid = simdjson::pad(bad);
  if (!invalid_parser.iterate(invalid).get(document) && !document.get_object().get(object)) return 3;
  return 0;
}
