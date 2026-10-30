#include <temporal_rs/PlainDate.hpp>
#include <temporal_rs/AnyCalendarKind.hpp>
#include <temporal_rs/Disambiguation.hpp>
#include <temporal_rs/OffsetDisambiguation.hpp>
#include <temporal_rs/ZonedDateTime.hpp>
#include <cassert>
#include <utility>
int main() {
  auto result = temporal_rs::PlainDate::try_new(2024, 2, 29, temporal_rs::AnyCalendarKind::Iso);
  assert(result.is_ok());
  auto date = std::move(result).ok();
  assert(date && (*date)->year() == 2024 && (*date)->month() == 2 && (*date)->day() == 29);
  auto invalid = temporal_rs::PlainDate::try_new(2023, 2, 29, temporal_rs::AnyCalendarKind::Iso);
  assert(!invalid.is_ok());
  auto before = temporal_rs::ZonedDateTime::from_utf8("2024-03-10T01:59:00-05:00[America/New_York]", temporal_rs::Disambiguation::Compatible, temporal_rs::OffsetDisambiguation::Reject);
  auto after = temporal_rs::ZonedDateTime::from_utf8("2024-03-10T03:00:00-04:00[America/New_York]", temporal_rs::Disambiguation::Compatible, temporal_rs::OffsetDisambiguation::Reject);
  assert(before.is_ok() && after.is_ok());
  auto earlier = std::move(before).ok();
  auto later = std::move(after).ok();
  assert(earlier && later && (*earlier)->hour() == 1 && (*later)->hour() == 3);
  assert((*earlier)->offset_nanoseconds() == -18000000000000LL && (*later)->offset_nanoseconds() == -14400000000000LL);
}
