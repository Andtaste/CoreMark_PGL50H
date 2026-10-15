# 当前 CPU 仿真目录

在项目已有 simulation/、tb/、scripts/、firmware/、waves/ 基础上完善结构。
已加入总线仲裁回归环境：仲裁单元检查、当前 SoC 的 RV32I/M 夹具回归、
ram2 连续访问和少量迭代 CoreMark CRC 仿真。其他目录仍有待实现的测试。
不包含专门的自定义周期统计功能单元测试。

运行入口为 [run_bus_regression.py](scripts/run/run_bus_regression.py)，
所需工具、协议范围及对比方法见 [总线仲裁优化说明](../docs/总线仲裁优化说明.md)。

```text
simulation/
├─ tb/                 core、soc、unit/{alu,muldiv,regfile,csr,bus}
├─ models/             memory、peripherals
├─ env/                startup、linker、macros
├─ tests/
│  ├─ isa/             smoke、rv32i、rv32m、zicsr、zifencei
│  ├─ pipeline/        hazards、muldiv、control_flow
│  ├─ bus/             memory、backpressure
│  ├─ system/          reset、interrupts、exceptions、csr
│  ├─ apps/            coremark、uart、timer、gpio
│  └─ advanced/        jtag、random、differential、formal
├─ assertions/         core、bus
├─ configs/            test_plan.json：40 个清单编号与目录的映射
├─ scripts/            build、run、compare
├─ firmware/generated/ ELF/BIN/HEX 生成目录
├─ results/            logs、signatures、reports
└─ waves/              已有波形目录
```

[完整测试清单](../docs/CPU功能仿真测试清单.md)定义优先级及验收重点，
[test_plan.json](configs/test_plan.json)保存编号、状态和目录映射，所有状态初始为 planned。
JSON 中的测试目录和 reference_roots 都以 simulation/ 为相对路径基准。
每个测试应记录 PASS/FAIL/TIMEOUT/UNSUPPORTED，不能将空用例集合报成全部通过。

参考源文件在 [references/tinyriscv](../references/tinyriscv/)；编译目标必须是
当前 [CPU RTL](../hardware/pds/source/core/) 和当前总线/外设。
旧目录的 TB、脚本和测试二进制需要核对模块层次、复位、入口和内存布局后再适配。
RAM 模型必须保留同步读、字节写和读写冲突语义。

新增用例源码放 tests/，共享启动/链接/宏放 env/，激励模型放 models/，
总线和核断言放 assertions/。生成固件、日志、签名和波形放对应输出目录并由 Git 忽略，
参考 `.reference_output` 仍在 references/ 中跟踪。

推荐实现顺序：smoke → RV32I/M → 数据相关与冲刷 → CSR/异常和背压 →
CoreMark CRC → 随机与差分。FENCE.I 及异常行为要按实际支持范围选择，
RV64、F/A/C 扩展和完整 S 模式不作为当前核的必过目标。
