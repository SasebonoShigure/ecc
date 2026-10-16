# Stage 14.6 实施记录

日期：2026-10-16。基线为 ECC 8f427ef、ecc-tools 79e3106df。状态：实施中；本次仅提交首批报告推迟改动，不代表阶段完成。

## 首批改动

- timing-only CPU 基线调用 propagateRequired()，保留 RAT/slack，不提前生成完整报告分组；默认一次性完整产物流程不变。
- 完整报告测试和 native 事务测试在实际消费处显式调用 analyzePropagatedTiming()。验证基线未提前生成路径组、报告前后完整 timing 相等、报告包含实际路径，以及回滚恢复已准备的报告。
- 独立设计与代码审查完成。复核撤回了一个 prefix0 回归判断：公开 oracle CLI 原本拒绝零前缀，本次不扩展该协议。

## 提交时验证状态

| 检查 | 结果 |
|---|---|
| 原版报告回归 | 通过 |
| Release / CUDA ON / debug OFF 构建 | 通过 |
| OFF 报告、native 事务、编辑与 lifecycle 回归 | 31/31 通过，无跳过 |
| Release / CUDA ON / debug ON | 配置通过，构建及回归仍在运行 |
| Release / 无 CUDA | 尚未执行，原串行任务后续运行 |
| 两仓库 diff 检查 | 通过 |
| 新性能测量、完整阶段回归及 sanitizer | 未执行，不作通过结论 |

运行目录：服务器 /home/qianhan/code/stage14.6-20261016-implementation，本地同名目录位于 /home/shigure/code。基线归档、源码哈希、batch01-source.json 和 checkpoint01-evidence 保存版本与结果；本地最终三个源码文件与服务器受测 source01 哈希一致。tmux stage146-batch01 继续运行，最终状态以 driver01.exit 和 batch01-verdict.json 为准。所有构建共用 512 GB 硬上限、swap=0。

曾启动的 batch02 仅验证后来撤回的 prefix0 扩展，已取消且保存日志；不计作最终改动的验证通过。

## 剩余范围

I 中的 native 绑定与 CSR 导出迁移、J 计时口径、模式收敛及 A–H 优化均未完成。未取得新加速结果；Stage 13 遗留项、Stage 12/15 正式性能门及既有严格构建、类型和 sanitizer 失败保持原记录。README、用户 CLAUDE 和独立报告不纳入本次提交。
