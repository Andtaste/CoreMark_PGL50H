# IPC与主频后续优化联合试验

推荐保留隔离候选 `dual_boundary_next_pairbranch` 供用户评估；当前采纳描述符未修改。

以采纳版 `dual_boundary_storewrite` 为共同起点；fqual只叠加本轮mqual，aluwake只叠加本轮capture-only，alulanes进一步将ALU返回资格按槽独立判断，均未混入此前拒绝的改动。各方案分别比较，没有把多个未验证策略合并后归因。

## 同镜像性能、完整时序与资源

| 版本 | fixed10周期 | IPC | IPC变化 | STA估算Fmax MHz | 慢角setup ns | 最差hold ns | LUT | FF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 采纳基线 | 2,704,650 | 1.038308 | +0.000% | 80.535 | +0.083 | +0.019 | 10843 | 4476 |
| 乘法旁路资格提前寄存 | 2,704,650 | 1.038308 | +0.000% | 78.715 | -0.204 | +0.107 | 10791 | 4476 |
| F/F1/M旁路资格提前寄存 | 2,704,650 | 1.038308 | +0.000% | 77.244 | -0.446 | +0.106 | 10718 | 4476 |
| 主槽乘法提前启动 | 2,676,930 | 1.049060 | +1.036% | 74.036 | -1.007 | +0.120 | 11151 | 4477 |
| 主槽load先行、副槽ALU后执行 | 2,704,650 | 1.038308 | +0.000% | 76.173 | -0.628 | -0.098 | 10988 | 4555 |
| 访存主槽＋乘法副槽 | 2,690,530 | 1.043758 | +0.525% | 77.447 | -0.412 | +0.110 | 11101 | 4511 |
| 访存主槽＋分支副槽 | 2,698,740 | 1.040582 | +0.219% | 80.710 | +0.110 | +0.111 | 11040 | 4476 |
| load返回仅捕获到操作数寄存器 | 2,704,650 | 1.038308 | +0.000% | 79.923 | -0.012 | +0.109 | 11084 | 4476 |
| 仅LW同拍返回旁路 | 2,534,333 | 1.108087 | +6.720% | 60.591 | -4.004 | +0.105 | 11215 | 4476 |
| 完整load同拍返回旁路 | 2,408,158 | 1.166145 | +12.312% | 57.614 | -4.857 | +0.106 | 11134 | 4476 |
| 整组ALU返回隔离对照 | 2,660,987 | 1.055346 | +1.641% | 76.400 | -0.589 | +0.109 | 11668 | 4476 |
| 逐槽独立ALU返回隔离 | 2,648,670 | 1.060253 | +2.114% | 77.053 | -0.478 | +0.111 | 11621 | 4476 |

各版均为 **709分布式RAM、48 DRM、4 APM**；没有新增LSU、乘法器或指令FIFO容量。所有候选真实PLL均为80 MHz，约束12.500 ns，选项和器件一致，每版只做一次布局布线，没有扫seed、加false/multicycle path或放宽uncertainty。负setup仍是80 MHz失败，hold违例也单独计为失败。估算Fmax不能代替在另一频率的重新实现/验证；尤其loadsplitv2的hold违例不能靠降频或提频消除。

## 逐拍机会与实际净收益

原版110,515拍副槽单独等待分解为：主槽ALU37,234、load17,840、store1、乘法55,440拍。它们是发生等待的窗口，不是可相加的省拍。主槽普通ALU先算完不等于整组能够推进；本轮分别实现了可独立启动的主槽乘法，以及主槽load先进入原MEM、年轻ALU仍留在EX的分步执行。两者都沿用原tag/lane和原组的顺序提交。

主槽乘法提前版，在基准窗口提前启动14,040次，副槽等待中主槽乘法由55,440降至27,720拍；整核净省27,720拍、IPC提升1.036%。但布线估算74.036 MHz，无法保留80 MHz。

