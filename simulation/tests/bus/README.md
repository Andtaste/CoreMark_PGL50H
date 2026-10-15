# 总线测试目录

以下目录对应清单编号。memory/ 已加入 ram2_parallel.S，用于当前总线实验；
完整背压/可变延迟支持仍需适配现有协议，尚未实现。

| 目录 | 用途 |
|---|---|
| [memory](memory/) | BUS-01..02：连续访存、程序 RAM 数据访问与取指恢复。 |
| [backpressure](backpressure/) | BUS-03..04：请求背压与响应延迟。 |

来源文件保留在 [references/tinyriscv](../../../references/tinyriscv/)，
适配后的用例放在本目录。完整验收条件见 [测试清单](../../../docs/CPU功能仿真测试清单.md)。
