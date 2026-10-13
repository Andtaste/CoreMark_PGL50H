# 应用与外设测试目录

以下目录对应清单编号；当前仅建立结构，测试实现和执行仍待完成。

| 目录 | 用途 |
|---|---|
| [coremark](coremark/) | APP-01：短运行 CRC 和周期验证。 |
| [uart](uart/) | APP-02：UART TX/RX 自检查。 |
| [timer](timer/) | APP-03：Timer 寄存器与中断。 |
| [gpio](gpio/) | APP-03：GPIO 输入/输出寄存器。 |

来源文件保留在 [references/tinyriscv](../../../references/tinyriscv/)，
适配后的用例放在本目录。完整验收条件见 [测试清单](../../../docs/CPU功能仿真测试清单.md)。
