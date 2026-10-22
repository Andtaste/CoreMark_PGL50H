# new_core — 82 MHz / CoreMark5000 上板版本

当前主分支已准备5000次迭代的CoreMark v1.0性能镜像，软件计时与实际PLL均为82 MHz，UART115200/8N1。CPU、SoC与外设共17个RTL文件保持采纳版本原字节。

- **直接下载文件：`output/board5000/top.sbit`**，同目录附SHA256与操作说明。
- **PDS工程：`hardware/pds/new_core.pds`**；完整受保护重建入口：`python tools/build_board5000.py`。
- [上板说明](docs/board5000_20261022/BOARD_RUN.md)、[配置与文件校验记录](docs/board5000_20261022/board_manifest.json)。

新的5000次镜像已通过原生82MHz四角时序：布局0 / 路由1，估算Fmax82.183MHz，慢角setup+0.027ns；布线后11039LUT /4476FF /709分布RAM /48DRM /4APM。
已检查全部16384条初始化字、实际UART分频712、验证种子短跑CRC和独立计数。**按用户要求不完成5000次全程RTL仿真，尚未上板，当前没有5000次正式实测成绩。**

在仓库根目录执行：

```powershell
python tools/build_board5000.py --verify-only
# 需要重新生成下载文件时：
python tools/build_board5000.py --pds-home E:/pango/PDS_2022.2-SP1-Lite
# 下载后，打开串口并按KEY1重新运行；替换成CP2102的COM号：
.\tools\capture_board5000.ps1 -Port COM13
```

构建使用本版本自己的5000次映射/布局检查点：先重新综合并核对所有输入与完整结构网表，再从冻结布局进行路由，四角通过后生成下载文件。源文件、镜像、IP或约束变化会使旧检查点失效；请勿跳过校验。`new_core.tcl`是综合阶段，完整构建使用Python入口。
FPGA配置JTAG临时下载，与未实现的CPU调试JTAG不同；UART采集不需要UART RX或DTM。暂未加入ILA。

`test`分支保留旧75MHz单发项目；此前主分支10次诊断镜像保留在Git历史提交`0c9a66b`。历史研究记录中的本机路径、旧manifest和短程分数仅用于追溯，当前发布以board_manifest和本次上板说明为准。
