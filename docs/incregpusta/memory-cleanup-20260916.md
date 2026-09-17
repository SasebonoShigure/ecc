# Stage 10 后诊断内存清理

日期：2026-09-16。状态：内存修改、完整功能回归与实测完成；既有质量检查问题见下文。

Stage 10 基线：ecc `df6d49a`、ecc-tools `6921b608`。本轮内存清理于 2026-09-17 提交，未 push。

## 修改

- 来源隔离用分块 SHA-256 与文件身份取代完整输入字节及 hex，保留前后与原始输入核对。
- Stage 5/6 移除同源 published 副本；保留唯一 observations、transaction 证明、独立 fresh 比较。
- 诊断 JSON 直接写流，来源规范化不深拷贝；跨 prefix 释放完成比较的对象。
- SHA-256 复用已有压缩实现，内存输入不再复制整份 padding，文件输入使用固定缓冲。生产身份值、默认 OFF 和必要检查不变。

Stage 4 涉及来源的 probe 格式升为 v2；Stage 5 process v2、Stage 6 process v3 使用 transaction_receipt。OFF 性能格式、公开 STA 模式接口及生产身份值不变。

## 内存实测

同一输入、构建模式和命令，50 ms 采样进程树峰值 RSS；下表单位 GiB。不同入口不能互相比作同一工作负载。

| 入口 | 修改前 | 修改后 |
|---|---:|---:|
| xtea CPU ON 完整两批 controller | 5.07 | 1.39 |
| xtea / usb / zipdiv CUDA ON 原生两批 probe | 1.36 / 2.68 / 4.82 | 1.20 / 1.79 / 2.87 |
| xtea / usb / zipdiv 单份 JSON 读取与形状检查 | 1.50 / 3.89 / 5.66 | 0.14 / 1.31 / 2.21 |
| xtea / zipdiv 两批 JSON I/O 与对象生命周期隔离测量 | 4.33 / 13.33 | 0.31 / 4.70 |

xtea 首批 targeted JSON 从 791,336,886 降至 26,283,225 字节。默认 OFF 单进程仍约 1.1–1.23 GiB，工艺库和 STA 初始化成本保留。完整 zipdiv CUDA 诊断 controller 仍约 7.32 GiB；同时装载独立结果的公开验收汇总峰值为 12.30 GiB。不能用原生 probe 的 2.87 GiB 代表完整验收。

服务器总内存还包含并行诊断和文件缓存；本轮全部测试退出后，项目 cgroup 仍约 42.3 GB，其中 file cache 约 42.2 GB、anon=0。不能把总内存全部归因于单个小设计的生产堆，也不据此宣称所有入口不存在泄漏。

## 验收

使用原 GCC 14.3、CUDA 12.8、依赖与独立 Release OFF/ON；隔离保存 binding。服务器任务共用 512 GB 硬上限、swap=0。输入仍为原 xtea、usb、zipdiv ICS55 post-synthesis、无 SPEF，以及原 Q/D frozen traces。

原始命令、输出、内存样本和检查结果：
`ecc-tools/build-incregpusta-memory-cleanup-20260916-160221/`，服务器同相对路径。清理前证据在 `build-incregpusta-memory-20260916/`。15 个功能测试组全部通过。小型证据包取回至该目录的 server-evidence/；完整诊断 JSON 和采样文件保留服务器，摘要见 evidence-inventory.json。


- 最终完整 native CTest：OFF 152 项通过、28 项按诊断配置禁用；ON 188 项通过。受影响 native targets 使用原有严格警告设置构建成功。
- Python parent 回归：OFF/ON 各 368 项通过；隔离 binding 的实际路径、CUDA/debug 状态及无设备拒绝通过。
- 三设计四模式 OFF/ON 的 24 个 baseline 组合各重复两次，一致；未编辑 incremental 仍仅记 baseline_only。
- 三个设计 CPU/CUDA 的 Q/D 多批次、实际恢复及继续提交通过；126 项公开/完整值比较（其中 72 项独立 fresh QOR/path 比较）和 14 项 full/mixed OFF/ON 回放一致。
- 性能审计 24 个组合通过：OFF 仅目标预热和采样，无 oracle/完整 receipt；ON 在采样前拒绝。12 组 memcheck/initcheck 零错误；预期设备错误和输出覆盖拒绝单列记录。

质量检查：修改文件 Ruff lint 通过；Pyright 修改文件为 58 个错误（修改前 68 个，无新增诊断），全仓仍为 836 个错误、6 个警告。format 检查仍报告原有的 5 个文件，未批量格式化。独立代码复审通过。

早期测量脚本有导入路径错误；部分任务因容器子 cgroup 的 swap 属性检查未通过而在启动前拒绝。修正路径、显式重设本任务子 cgroup 后复跑通过，原日志保留；共享 512 GB / swap=0 限制核验始终有效。剖析初次汇总的非零状态不覆盖成功重试，17 组对照使用各自实际成功记录。
