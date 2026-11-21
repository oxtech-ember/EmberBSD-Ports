// SPDX-License-Identifier: MIT
#define MCAP_IMPLEMENTATION
#include <mcap/reader.hpp>
#include <mcap/writer.hpp>
#include <lz4.h>
#include <zstd.h>
#include <algorithm>
#include <array>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

static constexpr uint64_t start = 1000000000;
static constexpr uint64_t step = 10000000;
static const std::string schemaText = R"({"type":"object","properties":{"sample":{"type":"integer"}}})";
static const std::array<unsigned, 12> fileOrder{{0, 4, 1, 8, 2, 10, 3, 9, 5, 11, 6, 7}};

static void require(bool condition, const std::string& message) {
  if (!condition) throw std::runtime_error(message);
}
static void check(const mcap::Status& status) {
  require(status.ok(), status.message);
}
static std::vector<std::byte> payload(unsigned sequence) {
  std::vector<std::byte> bytes(4096, std::byte('A' + sequence % 4));
  bytes[0] = std::byte(sequence);
  bytes[1] = std::byte(0);
  bytes[2] = std::byte(255);
  return bytes;
}
static std::vector<char> load(const std::string& path) {
  std::ifstream input(path, std::ios::binary);
  require(input.good(), "open fixture");
  return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}
static void save(const std::string& path, const std::vector<char>& bytes) {
  std::ofstream output(path, std::ios::binary | std::ios::trunc);
  output.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
  output.close();
  require(output.good(), "write fixture");
}
struct Files {
  std::vector<std::string> paths;
  ~Files() { for (const auto& path : paths) std::remove(path.c_str()); }
  std::string add(const std::string& path) { paths.push_back(path); return path; }
};

static std::vector<unsigned> read(mcap::McapReader& reader, mcap::ReadMessageOptions options) {
  std::vector<unsigned> sequences;
  bool problem = false;
  for (const auto& item : reader.readMessages([&](const mcap::Status& error) {
         problem = true;
         std::cerr << error.message << '\n';
       }, options)) {
    const unsigned sequence = item.message.sequence;
    require(sequence < 12, "sequence outside fixture");
    require(item.schema && item.schema->name == "ember.Sample" &&
      item.schema->encoding == "jsonschema", "schema identity");
    require(item.schema->data.size() == schemaText.size() &&
      std::equal(item.schema->data.begin(), item.schema->data.end(),
      reinterpret_cast<const std::byte*>(schemaText.data())), "schema content");
    require(item.channel && item.channel->topic == (sequence % 2 ? "/imu" : "/odometry") &&
      item.channel->messageEncoding == "ember-binary" &&
      item.channel->metadata.at("frame") == "robot" &&
      item.channel->schemaId == item.schema->id, "channel identity and metadata");
    require(item.message.logTime == start + sequence * step &&
      item.message.publishTime == start + sequence * step - 1234, "nanosecond timestamps");
    const auto expected = payload(sequence);
    require(item.message.dataSize == expected.size() &&
      std::equal(expected.begin(), expected.end(), item.message.data), "binary payload");
    sequences.push_back(sequence);
  }
  require(!problem, "unexpected reader error");
  return sequences;
}

// Demand an actual library error: a short result alone is not rejection.
static void rejected(const std::string& path, bool summary) {
  mcap::McapReader reader;
  if (!reader.open(path).ok()) return;
  if (summary && !reader.readSummary(mcap::ReadSummaryMethod::NoFallbackScan).ok()) return;
  bool problem = false;
  for (const auto& item : reader.readMessages([&](const mcap::Status& error) {
         require(!error.ok(), "success status reported as a problem");
         problem = true;
       })) {
    (void)item;
  }
  require(problem, "malformed MCAP was not rejected: " + path);
}

