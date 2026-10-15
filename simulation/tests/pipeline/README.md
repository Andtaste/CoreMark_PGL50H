# 流水线测试目录

以下目录对应清单编号。五级改造已增加跨类别定向程序
[five_stage_hazards.S](five_stage_hazards.S)，覆盖转发、load-use、乘除法、CSR、
异常冲刷、MRET 与定时器中断；各类别更完整的覆盖仍待补充。

运行 `python simulation/scripts/run/run_bus_regression.py --suite pipeline`，
分别在两种 SoC 仲裁模式和独立可变延迟存储模型下执行。

| 目录 | 用途 |
|---|---|
| [hazards](hazards/) | PIPE-01..04：ALU、load-use、分支操作数与 JALR 数据相关。 |
| [muldiv](muldiv/) | PIPE-05：多周期运算停顿及结果依赖。 |
| [control_flow](control_flow/) | PIPE-06：冲刷和错误路径副作用检查。 |

来源文件保留在 [references/tinyriscv](../../../references/tinyriscv/)，
适配后的用例放在本目录。完整验收条件见 [测试清单](../../../docs/CPU功能仿真测试清单.md)。
