#include <vtkMotionFXCFGGrammar.h>

#include <cassert>
#include <string>

namespace pegtl = tao::pegtl;
struct Word : pegtl::plus<pegtl::alpha> {};

int main()
{
  std::string motion = "motions { motion { name value } }";
  pegtl::text_copy_input<pegtl::ascii::scan::lf_crlf, std::string, std::string, std::string> in(
    "motion.cfg", motion);
  assert(pegtl::parse<MotionFX::CFG::Grammar>(in));

  std::string invalid = "word!";
  pegtl::text_copy_input<pegtl::ascii::scan::lf_crlf, std::string, std::string, std::string> bad(
    "constructRule", invalid);
  try
  {
    (void)pegtl::parse<pegtl::seq<Word, pegtl::eof>>(bad);
    return 1;
  }
  catch (decltype(bad)::parse_error_t& err)
  {
    const auto p = err.position_object();
    assert(!bad.line_view_at(p).empty());
    assert(p.column == 5);
  }

  std::string trace_text = "motions { motion { name value } }";
  pegtl::text_copy_input<pegtl::ascii::scan::lf_crlf, std::string, std::string, std::string> trace_in(
    "motion.cfg", trace_text);
  assert(pegtl::standard_trace<MotionFX::CFG::Grammar>(trace_in));
}
