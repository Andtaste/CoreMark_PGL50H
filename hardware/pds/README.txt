new_core 本机主工程：83 MHz / CoreMark5000 / 比较指令修复版
直接打开new_core.pds，或双击根目录open_main.cmd。
PGL50H-6 FBG484 / MES50HP / 50MHz输入。
布局种子9，布线种子1，fanout64，四角优化和hold修复已保存。
固件o3_inline80，5000次，原ROM保持不变。
下载download/top.sbit，或根目录output/board83/top.sbit。
UART 115200/8N1/无流控，按KEY1启动；PuTTY Terminal可启用Implicit CR in every LF。
预期CRC PASS，Iterations/Sec360.941214，CoreMark/MHz4.348689，IPC1.105，CPI0.904。
原计数器输入下新网表报告重放及63项回归通过；新文件尚未实板验证。
时序Fmax83.368MHz，最差setup+0.053ns。
完整重建：tools/run.ps1 -Task pds。必须确认All Constraints Met。
旧主工程保留于hardware/pds_before_compare_fix_20261023；其中旧文件存在比较错误，仅作对照。
SHA256: 6fda0a4e7f3d185d28fa719e4ca0da9b516b5a43a5ead92bb6f264fa4be97f79