load分步版增加一个待完成副槽所有者、结果寄存和一次性响应保留。主槽先进入有序MEM，副槽算完后才允许原组退休，年轻组不能越过；定向程序确认分步路径确实触发。修正版fixed10周期完全不变，额外状态与MEM保留没有转化为本镜像的净吞吐收益。初版因旧token完成误清新所有者而少退休586条副槽指令，已被完整退休计数检查拒绝；修正版将清除限定到实际有效的旧所有者，重新通过整套回归。失败源码/生成器/日志保留，未混入有效结果。

访存主槽＋乘法副槽：净省14,120拍，IPC提升0.525%，估算77.447 MHz。响应保留命中13,680次，已接受store但尚待乘法的保留命中1,080次；因此扩大准入需要真正处理两种不同完成时刻，不能只放宽类型条件。

访存主槽＋分支副槽：净省5,910拍，IPC提升0.219%，估算80.710 MHz。

分支配对版副槽分支退休54,537→73,916，副槽单独等待110,515→121,530拍，体现扩大配对也会增加成组等待。副槽有效退休率28.95%→29.73%，整核只净省5,910拍，不能把新增配对次数当成同等省拍。该版唯一功能改动为ID扩展准入：判断进入既有ID分配和FIFO pop1/pop2控制，由对应寄存边界捕获；未添加EX/MEM数据旁路或MEM ready反馈。已有跨模块控制路径仍保留。

## load返回与跨模块路径

完整返回旁路把LB/LBU/LH/LHU/LW格式化后的数据直接送到消费者，LW版只送未格式化整字。二者都能提高IPC，但都新增RAM输出到操作数选择、EX地址/分支运算及请求/恢复控制的组合通路。LW省去格式化并没有消除跨级数据路径。

capture-only版只把返回值在现有操作数寄存器边沿捕获，当前拍EX可用性与选择不使用返回数据；它保持原IPC和周期，作为“寄存旁路”的时序对照。

ALU隔离版增加独立ALU输入端口，返回数据只参与ALU结果，AGU、分支比较、跳转目标和CSR仍使用原来的寄存来源。局部SAT证明：任意新增ALU数据不会改变EX的ready/valid、分支决定、地址、异常、store数据或辅助字段；新增ALU口接回原操作数时与采纳版组合EX完全相同（证明配置关闭除法，完整含除法CPU另由回归验证）。整组ALU对照IPC为1.055346、提升1.641%；进一步去掉“伴随指令也必须是ALU”的非必要限制，逐槽独立开放ALU返回后IPC为1.060253、提升2.114%。后一版EX字节完全相同，明确按哈希复用局部SAT证据，独立重跑本版操作数模型、整核回归和真实SoC。

两版都避免了完整返回版同拍返回数据进入AGU/分支计算的设计连接，但返回有效资格到执行/请求控制的路径仍存在，不能称为消除了所有长控制链。它们与完整返回版的差距还包含成组供给和等待时序的变化，不能直接将IPC差值归属为某一种load→分支或load→load的独立收益。

逐槽ALU版最终全局最差转到`soc/cpu/destination1[0][3]/opit_0_inv_L5Q_perm/CLK`→`soc/cpu/operands/vb[0][23]/opit_0_L5Q_perm/L4`，11级，逻辑3.698 ns、布线8.955 ns。因此，即使所查RAM B口到控制端的路径被隔开，也不能据此宣布整核80 MHz通过。

输入信用始终来自寄存队列占用，没有新增MEM ready到EX输入信用的组合反馈。所有候选的完整最差路径如下；沿途最大扇出不能代替源寄存器总扇出，也不能把布线增加全归因于扇出。

