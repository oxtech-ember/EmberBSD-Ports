TEST_F(EnvironmentTest, V8WrappedFunctionCacheDetails) {
  v8::HandleScope scope(isolate_);
  auto context = node::NewContext(isolate_);
  v8::Context::Scope context_scope(context);
  isolate_->ClearCachesForTesting();
  using SC = v8::ScriptCompiler;
  v8::ScriptOrigin origin(v8::String::NewFromUtf8Literal(isolate_, "embedder-cache-result.js"));
  auto code = v8::String::NewFromUtf8Literal(isolate_, "return parameter + 4917;");
  v8::Local<v8::String> args[] = {v8::String::NewFromUtf8Literal(isolate_, "parameter")};
  auto invalid = [] { return new SC::CachedData(new uint8_t[64](), 64, SC::CachedData::BufferOwned); };
  {
    SC::Source source(code, origin, invalid());
    v8::Local<v8::Function> function;
    ASSERT_TRUE(SC::CompileFunction(context, &source, 1, args, 0, nullptr,
                                    SC::kConsumeCodeCache).ToLocal(&function));
    EXPECT_EQ(source.GetCompilationDetails().in_memory_cache_result, SC::InMemoryCacheResult::kMiss);
    EXPECT_TRUE(source.GetCachedData()->rejected);
  }
  {
    SC::Source source(code, origin, invalid());
    v8::Local<v8::Function> function;
    ASSERT_TRUE(SC::CompileFunction(context, &source, 1, args, 0, nullptr,
                                    SC::kConsumeCodeCache).ToLocal(&function));
    EXPECT_EQ(source.GetCompilationDetails().in_memory_cache_result, SC::InMemoryCacheResult::kHit);
    EXPECT_FALSE(source.GetCachedData()->rejected);
    v8::Local<v8::Value> argv[] = {v8::Integer::New(isolate_, 3)};
    EXPECT_EQ(function->Call(context, v8::Undefined(isolate_), 1, argv)
                  .ToLocalChecked()->Int32Value(context).FromJust(), 4920);
  }
}
