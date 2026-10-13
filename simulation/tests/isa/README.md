# 指令集测试目录

以下目录对应清单编号；当前仅建立结构，测试实现和执行仍待完成。

| 目录 | 用途 |
|---|---|
| [smoke](smoke/) | ISA-01：启动与 PASS/FAIL/TIMEOUT 冒烟测试。 |
| [rv32i](rv32i/) | ISA-02..10、13、14、16、17、19：基础整数指令及异常相关用例。 |
| [rv32m](rv32m/) | ISA-11..12：乘除法扩展指令用例。 |
| [zicsr](zicsr/) | ISA-15：六种 CSR 指令形式。 |
| [zifencei](zifencei/) | ISA-18：FENCE.I 独立扩展用例。 |

来源文件保留在 [references/tinyriscv](../../../references/tinyriscv/)，
适配后的用例放在本目录。完整验收条件见 [测试清单](../../../docs/CPU功能仿真测试清单.md)。
