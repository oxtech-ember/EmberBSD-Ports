#include <wx/platform.h>
#include <wx/setup.h>
#include <wx/version.h>
static_assert(wxUSE_GUI, "wx GUI required");
int wx_header_contract() { return wxMAJOR_VERSION * 10000 + wxMINOR_VERSION * 100 + wxRELEASE_NUMBER; }
