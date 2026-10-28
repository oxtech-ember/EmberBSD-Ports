#include <uvwasi.h>

int main(void)
{
	uvwasi_t instance;
	uvwasi_options_t options;

	uvwasi_options_init(&options);
	if (uvwasi_init(&instance, &options) != UVWASI_ESUCCESS)
		return 1;
	uvwasi_destroy(&instance);
	return 0;
}
