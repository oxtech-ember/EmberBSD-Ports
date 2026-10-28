#include <hdr/hdr_histogram.h>
#include <stdint.h>
int main(void) {
  struct hdr_histogram *h = 0;
  if (hdr_init(1, 10000, 3, &h) != 0 || !h) return 1;
  if (!hdr_record_value(h, 42) || !hdr_record_value(h, 84)) return 2;
  if (hdr_record_value(h, INT64_C(1000000000))) return 3;
  if (h->total_count != 2 || hdr_value_at_percentile(h, 100.0) != 84) return 4;
  hdr_close(h);
  return 0;
}
