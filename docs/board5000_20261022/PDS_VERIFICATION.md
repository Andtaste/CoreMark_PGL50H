# 普通PDS工程重新验证

此前冻结布局结果因实际板级引脚约束未生效而撤回。本次使用PDS2022.2-SP1-Lite原生工程流程，从RTL完整重新综合、映射、P&R和Report Timing，不导入旧映射/布局。

| 布局seed | 路由seed | 慢角Setup(ns) | Fmax(MHz) | 结果 |
|---:|---:|---:|---:|---|
| 0 | 1 | -0.228 | 80.496 | FAIL |
| 0 | 4 | -0.331 | 79.834 | FAIL |
| 1 | 1 | -0.195 | 80.710 | FAIL |
| 1 | 2 | -0.199 | 80.684 | FAIL |
| 1 | 4 | -0.096 | 81.360 | FAIL |
| 2 | 1 | -0.812 | 76.882 | FAIL |
| 3 | 1 | +0.008 | 82.055 | PASS |
| 22 | 4 | -0.977 | 75.919 | FAIL |

选定3/1已在独立工程目录从源文件重跑两次，四角结果完全一致。布局3 / 路由1，估算Fmax82.055MHz，慢角setup+0.008ns；布线后11037LUT /4476FF /709分布RAM /48DRM /4APM。

实际P&R引脚均已验证：clk=P20、rst_ext_i=K18、uart_tx_pin=R9、halted_ind=B2、gpio[0]=W11、gpio[1]=V11、jtag_TDO=Y11；CONSTRAINT均为YES，I/O标准与FDC一致。

PDS工程：`hardware/pds/new_core.pds`。已开启多角优化和Hold修复，max_ctrl_chain_length=4。CPU、镜像、PLL和FDC字节不变。没有完成5000次全程仿真，也未上板。

原生运行命令：`pds_shell.exe -project new_core.pds -run report_timing`。生成下载文件的保护入口为仓库根目录下`python tools/build_board5000.py`，同时检查所有有效板级引脚和最终四角时序。

原始时序、P&R报告和构建日志分别保存在本目录native_timing.rtr.gz、native_pnr.prr.gz、native_build.log.gz。下载文件SHA见board_manifest.json。
