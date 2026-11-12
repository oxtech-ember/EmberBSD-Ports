struct Info {
  enum class Id { value };
  constexpr Id GetId() const { return Id::value; }
};
template <typename T> struct Builder {
  static constexpr Info Build() { return {}; }
};
template <Info::Id id, typename T>
bool __attribute__((warn_unused_result)) convert(T*);
template <>
bool __attribute__((warn_unused_result))
convert<Builder<int>::Build().GetId(), int>(int*);
