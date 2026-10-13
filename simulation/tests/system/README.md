# 系统测试目录

以下目录对应清单编号；当前仅建立结构，测试实现和执行仍待完成。

| 目录 | 用途 |
|---|---|
| [reset](reset/) | SYS-01：执行、访存和除法过程中的复位。 |
| [interrupts](interrupts/) | SYS-02：Timer 中断与 MRET 返回。 |
| [exceptions](exceptions/) | SYS-03：非法指令/CSR 行为与支持范围。 |
| [csr](csr/) | SYS-04：架构 cycle/cycleh，排除自定义统计。 |

来源文件保留在 [references/tinyriscv](../../../references/tinyriscv/)，
适配后的用例放在本目录。完整验收条件见 [测试清单](../../../docs/CPU功能仿真测试清单.md)。
