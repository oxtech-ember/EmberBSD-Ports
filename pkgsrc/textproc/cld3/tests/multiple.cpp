// Execute the unchanged upstream mixed-language test independently of its
// prediction test, which has two known model misclassifications on both hosts.
#define main cld3_upstream_main
#include "nnet_lang_id_test.cc"
#undef main
int main()
{
    return chrome_lang_id::nnet_lang_id_test::TestMultipleLanguagesInInput() ? 0 : 1;
}
