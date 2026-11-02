// Author: Kerwin
// Thin wrapper around the separately attributed QQ-compatible DES implementation.
#include "third_party/qq_des/des.h"
__declspec(dllexport) int __cdecl qrc_decrypt(unsigned char* buffer, int length) {
    BYTE keys[3][8]={{'!','@','#',')','(','N','H','L'},
                    {'1','2','3','Z','X','C','!','@'},
                    {'!','@','#',')','(','*','$','%'}};
    BYTE schedule[16][6];
    if(length<=0 || length%8)return -1;
    for(int phase=0;phase<3;phase++) {
        des_key_setup(keys[phase],schedule,phase==1?DES_ENCRYPT:DES_DECRYPT);
        for(int i=0;i<length;i+=8)des_crypt(buffer+i,buffer+i,schedule);
    }
    return 0;
}
