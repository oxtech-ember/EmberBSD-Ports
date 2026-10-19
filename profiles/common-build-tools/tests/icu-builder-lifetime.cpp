// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
// Compile the real ICU implementation. Do not replace its data or iterator code.
#include "collationdatabuilder.cpp"
#include "collationroot.h"
#include "utf16collationiterator.h"
#include "unicode/normalizer2.h"
#include "unicode/uclean.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>

U_NAMESPACE_USE

class ObservedBuilder : public DataBuilderCollationIterator {
public:
    using DataBuilderCollationIterator::DataBuilderCollationIterator;

    bool hasNullTrie() const {
        unsigned char bytes[sizeof(trie)];
        const UTrie2 *nullTrie = nullptr;
        unsigned char nullBytes[sizeof(nullTrie)];
        std::memcpy(bytes, &trie, sizeof(bytes));
        std::memcpy(nullBytes, &nullTrie, sizeof(nullBytes));
        return std::memcmp(bytes, nullBytes, sizeof(bytes)) == 0;
    }
};

class ObservedRuntime : public UTF16CollationIterator {
public:
    using UTF16CollationIterator::UTF16CollationIterator;

    bool hasTrie(const UTrie2 *expected) const { return trie == expected; }
};

static int check(unsigned char fill, bool functional) {
    UErrorCode status = U_ZERO_ERROR;
    const CollationData *root = CollationRoot::getData(status);
    if (U_FAILURE(status) || root == nullptr) {
        std::fprintf(stderr, "FAIL: real ICU root data: %s\n", u_errorName(status));
        return 2;
    }
    CollationDataBuilder builder(false, status);
    builder.initForTailoring(root, status);
    if (U_FAILURE(status)) {
        std::fprintf(stderr, "FAIL: real ICU builder: %s\n", u_errorName(status));
        return 2;
    }
    alignas(ObservedBuilder) unsigned char storage[sizeof(ObservedBuilder)];
    std::memset(storage, fill, sizeof(storage));
    auto *iterator = ::new (static_cast<void *>(storage)) ObservedBuilder(builder);
    if (!iterator->hasNullTrie()) {
        std::fprintf(stderr, "FAIL: builder cached an unconstructed trie; fill=%u\n", fill);
        iterator->~ObservedBuilder();
        return 1;
    }
    if (functional) {
        const char16_t *texts[] = {u"abc", u"123", u"\u00e4\u0301", u"\ud55c", u"\U0001f600"};
        unsigned int textIndex = 0;
        for (const char16_t *text : texts) {
            // CollationBuilder passes NFD text to CollationDataBuilder::getCEs().
            UnicodeString input;
            const Normalizer2 *nfd = Normalizer2::getNFDInstance(status);
            if (U_SUCCESS(status) && nfd != nullptr) {
                nfd->normalize(UnicodeString(text), input, status);
            }
            if (U_FAILURE(status) || nfd == nullptr) {
                std::fprintf(stderr, "FAIL: real NFD preparation: %s\n", u_errorName(status));
                iterator->~ObservedBuilder();
                return 2;
            }
            ObservedRuntime runtime(root, false, input.getBuffer(), input.getBuffer(),
                                    input.getBuffer() + input.length());
            if (!runtime.hasTrie(root->trie)) {
                std::fprintf(stderr, "FAIL: the existing constructor lost its real trie\n");
                iterator->~ObservedBuilder();
                return 1;
            }
            int64_t actual[Collation::MAX_EXPANSION_LENGTH] = {};
            int32_t length = iterator->fetchCEs(input, 0, actual, 0);
            int32_t index = 0;
            for (;;) {
                int64_t expected = runtime.nextCE(status);
                if (U_FAILURE(status)) {
                    std::fprintf(stderr, "FAIL: runtime collation: %s\n", u_errorName(status));
                    iterator->~ObservedBuilder();
                    return 2;
                }
                if (expected == Collation::NO_CE) {
                    break;
                }
                if (expected == 0) {
                    continue;
                }
                if (index >= length || index >= Collation::MAX_EXPANSION_LENGTH ||
                    actual[index] != expected) {
                    std::fprintf(stderr, "FAIL: real builder/runtime collation differs: "
                                 "text=%u index=%d length=%d actual=%016llx expected=%016llx\n",
                                 textIndex, index, length,
                                 static_cast<unsigned long long>(
                                     index < Collation::MAX_EXPANSION_LENGTH ? actual[index] : 0),
                                 static_cast<unsigned long long>(expected));
                    iterator->~ObservedBuilder();
                    return 1;
                }
                ++index;
            }
            ++textIndex;
            if (index != length) {
                std::fprintf(stderr, "FAIL: real collation element counts differ\n");
                iterator->~ObservedBuilder();
                return 1;
            }
        }
    }
    iterator->~ObservedBuilder();
    std::printf("PASS: fill=%u functional=%d layout=%zu,%zu,%zu\n", fill, functional,
                sizeof(CollationIterator), sizeof(DataBuilderCollationIterator), sizeof(CollationData));
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 3 || (std::strcmp(argv[1], "constructor") != 0 &&
                      std::strcmp(argv[1], "functional") != 0)) {
        return 2;
    }
    char *end = nullptr;
    unsigned long fill = std::strtoul(argv[2], &end, 10);
    if (end == argv[2] || *end != '\0' || fill > 255) {
        return 2;
    }
    int result = check(static_cast<unsigned char>(fill), std::strcmp(argv[1], "functional") == 0);
    u_cleanup();
    return result;
}
