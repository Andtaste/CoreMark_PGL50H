/* Freestanding routines used by the GPL-2.0 application. */
#include <stddef.h>
#include <stdint.h>
typedef uint32_t AliasWord __attribute__((__may_alias__));
extern "C" void *memset(void *dst,int value,size_t n){
 unsigned char *p=(unsigned char *)dst;
 unsigned char byte=(unsigned char)value;
 while(n && ((uintptr_t)p & 3u)){*p++=byte;--n;}
 uint32_t word=(uint32_t)byte*0x01010101u;
 AliasWord *w=(AliasWord *)p;
 while(n>=16){w[0]=word;w[1]=word;w[2]=word;w[3]=word;w+=4;n-=16;}
 while(n>=4){*w++=word;n-=4;}
 p=(unsigned char *)w;
 while(n--)*p++=byte;
 return dst;
}
extern "C" void *memcpy(void *dst,const void *src,size_t n){unsigned char *d=(unsigned char *)dst;const unsigned char *s=(const unsigned char *)src;while(n--)*d++=*s++;return dst;}
extern "C" void *memmove(void *dst,const void *src,size_t n){unsigned char *d=(unsigned char *)dst;const unsigned char *s=(const unsigned char *)src;if(d<s){while(n--)*d++=*s++;}else {while(n){n--;d[n]=s[n];}}return dst;}
extern "C" char *strchr(const char *s,int c){do{if(*s==(char)c)return (char *)s;}while(*s++);return 0;}
extern "C" size_t strlen(const char *s){const char *p=s;while(*p)p++;return (size_t)(p-s);}