| 版本 | 全局最差起点→终点 | 级数 | 逻辑/布线 ns | 路径最大数据扇出 |
|---|---|---:|---:|---:|
| mqual | `soc/cpu/f1_valid/opit_0_inv_L5Q_perm/CLK → soc/bus/ram_data/U_ipml_dpram_ram2_tdp/ADDR_LOOP[1].DATA_LOOP[2].U_GTP_DRM18K/iGopDrm_inv/CEB[0]` | 11 | 3.698/8.747 | 35 |
| fqual | `soc/cpu/operands/wb[0]/opit_0_L5Q_perm/CLK → soc/bus/ram_data/U_ipml_dpram_ram2_tdp/ADDR_LOOP[3].DATA_LOOP[1].U_GTP_DRM18K/iGopDrm_inv/CEB[0]` | 13 | 3.784/8.903 | 69 |
| mpre | `soc/cpu/f1_valid/opit_0_inv_L5Q_perm/CLK → soc/bus/ram_code/U_ipml_dpram_ram1_tdp/ADDR_LOOP[4].DATA_LOOP[1].U_GTP_DRM18K/iGopDrm_inv/CEB[0]` | 11 | 3.456/9.810 | 38 |
| loadsplitv2 | `soc/cpu/operands/sf_a[0]/opit_0_A2Q1/CLK → soc/bus/ram_code/U_ipml_dpram_ram1_tdp/ADDR_LOOP[6].DATA_LOOP[1].U_GTP_DRM18K/iGopDrm_inv/CEB[0]` | 11 | 4.462/8.407 | 41 |
| pairmul | `soc/cpu/multiply/forward_valid/opit_0_inv_L5Q_perm/CLK → soc/cpu/f1_data[21]/opit_0_L5Q_perm/L1` | 9 | 3.162/9.316 | 31 |
| pairbranch | `soc/cpu/wb_q[12]/opit_0/CLK → soc/bus/ram_code/U_ipml_dpram_ram1_tdp/ADDR_LOOP[1].DATA_LOOP[1].U_GTP_DRM18K/iGopDrm_inv/CEB[0]` | 12 | 3.996/8.153 | 140 |
| loadcapture | `soc/cpu/multiply/forward_valid/opit_0_inv_L5Q_perm/CLK → soc/cpu/memory/held_side[2]/opit_0_L5Q_perm/L2` | 14 | 4.639/7.281 | 63 |
| wordwake | `soc/bus/ram_data/U_ipml_dpram_ram2_tdp/ADDR_LOOP[2].DATA_LOOP[0].U_GTP_DRM18K/iGopDrm_inv/CLKB[0] → soc/bus/ram_code/U_ipml_dpram_ram1_tdp/ADDR_LOOP[0].DATA_LOOP[2].U_GTP_DRM18K/iGopDrm_inv/CEB[0]` | 13 | 5.721/10.585 | 35 |
| loadwake | `soc/bus/ram_code/U_ipml_dpram_ram1_tdp/ADDR_LOOP[6].DATA_LOOP[1].U_GTP_DRM18K/iGopDrm_inv/CLKB[0] → soc/bus/ram_data/U_ipml_dpram_ram2_tdp/ADDR_LOOP[2].DATA_LOOP[0].U_GTP_DRM18K/iGopDrm_inv/CEB[0]` | 15 | 7.061/10.037 | 18 |
| aluwake | `soc/bus/ram_code/U_ipml_dpram_ram1_tdp/ADDR_LOOP[7].DATA_LOOP[1].U_GTP_DRM18K/iGopDrm_inv/CLKB[0] → soc/cpu/memory_queue/data_196/ram16x1d/WD` | 9 | 5.799/7.247 | 30 |
| alulanes | `soc/cpu/destination1[0][3]/opit_0_inv_L5Q_perm/CLK → soc/cpu/operands/vb[0][23]/opit_0_L5Q_perm/L4` | 11 | 3.698/8.955 | 33 |

定向查询另外覆盖IF/操作数寄存边界、操作数到控制端，以及RAM B口到redirect/F/F1有效位/RAM使能。后者为空只表示指定物理端点集合没有报告匹配路径，不替代全核形式证明。

