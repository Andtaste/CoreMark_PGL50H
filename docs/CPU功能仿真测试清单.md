# CPU 功能仿真测试清单

整理依据：当前 CoreMark_PGL50H RTL，以及仓库内 references/tinyriscv 的测试文件。
本清单不包括自定义周期统计功能。各大类仍需逐项验收，完成勾选暂为空。
当前已加入总线实验的旧 RV32I/M 夹具回归和 ram2 连续访问测试，
范围及结果见 [总线仲裁优化说明](总线仲裁优化说明.md)。通过夹具不代表整项覆盖全部完成。

五级分支已加入流水线转发、CSR/异常、中断和可变延迟定向测试，
本分支的协议、资源与执行记录见 [五级流水线改造说明](五级流水线改造说明.md)。

优先级：P0 为架构优化前的基本回归；P1 为扩展正确性和系统交互；P2 为后续提高覆盖率。
“现有”表示已有参考测试文件，仍须适配当前 CPU；“补充”表示需要新增测试用例或激励。

## 1. 现有指令测试

| 完成 | 编号 | 优先级 | 测试内容 | 验收重点 | 参考文件（相对 R1 或 R2） |
|---|---|---|---|---|---|
| [ ] | ISA-01 | P0 | 启动和测试结束 | 从复位入口执行；明确 PASS/FAIL/TIMEOUT；simple 仅是冒烟测试 | R1: rv32ui/simple.S |
| [ ] | ISA-02 | P0 | ADD、ADDI、SUB | 零、负数、边界值、32 位回绕 | R1: rv32ui/add.S、addi.S、sub.S |
| [ ] | ISA-03 | P0 | AND/OR/XOR 及立即数形式 | 位运算结果、立即数符号扩展 | R1: rv32ui/and.S、andi.S、or.S、ori.S、xor.S、xori.S |
| [ ] | ISA-04 | P0 | SLL/SRL/SRA 及立即数形式 | 移位量 0/31；寄存器移位量只取低 5 位；算术右移符号填充 | R1: rv32ui/sll.S、slli.S、srl.S、srli.S、sra.S、srai.S |
| [ ] | ISA-05 | P0 | SLT/SLTU/SLTI/SLTIU | 有符号/无符号边界与立即数语义 | R1: rv32ui/slt.S、sltu.S、slti.S、sltiu.S |
| [ ] | ISA-06 | P0 | LUI、AUIPC | 高 20 位、当前 PC 加立即数 | R1: rv32ui/lui.S、auipc.S |
| [ ] | ISA-07 | P0 | BEQ/BNE/BLT/BGE/BLTU/BGEU | 跳转/不跳转、有符号/无符号、前向/后向目标 | R1: rv32ui/beq.S、bne.S、blt.S、bge.S、bltu.S、bgeu.S |
| [ ] | ISA-08 | P0 | JAL、JALR | 目标地址、链接值 PC+4、JALR 清除目标最低位 | R1: rv32ui/jal.S、jalr.S |
| [ ] | ISA-09 | P0 | LB/LBU/LH/LHU/LW | 所有合法字节位置、符号/零扩展、地址计算 | R1: rv32ui/lb.S、lbu.S、lh.S、lhu.S、lw.S |
| [ ] | ISA-10 | P0 | SB/SH/SW | 字节写掩码、邻近字节不被改变 | R1: rv32ui/sb.S、sh.S、sw.S |
| [ ] | ISA-11 | P0 | MUL/MULH/MULHSU/MULHU | 低/高 32 位、符号组合与极值 | R1: rv32um/mul.S、mulh.S、mulhsu.S、mulhu.S；R2: rv32im/src/MUL*.S |
| [ ] | ISA-12 | P0 | DIV/DIVU/REM/REMU | 正负数、余数、除零、有符号溢出、结果依赖 | R1: rv32um/div.S、divu.S、rem.S、remu.S；R2: rv32im/src/DIV*.S、REM*.S |
| [ ] | ISA-13 | P0 | 寄存器堆 | x0 固定为 0；x1..x31 可用且宽度 32 位 | R2: rv32i/src/I-RF_x0-01.S、I-RF_size-01.S、I-RF_width-01.S |
| [ ] | ISA-14 | P0 | 端序和 NOP | 小端字节布局、NOP 无架构副作用 | R2: rv32i/src/I-ENDIANESS-01.S、I-NOP-01.S |
| [ ] | ISA-15 | P1 | CSRRW/CSRRS/CSRRC 及立即数形式 | 读旧值、写新值、置位/清位；rs1=x0 或 zimm=0 不应产生写副作用 | R2: rv32Zicsr/src/I-CSRRW-01.S、I-CSRRS-01.S、I-CSRRC-01.S、I-CSRRWI-01.S、I-CSRRSI-01.S、I-CSRRCI-01.S |
| [ ] | ISA-16 | P1 | ECALL、EBREAK | mepc/mcause/mtvec 与陷阱跳转 | R2: rv32i/src/I-ECALL-01.S、I-EBREAK-01.S |
| [ ] | ISA-17 | P1 | 非对齐跳转和 load/store | 按实现声明验证陷阱；区分 load 与 store 异常原因；不得产生非法副作用 | R2: rv32i/src/I-MISALIGN_JMP-01.S、I-MISALIGN_LDST-01.S |
| [ ] | ISA-18 | P1 | FENCE.I | 修改指令存储器后同步取指；需要将 Zifencei 作为单独扩展评估 | R1: rv32ui/fence_i.S；R2: rv32Zifencei/src/I-FENCE.I-01.S |
| [ ] | ISA-19 | P1 | 无延迟槽语义 | taken 分支后顺序指令不得执行 | R2: rv32i/src/I-DELAY_SLOTS-01.S |

