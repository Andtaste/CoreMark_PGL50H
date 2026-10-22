# CoreMark5000上板运行

本版本为PGL50H-6 FBG484 / MES50HP，50 MHz板载输入，CPU PLL82 MHz，CoreMark v1.0性能种子，5000次迭代，2000字节总工作区。
CPU/SoC/外设17个RTL文件与采纳版本逐字节一致；修改软件迭代次数、计时频率和报告打印，不增加流水线控制逻辑。
完整5000次RTL仿真已按用户要求停止；正式成绩以用户上板完整UART日志为准。

## 下载与运行

1. 使用FPGA配置JTAG下载器连接板上的配置JTAG接口。PDS的Fabric Configuration / Boundary Scan识别PGL50H后，选用本发布的`output/board5000/top.sbit`，执行SRAM临时配置。
2. 使用数据USB线连接底板UART口，设备管理器确认CP2102对应COM号。不要使用蓝牙COM端口；COM号不是固定COM13。
3. 串口设置115200、8数据位、无校验、1停止位、无流控。可以用PuTTY完整保存日志。
4. 打开串口后按下并释放用户按键KEY1，重启CPU；KEY1是K18、低电平有效。等待完整输出。预计基准计算约16秒，最终以实际周期计时为准。
5. 不要用板上的REST/重加载按键代替KEY1：SRAM临时配置断电后丢失，本版本未烧入Flash。

PowerShell也可在仓库根目录运行（替换COM号）：

```powershell
.\tools\capture_board5000.ps1 -Port COM13
```

脚本不发送串口命令，只接收并保存日志；随后核对5000次、82 MHz计时元数据、运行至少10秒、标准CRC、统计无溢出和双发IPC。启动采集后再按KEY1。
如果使用PuTTY，退出PuTTY释放串口后才能启动脚本。
独立验证已保存日志：

```powershell
python tools/verify_board5000_uart.py path/to/board.uart.txt
```

## 应看到的结果

- `Configured CPU Hz : 82000000`、`Iterations : 5000`。
- `CRC validation : PASS`、`Correct operation validated.`。
- `Total time (secs)`不少于10，`Stats overflow mask : 0x0000`。
- 性能种子CRC：seed=e9f5、list=e714、matrix=1fd7、state=8e3a。
- 输出IPC、CPI、副槽退休数和副槽利用率；双发允许退休数大于周期数。

## 管脚和接口

| 项目 | 配置 |
|---|---|
| 晶振输入 | P20，50 MHz，20 ns输入约束 |
| CPU时钟 | PLL82 MHz；软件计时82 MHz |
| UART TX / RX | R9 / R8；本核只有TX，运行CoreMark无需RX |
| CPU复位 | KEY1，K18，低有效 |
| UART | 115200 / 8N1 / 无流控；分频712 |
| 程序 / 数据存储 | RAM1 64 KiB / RAM2 32 KiB |

CPU调试JTAG引脚不承担FPGA配置下载。LED1在本核中是`tohost==1`完成指示，不能解释成已实现CPU调试暂停。
不要把原始32位`boot.hex`直接填到A64/B32 RAM的初始化设置；使用已经生成的`boot_interleaved.hex`及对应INIT参数。
暂未加入ILA，本下载文件用于先验证CoreMark运行；赛题所需ILA流水线波形证据另行采集。

## 验证边界

已完成新版固件编译、验证种子短跑CRC/独立计数检查、全部16384条32位初始化字的紫光原语读回检查、双口/字节写一致性和实际UART分频检查。
本机当前只检测到蓝牙串口，没有已连接的CP2102；尚未下载或获取物理板上成绩。不要把RTL/时序报告写成板上实测分数。
