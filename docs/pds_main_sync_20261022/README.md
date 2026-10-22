# 主 PDS 工程同步

`hardware/pds/new_core.pds` 已同步为当前采纳的 `dual_boundary_next_pairbranch` 双发基线，今后打开此入口。原工程完整保存在 `hardware/pds_before_pairbranch_20261022`，切换前全部文件 SHA 已复核。

主工程重新编译、综合、映射、布局布线和 STA 通过：PLL 80 MHz，估算 Fmax 80.710 MHz；资源 11040 LUT / 4476 FF / 709 分布 RAM / 48 DRM / 4 APM。四角 setup/hold 见 result.json。

全部 17 个 RTL 文件逐字节匹配采纳版；完整综合网表删除注释和空白后 SHA 完全相同，包括紫光 RAM 的原语 INIT 常量。主工程自带 memory/boot.hex 和正确的 A64/B32 编码 boot_interleaved.hex，16384 个 RV32 字逐字核对；仅改 IP 的 INIT_FILE 路径，构建不再依赖 simulation/results 中的源码或镜像。

实际主工程文件列表直接跑 6 项核心/SoC 集成测试通过，没有用独立候选源码覆盖。由于 RTL 和完整综合网表一致，IPC 和旧采纳版 CoreMark 结果按精确等价复用；未重新声称上板或正式 CoreMark 分数。

本次同步未纳入已经拒绝的四种资源改写。采纳描述和冻结试验归档不回写；新的主工程绑定以 docs/active_pds_baseline.json 和 hardware/pds/BASELINE.json 为准。旧单发源码的历史 hardware/pds 路径已迁到 backup，不能用新的主工程文件去校验旧单发哈希。
