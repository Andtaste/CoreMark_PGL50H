"""Write release notes from verified comparison-fix release metadata."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=ROOT/'hardware/pds';r=json.loads((p/'release_result.json').read_text());m=json.loads((p/'main_manifest.json').read_text())
 assert 'correctness_fix' in m
 f=r['estimated_fmax_mhz'];w=r['corners']['Setup Summary(Slow Corner)']['worst_slack_ns'];ps=m['place_seed'];rs=m['route_seed'];fanout=m['fanout_guide']
 note=f'''# 当前主工程：83 MHz，比较指令正确性修复（2026-10-23）

入口仍为 **[hardware/pds/new_core.pds](hardware/pds/new_core.pds)**，或双击 `open_main.cmd`。新下载文件为 **[output/board83/top.sbit](output/board83/top.sbit)**，与主工程 `download/top.sbit` 相同。83MHz、5000次、o3_inline80固件未变；布局/布线种子为{ps}/{rs}，fanout{fanout}。请重新下载新文件。

已修复ADS综合后部分无符号ALU/分支比较在最高位不同时误用有符号结果的问题：显式区分最高位的符号语义。旧网表能重现板测的360.567664和IPC unavailable；新网表使用原固件报告机器码及同一计数器值重放，输出 **Iterations/Sec 360.941214、IPC 1.105、CPI 0.904**。CoreMark/MHz仍为4.348689。软件统计公式、编译选项没有修改。

63项当前整核/SoC/ISA回归和RTL执行单元等价检查通过；原RTL完整5000次仿真的CRC及计数器与用户板测相符。新网表报告重放通过，83MHz布局布线四角STA通过：Fmax {f:.3f}MHz，最差setup {w:+.3f}ns。网表重放加速了UART/PLL且使用零延迟厂商模型，不能代替新bitstream的实板验证；新文件尚未上板。

旧主工程完整保留于 `hardware/pds_before_compare_fix_20261023`，其旧下载文件存在已复现的比较错误，仅作历史对照。诊断证据见 [diagnosis.json](simulation/results/report_large_20261023/diagnosis.json)，时序和下载哈希见 [release_result.json](hardware/pds/release_result.json)。测试缓存、逐指令轨迹已清理，保留脚本、日志和结果。以下均为修复前历史记录，其入口、哈希和通过结论不代表当前版本。

'''
 readme=ROOT/'README.md';readme.write_text(note+readme.read_text(encoding='utf-8'),encoding='utf-8')
 (p/'README.txt').write_text(f'''new_core 本机主工程：83 MHz / CoreMark5000 / 比较指令修复版
直接打开new_core.pds，或双击根目录open_main.cmd。
PGL50H-6 FBG484 / MES50HP / 50MHz输入。
布局种子{ps}，布线种子{rs}，fanout{fanout}，四角优化和hold修复已保存。
固件o3_inline80，5000次，原ROM保持不变。
下载download/top.sbit，或根目录output/board83/top.sbit。
UART 115200/8N1/无流控，按KEY1启动；PuTTY Terminal可启用Implicit CR in every LF。
预期CRC PASS，Iterations/Sec360.941214，CoreMark/MHz4.348689，IPC1.105，CPI0.904。
原计数器输入下新网表报告重放及63项回归通过；新文件尚未实板验证。
时序Fmax{f:.3f}MHz，最差setup{w:+.3f}ns。
完整重建：tools/run.ps1 -Task pds。必须确认All Constraints Met。
旧主工程保留于hardware/pds_before_compare_fix_20261023；其中旧文件存在比较错误，仅作对照。
SHA256: {r['bitstream_sha256']}
''',encoding='utf-8')
 progress=ROOT/'simulation/results/autonomous_20261022/PROGRESS.md'
 with progress.open('a',encoding='utf-8') as out:out.write('\n\n'+note)
 print('Release documentation updated')
if __name__=='__main__':main()
