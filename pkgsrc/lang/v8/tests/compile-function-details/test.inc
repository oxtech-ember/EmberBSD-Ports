// Append to V8 test/cctest/test-api.cc.
TEST(CompileFunctionInMemoryCacheResult) {
  LocalContext env;
  v8::Isolate* isolate = env.isolate();
  v8::HandleScope scope(isolate);
  using SC = v8::ScriptCompiler;
  const v8::ScriptOrigin origin(v8_str("embedder-cache-result.js"));
  const auto code = v8_str("return parameter + 4917;");
  v8::Local<v8::String> args[] = {v8_str("parameter")};
  auto invalid = []() {
    auto* data = new uint8_t[64]();
    return new SC::CachedData(data, 64, SC::CachedData::BufferOwned);
  };
  v8::Local<v8::Function> first;
  {
    SC::Source source(code, origin, invalid());
    CHECK(SC::CompileFunction(env.local(), &source, 1, args, 0, nullptr,
                              SC::kConsumeCodeCache).ToLocal(&first));
    CHECK_EQ(source.GetCompilationDetails().in_memory_cache_result,
             SC::InMemoryCacheResult::kMiss);
    CHECK(source.GetCachedData()->rejected);
  }
  {
    SC::Source source(code, origin, invalid());
    v8::Local<v8::Function> result;
    CHECK(SC::CompileFunction(env.local(), &source, 1, args, 0, nullptr,
                              SC::kConsumeCodeCache).ToLocal(&result));
    CHECK_EQ(source.GetCompilationDetails().in_memory_cache_result,
             SC::InMemoryCacheResult::kHit);
    // The isolate cache wins; the embedder bytes were not inspected.
    CHECK(!source.GetCachedData()->rejected);
    v8::Local<v8::Value> argv[] = {v8::Integer::New(isolate, 3)};
    CHECK_EQ(result->Call(env.local(), v8::Undefined(isolate), 1, argv)
                 .ToLocalChecked()->Int32Value(env.local()).FromJust(), 4920);
  }
}
