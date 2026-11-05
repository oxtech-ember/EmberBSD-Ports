#include <nnet_language_identifier.h>
#include <cmath>
#include <iostream>
#include <string>

int main()
{
    chrome_lang_id::NNetLanguageIdentifier identifier(0, 1000);
    const std::string english = "This is a message written in English. The application should identify the language correctly before offering a translation.";
    const std::string russian = "Это сообщение написано на русском языке. Приложение должно правильно определить язык текста перед предложением перевода.";
    for (const auto &sample : {std::pair{english, std::string("en")},
                               std::pair{russian, std::string("ru")}}) {
        const auto result = identifier.FindLanguage(sample.first);
        if (result.language != sample.second || !std::isfinite(result.probability)) {
            std::cerr << "language mismatch: " << result.language << '\n';
            return 1;
        }
    }
    for (const auto &sample : {std::string(), std::string("\xff\xfe\xc0\xaf", 4)}) {
        for (const auto &result : identifier.FindTopNMostFreqLangs(sample, 3)) {
            if (result.language != chrome_lang_id::NNetLanguageIdentifier::kUnknown ||
                !std::isfinite(result.probability)) {
                std::cerr << "invalid input was not rejected\n";
                return 2;
            }
        }
    }
    std::cout << "CLD3 English/Russian/empty/malformed UTF-8 PASS\n";
}
