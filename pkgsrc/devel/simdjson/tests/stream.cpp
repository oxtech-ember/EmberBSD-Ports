#include <simdjson.h>
#include <cstdio>
#include <string>
int main() {
  std::string input;
  for (int i = 0; i < 100000; ++i) input += "{\"value\":12345}\n";
  simdjson::padded_string padded(input);
  simdjson::dom::parser parser;
  simdjson::dom::document_stream stream;
  if (parser.parse_many(padded, 1024 * 1024).get(stream)) return 1;
  unsigned n = 0;
  for (auto value : stream) { if (value.error()) return 2; ++n; }
  std::printf("stream=%zu count=%u\n", sizeof(stream), n);
  return n == 100000 ? 0 : 3;
}
