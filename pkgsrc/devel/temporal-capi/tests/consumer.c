#include <PlainDate.h>
#include <assert.h>
int main(void) {
    temporal_rs_PlainDate_try_new_result good = temporal_rs_PlainDate_try_new(2024, 2, 29, AnyCalendarKind_Iso);
    assert(good.is_ok && temporal_rs_PlainDate_year(good.ok) == 2024);
    assert(temporal_rs_PlainDate_month(good.ok) == 2 && temporal_rs_PlainDate_day(good.ok) == 29);
    temporal_rs_PlainDate_destroy(good.ok);
    temporal_rs_PlainDate_try_new_result bad = temporal_rs_PlainDate_try_new(2023, 2, 29, AnyCalendarKind_Iso);
    assert(!bad.is_ok);
    return 0;
}
