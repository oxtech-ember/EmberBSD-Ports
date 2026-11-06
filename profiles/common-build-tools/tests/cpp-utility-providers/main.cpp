#include <nanoflann.hpp>
#include <parson.h>
#include <picosha2.h>
#include <rapidcsv.h>

#include <sstream>
#include <string>

int main()
{
    std::istringstream csv("value\n7\n");
    rapidcsv::Document document(csv);
    if (document.GetCell<int>(0, 0) != 7)
        return 1;

    const std::string digest = picosha2::hash256_hex_string(std::string("x"));
    if (digest.size() != 64)
        return 2;

    JSON_Value* value = json_value_init_object();
    if (!value)
        return 3;
    json_value_free(value);

    // Keep nanoflann's public index parameter type in the consumer interface.
    nanoflann::KDTreeSingleIndexAdaptorParams indexParams(10);
    (void)indexParams;
    return 0;
}
