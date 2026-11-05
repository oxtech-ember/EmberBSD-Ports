#include <srtp2/srtp.h>
int main(void)
{
    if (srtp_init() != srtp_err_status_ok)
        return 1;
    return srtp_shutdown() != srtp_err_status_ok;
}
