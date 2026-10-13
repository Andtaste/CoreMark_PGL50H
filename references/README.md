# 参考项目快照

归档日期：2026-10-13。这里保存本机 progject 目录中的参考项目资料，供测试移植、
源码对照与项目交接使用。当前硬件源文件和适配后的测试仍分别放在 hardware/ 和 simulation/。

| 归档目录 | 原目录 | 内容 |
|---|---|---|
| [tinyriscv](tinyriscv) | tinyriscv-master | 原 CPU RTL、测试源码及测试 ELF/BIN、参考结果、TB、仿真脚本、文档和许可证 |
| [pgl22g](pgl22g) | FPGA_Competition-RISC-V_Processor-in-PGL22G-main | 竞赛工程 RTL、IP 描述与实现/模板、约束、PDS/Tcl 工程文件和说明 |

本次保留 851 个参考文件（tinyriscv 787 个，pgl22g 64 个），其中包含 110 个
指令测试 BIN。未归档 .git、工具可执行程序、编译缓存、波形、日志、综合/布局布线结果
与 bitstream。文件列表、大小、SHA-256 和排除列表见 [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json)。

源目录的上游 commit 无法从本地副本确认，不能将此快照当作上游最新版本。
保留源文件原有版权/许可证；tinyriscv 的顶层许可证见 [LICENSE](tinyriscv/LICENSE)。
归档文件按字节复制并检查一致性，归档目录的 .gitattributes 禁止自动行尾转换。

这里的测试运行脚本和 TB 面向旧 CPU，仍需要适配当前模块名称、复位、内存地址及同步 RAM。
测试 ELF/BIN 是参考夹具，不代表已在当前 CPU 上验证通过。
建议在 simulation/ 中建立当前测试环境，引用这里的用例并记录使用版本。

pgl22g/tinydram.fdc 是本机现有文件的快照，已包含此前为 MES50HP 修改的管脚，
不能视为上游 PGL22G 原始引脚约束。PDS、Tcl、IP 文件也可能保留原绝对路径与器件参数，
归档不代表已经能直接打开重建。当前硬件工程的有效 FDC 外部引用尚需另行迁入本工程。

后续引用使用仓库相对路径，例如从 docs/ 文档引用
`../references/tinyriscv/tests/isa/rv32ui/add.S`，避免依赖用户桌面路径。