| 查询版本 | IF/操作数边界最差setup ns | 操作数→控制最差setup ns | RAM B口→所查控制端 |
|---|---:|---:|---|
| storewrite | +0.154 | +0.083 | 无匹配路径 |
| next_pairbranch | +0.169 | +0.126 | 无匹配路径 |
| next_aluwake | -0.257 | -0.279 | 无匹配路径 |
| next_wordwake | -2.404 | -3.054 | -4.004 ns / 13级 |
| next_alulanes | -0.478 | -0.298 | 无匹配路径 |

旁路资格试验减少了一些映射逻辑，但M-only及F/F1/M版的全局路径仍落在既有等待/来源选择到请求使能的网络上；局部删门没有形成整核提频。

## 双发有效利用率

“主/副槽利用率”以下均为退休条数除以同一统计窗口周期，不与含投机的发射组数混用。

| 版本 | 主槽有效退休/周期 | 副槽有效退休/周期 | 发射双发组/全部组 |
|---|---:|---:|---:|
| 采纳版 | 74.88% | 28.95% | 39.49% |
| mqual | 74.88% | 28.95% | 39.49% |
| fqual | 74.88% | 28.95% | 39.49% |
| mpre | 75.66% | 29.25% | 39.49% |
| loadsplitv2 | 74.88% | 28.95% | 39.49% |
| pairmul | 74.82% | 29.56% | 40.31% |
| pairbranch | 74.33% | 29.73% | 40.79% |
| loadcapture | 74.88% | 28.95% | 39.49% |
| wordwake | 79.98% | 30.83% | 39.36% |
| loadwake | 84.53% | 32.08% | 38.77% |
| aluwake | 76.22% | 29.32% | 39.27% |
| alulanes | 76.57% | 29.45% | 39.27% |

## 验证范围和取舍

每个有效候选均通过fixed1/fixed10 CRC、相同架构退休总数、63项整核/随机/ISA、6项配对、4项取消、4项lint/结构/准入审计、8项未来tag、4项乘法tag、6项真实posted-enabled SoC契约、4项逐拍load及真实top UART80帧检查。

M资格、F/F1/M资格、capture-only、LW返回、完整返回和独立ALU返回另各运行300,000拍操作数模型；前两者使用真实下一拍valid契约，capture-only使用返回值下一拍成为相同WB值的契约，独立ALU版本比较其有效独立ALU数据口。没有将局部模型称为整核形式证明。

扩展配对、主槽提前乘法、load分步版还运行新增访存配对/分步与精确异常定向程序，在带随机响应延迟的core及真实SoC上检查，覆盖主槽load/store故障时副槽不得退休和故障前的预测重定向。新增响应保留模块对POST_LOCAL_STORES=0/1分别检查128组load、随机等待与token重用、错误保留、取消；配对乘法另各覆盖32组store，已有8项posted-store模块测试也重新运行。

所有有效RTL/IP生成器精确重建，编译输入哈希与采纳版描述符/源文件/IP/证据核验。Verilator对LW性能编译曾出现一次内部错误，保留失败日志，原源码不变重跑通过；还有模块证明输入缺少divider依赖及适配器结果目录名称的问题，修正工具后通过，未修改CPU去绕过断言。

ALU返回版逐拍测试原先沿用“所有消费者均在WB下一拍执行”的旧预期，保留失败记录后，按“ALU返回当拍、LSU下一拍”的精确契约重新检查已经运行的真实SoC波形；未放宽为任意等待，也未修改RTL。

软件镜像仍打印75 MHz，旧软件把IPC>1提示为不可用；本报告使用独立退休/周期窗口。短CoreMark仅作诊断，不是正式成绩；本轮没有上板，没有验证游戏负载。

本轮新增的可重建obj/VVP/PDS compile/STA查询DB缓存已清理，共1,558文件、4,310,345,558字节（约4.014 GiB）。RTL/IP、镜像、日志、trace、STA、映射资源报告及压缩路由快照保留，采纳版描述符哈希未变。

建议保留上述推荐候选供进一步评估。

完整机器数据见[comparison.json](dual_next_trials/comparison.json)，归档哈希见[manifest.json](dual_next_trials/manifest.json)。
