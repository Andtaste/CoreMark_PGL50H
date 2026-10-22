# 2026-10-21：采用 new_core 单发 BTB64 基线

用户明确要求用 `new_core` 的 89.638 MHz 单发版本覆盖 `CoreMark_PGL50H` 的 `test` 工作区。
源版本采纳时间为 2026-10-20T16:49:03.279211+08:00。迁移前 23 项采纳清单全部匹配。

- 旧 Git HEAD：`5be342b0e36ec2583c65c43b4ac622ec32df61d1`；Git 仓库及分支保留，未提交或推送。
- 旧工作区完整归档：`C:/Users/Lenovo/Desktop/FPGA/tmp/new_core_baseline_import_20261021_151158/previous_worktree`，含本地未提交修改及忽略的构建/仿真文件，`.git` 留在原处。
- 导入正式 RTL、约束、IP、PDS/Tcl、软件/HEX、ISA 夹具、功能测试及其必要参考文件、正式构建脚本和单发验证证据。
- 原 `new_core` 目录及其双发研究、实验中间输出未修改；未把其双发采纳记录当成本工程基线。
- 仅将 RAM1 IDF/包装文件/示例 TB 的初始化路径从源目录改到目标目录的同一 boot.hex。
  已生成的初始化参数、CPU/SoC RTL、PLL 配置、引脚约束和 boot.hex 内容保持逐字节一致。
- `docs/accepted_baseline.json` 保存原始哈希并记录本地路径适配后的哈希。
  原始 STA/功能记录保留在 `docs/ex_id_finish/validation/`，其中路径仍反映原测量目录。
- 清除迁移 PDS 中旧构建结果的缓存引用，将流程状态复位为未运行，保留源文件、IP、约束和实现选项。
- PDS 入口现在为 `hardware/pds/new_core.pds`；旧 `CoreMark_PGL50H.pds` 已随旧工作区归档。
- 原始测量：89.638 MHz STA 估算、IPC 0.778988、6461 LUT / 3520 FF、48 DRM / 4 APM。
  PLL 实际约 75 MHz；没有新跑功能仿真、固件构建、IP 生成、综合、布局布线或上板。

迁移清单及操作前 Git patch：`C:/Users/Lenovo/Desktop/FPGA/tmp/new_core_baseline_import_20261021_151158`。
