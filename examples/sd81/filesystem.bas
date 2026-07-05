#include <mcu.bas>
#include <input.bas>
dim version as ubyte
version = McuVersion()
print "SD81 OS version: ";version
print "Current dir: "; McuPwd()
if McuCd("/")=0 then print "Change to root dir" else print "error"
if McuCd("/test")=0 then print "Change to test dir" else print "error"
McuDirPrint("/test/*.*")
McuLoad("/DEMO.WAV",0)
input a$