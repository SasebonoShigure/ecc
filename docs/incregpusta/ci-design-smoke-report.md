# ECC CI 小设计补测报告

日期：2026-09-09。输入来自 `/home/shigure/code/ecc-ci-designs`，提交 `f6994018cbe3a72b2b743d08222470b80a6820ba`。测试在独立 build 目录进行，源设计及原有 runs 未修改。本次只补测试与报告，未修改算法，未 commit/push。

## 结果

| 设计 | 综合后单元数 | split 后端口数 | CPU/full | CUDA/full |
|---|---:|---:|---|---|
| xtea | 71 | 260 | 通过，ON/OFF 全输出一致 | ON/OFF 均 unsupported |
| usb | 803 | 44 | 通过，ON/OFF 全输出一致 | ON/OFF 均 unsupported |
| zipdiv | 1107 | 107 | 通过，ON/OFF 全输出一致 | ON/OFF 均 unsupported |

三个设计均重新经过 ECC `syn_sta` 流程完成 Yosys 综合和默认 CPU STA。随后使用相同门级网表、SDC 和 Liberty，在 Stage 7–8 的 Release OFF/ON 两套 native binding 上运行。每个 CPU 构建连续调用两次，共 12 次完整 timing 执行；同构建重跑及跨 ON/OFF 的完整导出 QOR、timing paths 对象均一致。这里比较的是公开输出，不是所有内部 timing 数组，也未与外部 OpenSTA 做 signoff 对比。

6 次 CUDA 请求（3 个设计 × ON/OFF）均明确返回 `StaUnsupportedError`：

```
CUDA STA does not support analysis features:
sequential_instance sequential_launch timing_check crpr
clock_tree_fanout conditional_timing_arc
```

这些请求未产生成功的 QOR 文件，未静默 fallback。它们证明当前 capability 拒绝机制生效，**不算 CUDA 功能通过，也没有取得 CPU/CUDA timing 等价结果**。Stage 8 targeted 生产 replayer 依赖受支持的 CUDA baseline，因此本轮未继续执行这三个设计的 targeted 编辑/恢复/性能测试。

## 测试边界

选取 zipdiv、xtea、usb 是为了覆盖小型除法器、加密模块和 USB 逻辑；规模采用本轮综合的实际单元数，不能从 RTL 行数推断。xtea 本轮优化后为 71 个单元，此处如实使用综合结果，不宣称它代表任意实现规模的完整加密核。

PDK 使用仓内 ICS55，H7CR/H7CL 的 `ss_rcworst_1p08_125_nldm.lib` 及对应 LEF，tech LEF 为 `N551P6M_ecos.lef`。时钟/频率沿用每个设计的 ecc.toml；综合产物没有经过布局布线，不带 SPEF，属于 post-synthesis NoParasitic 测试。Yosys 报告版本为 0.62；native 继续使用此前 GCC 14.3 Release/CUDA 构建，未升级依赖。

先前 Stage 7–8 小图验收不能推广为这类含寄存器实际设计的 GPU 支持。要完成它们的 CUDA/full 与 targeted 差分，需要补齐上述顺序逻辑、时钟和条件 arc 语义及相应验收；本轮没有通过移除寄存器、修改约束或关闭必要检查来绕过拒绝。

## 证据和复现

全部原始数据目录：`/home/shigure/code/ecc/chipcompiler/thirdparty/ecc-tools/build-incregpusta-cuda-on/ci-design-tests-20260909`。

- `summary.json`：源仓库提交、门级网表 SHA-256、规模和汇总。
- `<design>/ecc.toml`：仅副本改为 syn_sta，RTL 指向原设计，PDK 指向现有 ICS55。
- `<design>/runs/default/Synthesis_yosys/`：综合脚本、完整日志、mapped netlist 和统计。
- `<design>/mapped.v`：原综合 `.v.gz` 的无修改解压结果。
- `<design>/cpu-off/`、`cpu-on/`：每套构建两轮完整 report/feature 与 result.json。
- `<design>/cuda-off/`、`cuda-on/`：真实拒绝结果；相邻 `.log` 为完整 native 日志。
- `run_native.py`、`run_matrix.py`、`run_cpu_on.py`：本轮实际执行脚本。

在 ecc 根进入既有 bare Nix dev shell后，综合命令为 `.venv/bin/ecc run --project <本轮design目录> --plain`。native 命令为 `.venv/bin/python <证据目录>/run_native.py <design> <cpu|cuda> <off|on>`；通过 `PYTHONPATH=<对应build>/python` 选择实际 binding，CUDA driver 库设置 `LD_LIBRARY_PATH=/usr/lib/wsl/lib`。脚本拒绝覆盖已有输出；复验应使用新的输出目录并保留原证据。