R1: [tests/isa](../references/tinyriscv/tests/isa)

R2: [riscv-test-suite](../references/tinyriscv/tests/riscv-compliance/riscv-test-suite)

R2 下每个扩展的 references 目录有同名 `.reference_output`。
例如 [I-ADD-01.reference_output](../references/tinyriscv/tests/riscv-compliance/riscv-test-suite/rv32i/references/I-ADD-01.reference_output)。
已有 ELF/BIN 分别位于 `tests/isa/generated` 和 `tests/riscv-compliance/build_generated`。
R1 下虽存在 ld.S/lwu.S/sd.S 等文件，当前 RV32 CPU 不应把这些 RV64 指令列为通过目标。
CSR/异常测试的启动和参考环境需核对；文件存在不意味着当前核已支持完整特权规范。

## 2. 建议补充的流水线和总线测试

| 完成 | 编号 | 优先级 | 测试内容 | 激励/验收重点 | 参考 |
|---|---|---|---|---|---|
| [ ] | PIPE-01 | P0 | ALU 数据相关 | 生产者/消费者相隔 0、1、2 条指令；rs1、rs2、两者同时依赖；连续覆盖同一 rd | R1 add.S 已有 TEST_RR_*_BYPASS，参考 test_macros.h 扩展 |
| [ ] | PIPE-02 | P0 | Load-use | lw→add、lw→branch、lw→store 地址/数据；相隔 0、1、2 条指令 | R1 lw.S 已有 TEST_LD_DEST_BYPASS、TEST_LD_SRC1_BYPASS |
| [ ] | PIPE-03 | P0 | 分支操作数依赖 | ALU/load 刚生成结果，下一条分支立即比较；结果决定跳转/不跳转 | R1 beq.S、bne.S；扩展当前流水线用例 |
| [ ] | PIPE-04 | P0 | JAL/JALR 依赖 | 新生成跳转目标立即 JALR；返回地址立即被使用；rd=rs1 | R1 jal.S、jalr.S |
| [ ] | PIPE-05 | P0 | 乘除法停顿与结果使用 | mul/div→ALU/store/branch；连续两条乘法/除法；不得重复提交结果 | R1 rv32um 用例；补组合程序 |
| [ ] | PIPE-06 | P0 | 冲刷副作用 | taken branch/JAL 后安排寄存器写、store、CSR 写；检查错误路径没有生效 | R2 I-DELAY_SLOTS-01.S；补 store/CSR 检查 |
| [ ] | BUS-01 | P0 | 连续数据访存 | store→load 同地址、不同地址、字节交叉写；load/store 交替 | R1 lw.S/sw.S/sb.S/sh.S；补连续压力 |
| [ ] | BUS-02 | P0 | 指令和数据访问程序 RAM | load 程序区常量、写可写程序区、访问后恢复取指；PC 不重复/漏指令 | 当前 ifu.v、local_ram_bus.v；补测试 |
| [ ] | BUS-03 | P1 | 请求背压 | 在实际握手约束内延迟 ready；请求字段稳定、只接受一次 | 当前 ifu.v、tinyriscv_core.v、local_ram_bus.v；memory/bus 模型 |
| [ ] | BUS-04 | P1 | 响应延迟 | 请求接受后延迟响应，测试固定延迟与可重复随机延迟；无误写回/死锁 | 同上；新增模型。若设计只支持固定延迟，应明确记录限制 |
| [ ] | SYS-01 | P1 | 复位 | 正常执行、访存等待、除法过程中复位；重新从复位地址启动 | 当前 rst_ctrl.v、ifu.v、divider.v；新增 TB 激励 |
| [ ] | SYS-02 | P1 | timer 中断与 MRET | 中断使能/关闭、mepc 保存、mstatus 恢复、返回继续执行 | R3 timer_int/main.c；当前 clint.v；补自检查 |
| [ ] | SYS-03 | P1 | 非法指令/CSR 访问 | 根据声明的 ISA/特权能力检查异常行为，发现未实现功能须标记 | 当前 idu.v/csr_reg.v；新增程序 |
| [ ] | SYS-04 | P1 | 架构 cycle 计数器 | 单调递增、cycle/cycleh 边界、CSR 读取语义；不包含本次自定义统计 CSR | 当前 csr_reg.v；新增 TB/程序 |

