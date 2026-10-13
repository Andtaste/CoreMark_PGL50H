# 流水线测试目录

以下目录对应清单编号；当前仅建立结构，测试实现和执行仍待完成。

| 目录 | 用途 |
|---|---|
| [hazards](hazards/) | PIPE-01..04：ALU、load-use、分支操作数与 JALR 数据相关。 |
| [muldiv](muldiv/) | PIPE-05：多周期运算停顿及结果依赖。 |
| [control_flow](control_flow/) | PIPE-06：冲刷和错误路径副作用检查。 |

来源文件保留在 [references/tinyriscv](../../../references/tinyriscv/)，
适配后的用例放在本目录。完整验收条件见 [测试清单](../../../docs/CPU功能仿真测试清单.md)。