int main(int argc, char** argv) {
  try {
    require(argc == 2, "usage: mcap-contract none|lz4|zstd");
    const std::string mode = argv[1];
    require(mode == "none" || mode == "lz4" || mode == "zstd", "unknown compression");
    require(std::string(mcap::LibraryVersion) == "2.1.3", "MCAP version");
    require(LZ4_versionNumber() == 11101 && LZ4_VERSION_NUMBER == 11101, "LZ4 version");
    require(ZSTD_versionNumber() == 10507 && ZSTD_VERSION_NUMBER == 10507, "Zstd version");
    Files files;
    const auto path = files.add("contract-" + mode + ".mcap");
    mcap::McapWriter writer;
    mcap::McapWriterOptions options("");
    options.compression = mode == "none" ? mcap::Compression::None :
      mode == "lz4" ? mcap::Compression::Lz4 : mcap::Compression::Zstd;
    options.forceCompression = true;
    options.chunkSize = 9000;
    options.enableDataCRC = true;
    check(writer.open(path, options));
    mcap::Schema schema("ember.Sample", "jsonschema", schemaText);
    writer.addSchema(schema);
    mcap::Channel odometry("/odometry", "ember-binary", schema.id);
    mcap::Channel imu("/imu", "ember-binary", schema.id);
    odometry.metadata["frame"] = "robot";
    imu.metadata["frame"] = "robot";
    writer.addChannel(odometry);
    writer.addChannel(imu);
    for (unsigned sequence : fileOrder) {
      const auto bytes = payload(sequence);
      mcap::Message message;
      message.channelId = sequence % 2 ? imu.id : odometry.id;
      message.sequence = sequence;
      message.logTime = start + sequence * step;
      message.publishTime = message.logTime - 1234;
      message.data = bytes.data();
      message.dataSize = bytes.size();
      check(writer.write(message));
    }
    writer.close();

    mcap::McapReader reader;
    check(reader.open(path));
    check(reader.readSummary(mcap::ReadSummaryMethod::NoFallbackScan));
    require(reader.statistics().has_value() && reader.statistics()->messageCount == 12 &&
      reader.statistics()->channelCount == 2 && reader.statistics()->schemaCount == 1,
      "summary counts");
    const auto indexes = reader.chunkIndexes();
    require(indexes.size() >= 3, "multiple indexed chunks");
    for (const auto& index : indexes) {
      require(index.compression == (mode == "none" ? "" : mode), "actual chunk compression");
      require(!index.messageIndexOffsets.empty(), "message index missing");
      if (mode != "none") require(index.compressedSize < index.uncompressedSize, "compression ratio");
    }
    mcap::ReadMessageOptions reading;
    require(read(reader, reading) == std::vector<unsigned>(fileOrder.begin(), fileOrder.end()),
      "file-order replay");
    reading.readOrder = mcap::ReadMessageOptions::ReadOrder::LogTimeOrder;
    require(read(reader, reading) == std::vector<unsigned>({0,1,2,3,4,5,6,7,8,9,10,11}),
      "indexed timestamp ordering");
    reading.startTime = start + 3 * step;
    reading.endTime = start + 8 * step;
    require(read(reader, reading) == std::vector<unsigned>({3,4,5,6,7}), "half-open indexed time window");
    reading.topicFilter = [](std::string_view topic) { return topic == "/imu"; };
    require(read(reader, reading) == std::vector<unsigned>({3,5,7}), "indexed channel filter");
    reading.readOrder = mcap::ReadMessageOptions::ReadOrder::ReverseLogTimeOrder;
    require(read(reader, reading) == std::vector<unsigned>({7,5,3}), "reverse indexed replay");
    reader.close();

    const auto original = load(path);
    auto bytes = original;
    bytes[0] = 0;
    const auto badMagic = files.add(path + ".magic");
    save(badMagic, bytes);
    rejected(badMagic, false);
    bytes = original;
    bytes.resize(bytes.size() - 10);
    const auto truncated = files.add(path + ".truncated");
    save(truncated, bytes);
    rejected(truncated, true);

    // MCAP Chunk: opcode/length (9), times/size (24), CRC (4), compression string
    // (4+N), then compressed size (8) and payload. Mutate structure/frame, not CRC.
    const size_t chunkData = static_cast<size_t>(indexes.front().chunkStartOffset) +
      9 + 24 + 4 + 4 + (mode == "none" ? 0 : mode.size()) + 8;
    require(chunkData + 10 < original.size(), "chunk bounds");
    bytes = original;
    if (mode == "none") {
      // Preserve the inner opcode but make its declared record length impossible.
      std::fill(bytes.begin() + chunkData + 1, bytes.begin() + chunkData + 9, char(0xff));
    } else {
      std::fill(bytes.begin() + chunkData, bytes.begin() + chunkData + 4, char(0));
    }
    const auto corrupt = files.add(path + ".corrupt");
    save(corrupt, bytes);
    rejected(corrupt, false);
    bytes = original;
    bytes.resize(chunkData + 3);
    const auto shortChunk = files.add(path + ".short-chunk");
    save(shortChunk, bytes);
    rejected(shortChunk, false);
    std::cout << "MCAP 2.1.3 " << mode << ": 12 binary messages, schemas/channels, timestamps, "
      << "indexed windows/filters/order and four malformed files passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "MCAP contract failed: " << error.what() << '\n';
    return 1;
  }
}