R1 示例：[add.S](../references/tinyriscv/tests/isa/rv32ui/add.S)、
[lw.S](../references/tinyriscv/tests/isa/rv32ui/lw.S)、
[test_macros.h](../references/tinyriscv/tests/isa/test_macros.h)。

R3: [tests/example](../references/tinyriscv/tests/example)。

## 3. 程序、外设与进阶验证

| 完成 | 编号 | 优先级 | 测试 | 参考及要求 |
|---|---|---|---|---|
| [ ] | APP-01 | P1 | 少量迭代 CoreMark CRC | 当前 sw/coremark；短仿真验证计算/周期，不作为正式性能成绩 |
| [ ] | APP-02 | P1 | UART TX/RX | R3 uart_tx/main.c、uart_rx/main.c；TB 解码/发送帧并自检查结果 |
| [ ] | APP-03 | P1 | Timer/GPIO 寄存器 | R3 timer_int/main.c、gpio/main.c；检查中断和 I/O 数值，例程本身不等于自检查测试 |
| [ ] | APP-04 | P2 | JTAG 基础调试 | 普通 TB 的 TEST_JTAG 分支可参考；原测试范围有限，需适配当前 debug 模块 |
| [ ] | ADV-01 | P2 | 随机短指令序列 | 与匹配 ISA 的参考模型比较寄存器/内存，保存 seed；只靠自检查程序不足以覆盖全部错误 |
| [ ] | ADV-02 | P2 | 逐指令差分验证 | 建立可靠退休跟踪，比较 PC、指令、寄存器写回和内存行为；不能把写寄存器次数当退休次数 |
| [ ] | ADV-03 | P2 | 协议断言/形式检查 | 请求保持、单次完成、冲刷无副作用、x0 不变；定义设计的环境约束后进行 |

当前 SoC 没有连接 SPI 外设，不优先移植 spi_master 测试。
F/A/C 扩展、S 模式、MMU、Linux 不作为当前核已声明支持的必过项目。

## 4. 可复用的运行框架文件

| 参考文件 | 用途 | 必须适配的点 |
|---|---|---|
| [普通 testbench](../references/tinyriscv/tb/tinyriscv_soc_tb.v) | 时钟、复位、装载、PASS/FAIL、失败编号、波形 | 当前 rst_n、模块层次、RAM 模型；固定结束超时 |
| [签名 testbench](../references/tinyriscv/tb/compliance_test/tinyriscv_soc_tb.v) | 读取结束标记、导出 signature | 原 TB 从 ROM 数组读签名；必须核对测试签名的真实地址和存储区域 |
| [compile_rtl.py](../references/tinyriscv/sim/compile_rtl.py) | Icarus 编译 | 原文件列表属于旧 CPU；换成当前 RTL；明确 top；检查退出码 |
| [sim_new_nowave.py](../references/tinyriscv/sim/sim_new_nowave.py) | BIN 转换和单项运行 | 编译失败立即停止；超时终止子进程；不使用残留 out.vvp |
| [test_all_isa.py](../references/tinyriscv/sim/test_all_isa.py) | 批量 ISA 回归 | 0 测试不得报通过；逐项日志/退出码；汇总失败与跳过项 |
| [compliance_test.py](../references/tinyriscv/sim/compliance_test/compliance_test.py) | reference_output 比对 | 稳健的超时/错误处理、隔离输出文件；规范化文本而不是只按文件字节大小比较 |
| [BinToMem_CLI.py](../references/tinyriscv/tools/BinToMem_CLI.py) | 小端 BIN 转字级 HEX | 原工具忽略末尾不足 4 字节的数据；应补零并校验容量 |

所有测试必须在当前 CPU RTL 上执行。仅在参考目录旧 CPU 上跑过，不算当前 CPU 的验证。
仿真 RAM 要保持同步读延迟、字节写使能、读写冲突语义。旧组合读 ROM 不能直接代表当前 PDS RAM。
测试 ELF/BIN 的复位入口、链接布局和结束协议需核对；必要时重新编译，不能只复制二进制。
每个用例记录 PASS/FAIL/TIMEOUT/UNSUPPORTED，附失败编号、日志及必要波形。

推荐顺序：环境冒烟 → RV32I/M 基本回归 → 依赖/冲刷/连续访存 → CSR/异常/等待激励 → CoreMark CRC → 随机与差分。

## 5. 当前工程测试目录

使用项目原有 [simulation/](../simulation/)，结构说明见 [README](../simulation/README.md)。
40 个测试编号与目录的对应关系见 [test_plan.json](../simulation/configs/test_plan.json)。
部分回归环境已实现，入口为 [run_bus_regression.py](../simulation/scripts/run/run_bus_regression.py)。
JSON 记录大类计划，具体覆盖情况以总线优化说明和运行报告为准。
