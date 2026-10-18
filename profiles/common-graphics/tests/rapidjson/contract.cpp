// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted), installed RapidJSON ownership and JSON checks.
#include <rapidjson/document.h>
#include <rapidjson/pointer.h>
#include <rapidjson/schema.h>
#include <cstdio>
#include <cstddef>
#include <cstring>

int main() {
    const rapidjson::Pointer::Token tokens[] = {
        {"items", 5, rapidjson::kPointerInvalidIndex}, {"0", 1, 0}
    };
    rapidjson::Pointer original(tokens, 2);
    rapidjson::Pointer appended = original.Append("value");
    if (!(appended == rapidjson::Pointer("/items/0/value"))) return 1;
    if (appended.GetTokens()[0].name == tokens[0].name) return 2;
    if (!(original == rapidjson::Pointer("/items/0"))) return 3;

    alignas(std::max_align_t) unsigned char buffer[256];
    {
        rapidjson::MemoryPoolAllocator<> pool(buffer, sizeof buffer, 128);
        {
            rapidjson::MemoryPoolAllocator<> shared(pool);
            if (!pool.Shared()) return 4;
            std::memset(shared.Malloc(4096), 0x5a, 4096);
        }
        if (pool.Shared()) return 5;
        pool.Clear();
        if (pool.Size() != 0) return 6;
        std::memset(pool.Malloc(4096), 0xa5, 4096);
    }

    rapidjson::Document document;
    document.Parse("{\"items\":[{\"value\":42}],\"text\":\"caf\\u00e9\"}");
    if (document.HasParseError()) return 7;
    const rapidjson::Value* value = appended.Get(document);
    if (!value || !value->IsInt() || value->GetInt() != 42) return 8;
    if (std::strcmp(document["text"].GetString(), "caf\xc3\xa9") != 0) return 9;
    rapidjson::Document schema;
    schema.Parse("{\"type\":\"object\",\"required\":[\"items\"],\"properties\":{\"items\":{\"type\":\"array\"}}}");
    if (schema.HasParseError()) return 10;
    rapidjson::SchemaDocument compiled(schema);
    rapidjson::SchemaValidator validator(compiled);
    if (!document.Accept(validator) || !validator.IsValid()) return 11;
    validator.Reset();
    document["items"].SetInt(42);
    if (document.Accept(validator) || validator.IsValid()) return 12;
    std::puts("PASS: installed pointer ownership, shared stack pool, DOM, UTF-8, schema and negative input.");
    return 0;
}
