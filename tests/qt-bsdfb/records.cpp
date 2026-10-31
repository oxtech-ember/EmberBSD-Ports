#include "qbsdfbrecordbuffer_p.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <type_traits>
#include <vector>

namespace {

struct TestRecord
{
    std::uint32_t type;
    std::int32_t value;
    std::int64_t seconds;
    std::int64_t nanos;
};

static_assert(sizeof(TestRecord) == 24, "fixture record must be 24 bytes");
static_assert(std::is_trivially_copyable<TestRecord>::value,
              "wscons records must support byte-copy decoding");

constexpr std::array<TestRecord, 3> kRecords{{
    {1U, -17, 1700000000LL, 123456789LL},
    {2U, 42, 1700000000LL, 123456789LL},
    {3U, -9001, 1700000001LL, 123456789LL},
}};

int failures = 0;

#define CHECK(condition) \
    do { \
        if (!(condition)) { \
            std::fprintf(stderr, "%s:%d: check failed: %s\n", \
                         __FILE__, __LINE__, #condition); \
            ++failures; \
        } \
    } while (false)

std::array<char, sizeof(TestRecord)> serializeFixture(const TestRecord &record)
{
    std::array<char, sizeof(TestRecord)> bytes{};
    std::memcpy(bytes.data(), &record, sizeof(record));
    return bytes;
}

template<std::size_t Count>
std::array<char, Count * sizeof(TestRecord)> serializeFixtures(
    const std::array<TestRecord, Count> &records)
{
    std::array<char, Count * sizeof(TestRecord)> bytes{};
    for (std::size_t i = 0; i < Count; ++i)
        std::memcpy(bytes.data() + i * sizeof(TestRecord), &records[i], sizeof(TestRecord));
    return bytes;
}

bool sameRecord(const TestRecord &actual, const TestRecord &expected)
{
    return actual.type == expected.type
        && actual.value == expected.value
        && actual.seconds == expected.seconds
        && actual.nanos == expected.nanos;
}

bool sameRecords(const std::vector<TestRecord> &actual,
                 const TestRecord *expected, std::size_t count)
{
    if (actual.size() != count)
        return false;
    for (std::size_t i = 0; i < count; ++i) {
        if (!sameRecord(actual[i], expected[i]))
            return false;
    }
    return true;
}

template<std::size_t Capacity>
bool appendBytes(QBsdFb::RecordBuffer<TestRecord, Capacity> &buffer,
                 const char *bytes, std::size_t count,
                 std::vector<TestRecord> &decoded)
{
    if (count > buffer.writableBytes())
        return false;
    if (count != 0)
        std::memcpy(buffer.writeData(), bytes, count);
    return buffer.append(count, [&decoded](const TestRecord &record) {
        decoded.push_back(record);
    });
}

void everyByteSplitAcrossTwoRecordsDecodesExactly()
{
    const std::array<TestRecord, 2> expected{{kRecords[0], kRecords[1]}};
    const auto bytes = serializeFixtures(expected);

    for (std::size_t split = 1; split < bytes.size(); ++split) {
        QBsdFb::RecordBuffer<TestRecord, 64> buffer;
        std::vector<TestRecord> decoded;
        CHECK(appendBytes(buffer, bytes.data(), split, decoded));
        CHECK(appendBytes(buffer, bytes.data() + split, bytes.size() - split, decoded));
        CHECK(sameRecords(decoded, expected.data(), expected.size()));
        CHECK(buffer.pendingBytes() == 0);
    }
}

void everyByteSplitAcrossThreeRecordsDecodesExactly()
{
    const auto bytes = serializeFixtures(kRecords);

    for (std::size_t split = 1; split < bytes.size(); ++split) {
        QBsdFb::RecordBuffer<TestRecord, 96> buffer;
        std::vector<TestRecord> decoded;
        CHECK(appendBytes(buffer, bytes.data(), split, decoded));
        CHECK(appendBytes(buffer, bytes.data() + split, bytes.size() - split, decoded));
        CHECK(sameRecords(decoded, kRecords.data(), kRecords.size()));
        CHECK(buffer.pendingBytes() == 0);
    }
}

void byteAtATimeReadsReassembleCompleteRecords()
{
    const std::array<TestRecord, 2> expected{{kRecords[0], kRecords[1]}};
    const auto bytes = serializeFixtures(expected);
    QBsdFb::RecordBuffer<TestRecord> buffer;
    std::vector<TestRecord> decoded;

    for (char byte : bytes)
        CHECK(appendBytes(buffer, &byte, 1, decoded));

    CHECK(sameRecords(decoded, expected.data(), expected.size()));
    CHECK(buffer.pendingBytes() == 0);
}

void multipleCompleteRecordsAndPartialTailArePreserved()
{
    const auto bytes = serializeFixtures(kRecords);
    constexpr std::size_t tailBytes = 5;
    QBsdFb::RecordBuffer<TestRecord, 64> buffer;
    std::vector<TestRecord> decoded;

    CHECK(appendBytes(buffer, bytes.data(), 2 * sizeof(TestRecord) + tailBytes, decoded));
    CHECK(sameRecords(decoded, kRecords.data(), 2));
    CHECK(buffer.pendingBytes() == tailBytes);
    CHECK(appendBytes(buffer, bytes.data() + 2 * sizeof(TestRecord) + tailBytes,
                      sizeof(TestRecord) - tailBytes, decoded));
    CHECK(sameRecords(decoded, kRecords.data(), kRecords.size()));
    CHECK(buffer.pendingBytes() == 0);
}

void exactCapacityOversizeRejectionAndSameTimestampRecords()
{
    const auto bytes = serializeFixtures(kRecords);
    QBsdFb::RecordBuffer<TestRecord, 32> buffer;
    std::vector<TestRecord> decoded;

    CHECK(appendBytes(buffer, bytes.data(), 32, decoded));
    CHECK(decoded.size() == 1);
    if (decoded.size() == 1)
        CHECK(sameRecord(decoded[0], kRecords[0]));
    CHECK(buffer.pendingBytes() == 8);
    CHECK(buffer.writableBytes() == 24);

    std::memcpy(buffer.writeData(), bytes.data() + 32, 24);
    CHECK(!buffer.append(25, [&decoded](const TestRecord &record) {
        decoded.push_back(record);
    }));
    CHECK(buffer.pendingBytes() == 8);
    CHECK(buffer.writableBytes() == 24);
    CHECK(decoded.size() == 1);

    CHECK(buffer.append(24, [&decoded](const TestRecord &record) {
        decoded.push_back(record);
    }));
    CHECK(decoded.size() == 2);
    if (decoded.size() == 2)
        CHECK(sameRecord(decoded[1], kRecords[1]));
    CHECK(kRecords[0].seconds == kRecords[1].seconds);
    CHECK(kRecords[0].nanos == kRecords[1].nanos);
    CHECK(kRecords[0].type != kRecords[1].type);
    CHECK(kRecords[0].value != kRecords[1].value);
    CHECK(buffer.pendingBytes() == 8);

    CHECK(appendBytes(buffer, bytes.data() + 56, 16, decoded));
    CHECK(sameRecords(decoded, kRecords.data(), kRecords.size()));
    CHECK(buffer.pendingBytes() == 0);
}

void zeroByteAppendDoesNotEmitOrDiscardResidual()
{
    const auto bytes = serializeFixture(kRecords[0]);
    QBsdFb::RecordBuffer<TestRecord, 32> buffer;
    std::vector<TestRecord> decoded;

    CHECK(appendBytes(buffer, bytes.data(), 7, decoded));
    CHECK(decoded.empty());
    CHECK(buffer.pendingBytes() == 7);
    CHECK(buffer.append(0, [&decoded](const TestRecord &record) {
        decoded.push_back(record);
    }));
    CHECK(decoded.empty());
    CHECK(buffer.pendingBytes() == 7);
    CHECK(appendBytes(buffer, bytes.data() + 7, bytes.size() - 7, decoded));
    CHECK(sameRecords(decoded, &kRecords[0], 1));
    CHECK(buffer.pendingBytes() == 0);
}

} // namespace

int main()
{
    everyByteSplitAcrossTwoRecordsDecodesExactly();
    everyByteSplitAcrossThreeRecordsDecodesExactly();
    byteAtATimeReadsReassembleCompleteRecords();
    multipleCompleteRecordsAndPartialTailArePreserved();
    exactCapacityOversizeRejectionAndSameTimestampRecords();
    zeroByteAppendDoesNotEmitOrDiscardResidual();
    return failures == 0 ? 0 : 1;
}
