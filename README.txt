CoreMark_PGL50H 项目框架
========================

当前状态
sw 已含从 TinyRISC-V 复制的软件源码与编译脚本。
其他目录当前只建立空目录，没有复制板级 RTL/IP/约束或生成工程文件。
创建框架时保留了 sw 的全部文件内容。

目录用途
hardware/pds/                新建 PDS 工程的位置
  source/top/                SoC 顶层 tinyriscv_soc_top.v
  source/core/               CPU RTL
  source/sys_bus/            RIB 等系统总线
  source/perips/             UART、ROM、RAM、Timer、GPIO
  source/debug/              CPU JTAG 调试模块
  source/utils/              公共 RTL 辅助模块
  constraints/              目标板 FDC 引脚/时序约束
  ipcore/pll/                目标器件的时钟 IP（按需要生成）
  ipcore/ram1/rtl/            目标器件的存储器 IP 内部代码
  ipcore/ram2/rtl/            目标器件的存储器 IP 内部代码
  synthesize/                预留：PDS 综合结果
  compile/                   预留：PDS 编译结果
  device_map/                预留：PDS 器件映射结果
  place_route/               预留：PDS 布局布线结果
  report_timing/             预留：PDS 时序报告
  generate_bitstream/        预留：PDS 配置文件
  logbackup/                 预留：PDS 历史日志
  constraint_backup/         预留：PDS 约束备份
hardware/notes/              引脚表、存储器映射、时钟与复位记录
sw/                          CoreMark、UART示例、启动代码与驱动
tools/openocd/               OpenOCD 调试器/目标配置及操作说明
simulation/tb/               与实际 SoC 匹配的 testbench
simulation/firmware/         仿真程序初始化数据
simulation/scripts/          仿真运行脚本
simulation/waves/            仿真波形
output/bringup/              少量迭代的调试软件产物
output/release/              正式测试软件产物
output/release/fpga/         与正式测试固件对应的 FPGA 配置文件
logs/uart/                   串口日志
logs/openocd/                下载/校验/运行日志
logs/screenshots/            操作和报错截图
docs/                       教程、测试记录、来源版本记录

后续放置文件
1. 在 hardware/pds 新建实际 PDS 工程；工程文件由 PDS 创建。
2. 板级 top.v 放 hardware/pds/source；SoC 顶层放其 top 子目录。
3. FDC 放 constraints；按实际器件重新生成的 IP 放 ipcore。
4. PDS 产生的中间结果由工具管理，实际目录名以工具版本为准。
   预留的目录当前为空，不代表已经综合、实现或生成配置文件。
5. 从 sw/README.txt 开始看软件说明，并按 sw/待修改清单.txt 确认板级参数。
   sw 的 build.bat 使用相对路径，移动到本项目后仍保持原有路径关系。
6. 输出文件需要构建后再归档；目前未生成可用于目标板的正式固件。

IP 数量与名称只是参考框架；是否需要 PLL、两块RAM及其具体用途，以最终 SoC 为准。
PGL50H/PG2L50H 的完整型号、封装和板卡引脚必须确认后才能完成硬件工程。
