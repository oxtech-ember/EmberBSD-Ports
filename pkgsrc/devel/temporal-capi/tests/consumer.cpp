#include <temporal_rs/PlainDate.hpp>
#include <temporal_rs/AnyCalendarKind.hpp>
#include <cassert>
#include <utility>
int main() {
  auto result = temporal_rs::PlainDate::try_new(2024, 2, 29, temporal_rs::AnyCalendarKind::Iso);
  assert(result.is_ok());
  auto date = std::move(result).ok();
  assert(date && (*date)->year() == 2024 && (*date)->month() == 2 && (*date)->day() == 29);
  auto invalid = temporal_rs::PlainDate::try_new(2023, 2, 29, temporal_rs::AnyCalendarKind::Iso);
  assert(!invalid.is_ok());
}
