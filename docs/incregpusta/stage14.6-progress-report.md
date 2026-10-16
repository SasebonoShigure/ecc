# Stage 14.6 实施记录

日期：2026-10-16。基线为 ECC 8f427ef、ecc-tools 79e3106df。状态：实施中。首批已提交推送（ECC d6b7ee4、ecc-tools 1d13fe226）；本次按用户要求提交第二批回传与等待计量改动，不代表阶段完成。

## 首批改动

- timing-only CPU 基线调用 propagateRequired()，保留 RAT/slack，不提前生成完整报告分组；默认一次性完整产物流程不变。
- 完整报告测试和 native 事务测试在实际消费处显式调用 analyzePropagatedTiming()。验证基线未提前生成路径组、报告前后完整 timing 相等、报告包含实际路径，以及回滚恢复已准备的报告。
- 独立设计与代码审查完成。复核撤回了一个 prefix0 回归判断：公开 oracle CLI 原本拒绝零前缀，本次不扩展该协议。

## 首批最终验证

| 检查 | 结果 |
|---|---|
| 原版报告回归 | 通过 |
| Release / CUDA ON / debug OFF 构建 | 通过 |
| OFF 报告、native 事务、编辑与 lifecycle 回归 | 31/31 通过，无跳过 |
| Release / CUDA ON / debug ON | 配置、构建及相关回归通过 |
| Release / 无 CUDA | 配置、构建及相关回归通过 |
| 两仓库 diff 检查 | 通过 |
| 新性能测量、完整阶段回归及 sanitizer | 未执行，不作通过结论 |

运行目录：服务器 /home/qianhan/code/stage14.6-20261016-implementation，本地同名目录位于 /home/shigure/code。基线归档、源码哈希、batch01-source.json 和 checkpoint01-evidence 保存版本与结果；本地最终三个源码文件与服务器受测 source01 哈希一致。driver01.exit=0，batch01-verdict.json 确认全部命令成功；原始日志已取回 checkpoint01-evidence。所有构建共用 512 GB 硬上限、swap=0。

曾启动的 batch02 仅验证后来撤回的 prefix0 扩展，已取消且保存日志；不计作最终改动的验证通过。

## 第二批：回传与等待计量（部分验证完成）

ecc-tools 提交：8da1527fc。

- 分开记录分层决策、level 元数据、必要状态、候选及完整结果的实际 D2H 字节和既有同步点等待。原 d2h_ms 改名 delivery_d2h_ms，仅表示传播后状态及显式查询的设备事件区间。
- Runtime 等待归属于本代计算、查询及针对该代的撤销。close 的同步属于生命周期清理；构造失败前临时候选中的计算等待不保证保留，失败整段成本仍取外层 wall time。主机等待与 kernel/传输区间重叠，不可相加。
- 复用现有同步和事件，只增加常数计数及主机时钟读取；不宣称零开销。分组仅在相应等待成功后完成，错误路径可留未分类字节。
- trace process/verdict 升级 major；samples v2 添加可选 readback 扩展，历史样本不补造缺失计量。
- 独立审查发现撤销等待原会随 cleanup 对象丢弃，已改为归属存活 owner。新增实际放弃、部分 patch 失败、构造分配失败、输入拒绝和重复查询行为测试，OFF 行为回归已通过；ON 构造分配失败分支尚未执行。
- 修改文件类型检查失败：默认导入配置 44 项；在相同显式导入路径下，基线与本轮均为 43 项，没有新增诊断。原始输出及比较在 batch03-type-comparison.json；不将基线同错记为通过。
- Python 8 项通过，包含错误计量拒绝及旧 samples 兼容。首次运行发现 samples schema 未迁移，修复后通过；修改文件 lint 曾报 3 处 E501，修复后通过。未将这些主机测试当作设备验收。
- 冻结源码 source03 与本地 15 个 native 文件哈希一致。Release/OFF 配置和构建通过，10 项 CUDA trace、事务、mixed、fallback、查询及性能编排回归全部通过。任务使用 GPU 1 和共同 512 GB 内存上限、swap=0。
- driver03.exit=1：随后启动 memcheck 时找不到 compute-sanitizer，脚本以 FileNotFoundError 中断；memcheck/initcheck、ON 和无 CUDA 检查均未执行，未生成总 verdict。原始失败及已完成结果已取回 checkpoint03-commit-evidence；本次提交不将部分验证写成完整通过。

## 剩余范围

I 中的 native 绑定与 CSR 导出迁移、J 的 ON／无 CUDA／sanitizer 验收、模式收敛及 A–H 优化均未完成。未取得新加速结果；Stage 13 遗留项、Stage 12/15 正式性能门及既有严格构建、类型和 sanitizer 失败保持原记录。README、用户 CLAUDE 和独立报告不纳入本次提交。
