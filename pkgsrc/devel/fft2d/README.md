The source archive is Takuya Ooura's original 2006-12-28 FFT2D package:
https://www.kurims.kyoto-u.ac.jp/~ooura/fft.html. `LICENSE.ooura` in the prepared tree
records the current author's license from that page. Preserve the original
`readme2d.txt` as well.

`patches/patch-fft_declarations` adds `fft.h` and `fft2d.h` are Apache-2.0 declarations from the
TensorFlow Authors, 2017, `third_party/fft2d` in commit
9edd58f895c58c3db484a9e39ab2e953baca4bca. The latter include guard is renamed
so both public declarations can be included in one translation unit. Their
copyright and license headers remain intact; `LICENSE.apache-2.0` supplies the complete license.
