#include <merve_c.h>
#include <string.h>
int main(void) {
  const char *src = "exports.foo = 1;";
  merve_analysis a = merve_parse_commonjs(src, strlen(src), 0);
  if (!a || !merve_is_valid(a) || merve_get_exports_count(a) != 1) return 1;
  merve_string name = merve_get_export_name(a, 0);
  if (name.length != 3 || memcmp(name.data, "foo", 3)) return 2;
  merve_free(a);
  src = "import 'x';";
  a = merve_parse_commonjs(src, strlen(src), 0);
  if (!a || merve_is_valid(a)) return 3;
  merve_free(a);
  return 0;
}
