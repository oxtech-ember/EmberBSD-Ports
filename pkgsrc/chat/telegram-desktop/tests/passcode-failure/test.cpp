#include "ui/passcode_strength.h"
#include <zxcvbn-dictionary.h>
#include <QString>
#include <cstdio>
extern "C" {
extern const ZxcvbnDictionaryData TelegramZxcvbnDictionary = {};
ZxcvbnDictionary *ZxcvbnDictionaryCreate(const ZxcvbnDictionaryData *) { return nullptr; }
void ZxcvbnDictionaryFree(ZxcvbnDictionary *) {}
double ZxcvbnMatchWithDictionary(const ZxcvbnDictionary *,const char *,const char *[],ZxcMatch_t **out) { if(out)*out=nullptr; return -1; }
void ZxcvbnFreeInfo(ZxcMatch_t *) {}
}
int main() {
 const auto result = Ui::EstimatePasscodeStrength(QString(8000000, QChar('a')));
 std::printf("band=%d advice=%d\n",int(result.band),int(result.advice));
 if (result.band != Ui::PasscodeStrengthBand::Weak || result.advice != Ui::PasscodeStrengthAdvice::AddVariety) return 1;
 puts("estimator failure remains weak: PASS");
}
