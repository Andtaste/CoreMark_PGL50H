# new_core — 82 MHz 双发采纳基线

本分支保存用户指定的 new_core 项目。实际PLL82 MHz，布局22／路由4，已验证STA估算Fmax82.271 MHz，IPC1.040582。布线后11029 LUT／4476 FF／709分布RAM／48 DRM／4 APM。

两个分支均以项目根目录组织：`test`为75 MHz单发旧版，`main`为当前82 MHz双发版。
CPU、SoC和外设共17个RTL文件与对应采纳版本逐字节一致。
发布适配仅处理初始化镜像路径、构建脚本路径及发布记录，没有改变CPU流水线或增加组合控制链。

## 工程入口

- PDS项目：`hardware/pds/new_core.pds`
- 完整构建入口：`tools/build_release.py`；分阶段Tcl位于`hardware/pds/`
- RTL：`hardware/pds/source/`
- 软件及CoreMark：`sw/`
- 发布版本、输入SHA与改动范围：`docs/published_release.json`
- 路径适配前的原始采纳记录：`docs/release_source_records/`
- 本发布目录原生构建验证：`docs/published_build/`（原始STA和资源报告）

## 构建

需要Windows、Python3和紫光PDS2022.2-SP1-Lite，器件PGL50H-6 FBG484，板级输入50 MHz。
在仓库根目录运行：

```powershell
python tools/build_release.py --verify-only
python tools/build_release.py --pds-home E:/pango/PDS_2022.2-SP1-Lite
```

82 MHz完整构建请使用以上Python入口：先运行`new_core.tcl`生成新网表，再由Python校验并安装检查点，最后运行`route_verified.tcl`。不要单独跳过校验直接运行布线阶段。
初始化镜像使用项目相对路径，Tcl入口会切换到工程目录。

82 MHz入口先重新编译、综合和映射，再核对源码、IP、镜像、约束SHA及完整结构网表，核对通过后装入已验证的固定映射检查点并重新布局布线。
寄存器文件128个等价RAM读副本的实例名可能随综合变化，因此seed必须与映射输入一起固定。
修改任何输入后，校验会拒绝旧检查点；请使用`hardware/pds/rebuild_from_rtl.tcl`生成新映射并重新收敛。

原短跑固件仍打印75 MHz元数据；以上IPC取独立周期/退休计数。真实PLL为82 MHz，未声称板上正式长跑成绩。

## 发布范围

保留可构建输入、软件、初始化镜像、功能夹具、研究文本记录和当前版本的关键原始时序证据。
不提交可再生的PDS/仿真缓存、本机备份目录、波形及失败试验的二进制检查点。
历史研究目录中的旧manifest描述原本机完整归档；本次Git发布范围以`docs/published_release.json`为准。
重新综合可能改变布局结果，既有历史性能不能自动等同于任意一次重新实现的成绩。尚未上板。
