extern int unintended_symbol(void);
__attribute__((visibility("default"))) int run(void) { return unintended_symbol(); }
