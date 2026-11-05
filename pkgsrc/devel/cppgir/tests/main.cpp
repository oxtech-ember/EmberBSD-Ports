#include <gio/gio.hpp>
#include <cstring>
int main() {
  auto file = gi::repository::Gio::File::new_for_path("/tmp/ember-cppgir-check");
  auto path = file.get_path();
  return !path.c_str() || std::strcmp(path.c_str(), "/tmp/ember-cppgir-check");
}
