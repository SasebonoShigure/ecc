# IncreGPUSTA Stage 0–6 冗余清理报告

日期：2026-09-08。起点为 ecc `dfa7142`、ecc-tools `5d0bf7ad7`。本轮保留未提交差异，不 push；用户原有 CLAUDE.md 改动和三份报告不纳入本轮，通用 README 与项目依赖保持原样。

## 改造范围

- 删除仅剩拒绝测试调用的 legacy recovery 链及专属辅助；按模式逐批重建成为唯一恢复路径。完成状态 move 进入恢复结果，诊断 evidence 仅 ON 存一份且不参与授权。
- ExpectedBeforeBinding 保留功能所需 graph/index；resolver/identity 比较副本只在 ON 构造。移除固定复制次数及仅测试消费的字节估计。
- Factory 保留最终一次 ON aggregate proof，删除被其涵盖的分项和 publish 对同一 staged 的重复全检；生成 levels 的完整证明由 full backend / mixed pipeline 各自负责，内部 propagation 复用唯一实现。
- 公开外部输入、levels、注入 replay 和 updater/index 局部适用性检查仍运行。故障 adapter 可在构造后修改 descriptor，因此不增加绕过这些检查的 skip 开关。index 错误改由真正的 updater/index 边界报告；被 aggregate 覆盖的诊断错误归并为 state validation。
- Stage 6 删除同源第二份 receipt 和其 serializer/绑定证明。每批 canonical graph/timing 只有一份，值比较与 level 合法性仍分别执行。Process 为 `ista-stage6-trace-process/2.0.0`，verdict 为 `ista-stage6-differential-verdict/2.0.0`；Stage 5 和 OFF 性能 schema 保持。
- 在最窄测试公共层合并 token/signature/stable reference 的 JSON 编码；Stage 6 复用 Stage 5 子进程 runner。独立 targeted/fresh 计算不共享。
- 删除旧 ON diagnostic timing smoke；现有 Stage 5/6 controller 继续保存完整诊断。OFF smoke 删除三项冗余构建 CLI 参数，唯一信息来源为 native build-info；ON 采样前拒绝，非 Release 维持退出 77。

## 验收

两套已有构建目录使用相同 GCC 14.3.0、依赖、Release `-O3 -DNDEBUG`，分别为 `build-incregpusta-off` 与 `build-ista-stage34`（ON）。相关 native 严格构建通过；修改行已格式化，无文件因本轮修改从 700 行以下跨到 700 行以上。

| 验收 | 最终结果 |
|---|---|
| Native OFF | 140 passed，28 项诊断明确 Disabled / Not Run，0 failed |
| Native ON | 168 passed，0 failed；含独立 fresh differential、故障注入、属性与 canary |
| Parent 非 PDK | 1669 passed、6 skipped、4 deselected、13 xfailed |
| 重建 OFF binding 后 parent focused | 497 passed；实际 native flag 为 False 且赋值抛 AttributeError |
| 修改 Python lint / 性能行为测试 | ruff 通过；3 项行为测试通过 |
| 两仓库差异检查 | git diff --check 通过 |

上述数量是实际结果，不是固定测试数量门禁。**类型检查没有通过：五个修改文件为 54 项诊断，全仓为 2139 项。** 用相同 ty/config 导出提交基线逐项比较五文件，基线 60 项，当前 54 项，新增 0、减少 6；两侧补足相同 sibling import 搜索路径后仍新增 0。对应依据为文件、函数、诊断类别和消息，不按行号或固定数量推断。此结论仅覆盖五文件，不能宣称全仓诊断均为既有问题。

Stage 5/6 的 OFF smoke 各产生 1 次预热和 6 个原始样本，`debug_checks_enabled=false`、`correctness_comparison=not_run`。ON 性能拒绝用例通过。正式采样未启动 oracle 或生成完整诊断 receipt；ON 原有 controller 的真实 synthetic/real 独立比较通过。

## 实际调用与复制证据

同一 synthetic 双批次 targeted 工作负载的 GDB 函数入口次数：

| 完整校验 | OFF 清理前 → 后 | ON 清理前 → 后 |
|---|---:|---:|
| aggregate validator | 1 → 1 | 13 → 9 |
| FIFO levels validator | 3 → 1 | 7 → 3 |

OFF 保留的调用来自 baseline/初始公开边界。这里没有声称整个算法只扫图一次，aggregate 内部仍承担其必要证明。每个被统计目标进程均正常退出；GDB pending 的复制符号不当作零复制证明。

恢复测试的两次实际恢复中，OFF `replayDualCsrModesForRecovery` 内的 aggregate 复制调用从 2 降为 0。测试新增了失败不发布的用例，测试调用层因此另有副本，不能直接比较整个恢复测试的总复制数；ON 仍保留独立 expected rebind 证明。成功交付的 graph 存储地址保持断言同时验证 move 发布。

另用当前真实 ExpectedBeforeBinding 头和每套构建实际编译参数执行隔离构造剖析，只在构造窗口计数 operator new：

| resolver / identity 记录数 | OFF 分配次数 / 字节 | ON 分配次数 / 字节 |
|---:|---:|---:|
| 1 | 0 / 0 | 6 / 5095 |
| 32 | 0 / 0 | 130 / 36099 |
| 128 | 0 / 0 | 514 / 132279 |

OFF 两个诊断 optional 均为空；ON 均存在且内容相等、存储独立。临时探针仅开放构造访问，未修改生产实现；graph/index 采用空对象移动以隔离诊断副本成本。结果不表示整条工作负载零分配，也不用于声称加速比。

清理前后及 OFF/ON 的 `--runtime-output` 功能投影全部相等，覆盖双批次恢复前、按模式重放后、恢复后继续下一 mixed 批次；比较拓扑、timing 和实际结果，排除计时、诊断与 session 实例身份。该开发比较没有加入性能入口。

## 实际失败与修复

1. 首轮 OFF 137 passed / 3 failed：DescriptorBuilder 的 `before` 别名仍读 resolver/identity optional，导致 `bad_optional_access`。将重复 resolver 重演和 capture-plan 重建移入 ON；保留必要 session/generation/high-water、真实 capture binding/coverage。新增错误 generation 拒绝且原状态保持的行为用例后双模式回归通过。
2. 首轮 ON 167 passed / 1 failed：malformed-generation 的错误归属从已删的输入 aggregate 检查移到现存 capability 边界。更新断言为真实拒绝位置，仍比较输入未变，重跑通过。
3. 首次交叉静态审查也漏掉 `before` 别名消费者。失败后重新沿全部 accessor、类型和别名追踪，复核修复；最终结论同时依赖动态回归，不把早期静态判断冒充完整验收。
4. 类型检查仍失败，范围与基线对应如上；没有为消除既有类型噪音增加重复检查、casts 或放宽实际输入验证。
5. 一次只读日志命令的自动审批超时，原命令未执行；按工具要求重试一次成功，没有遗留审批阻塞。

## 复核入口与交付

机器可读结果见 [验收证据](stage0-6-cleanup-acceptance.json)，开发归属见 [规范](development-guidelines.md) 和 [检查分类](debug-check-classification.md)。构建目录位于 ecc-tools，原始调用/功能结果在各自 `cleanup-profile/before` 与 `cleanup-profile/after`；性能原始样本在各构建目录 `src/operation/iSTA/test/*-timing-smoke/`。临时脚本、日志、构造探针与类型基线已另存到 OFF 构建目录 `cleanup-profile/support/`，不新增仓库测试框架。

从 `/home/shigure/code/ecc` 使用裸 flake，例如：

```bash
nix develop --command env PYTHONHOME=/home/shigure/.local/share/uv/python/cpython-3.11.13-linux-x86_64-gnu ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-incregpusta-off -R '^ista_' --output-on-failure -j 2
nix develop --command env PYTHONHOME=/home/shigure/.local/share/uv/python/cpython-3.11.13-linux-x86_64-gnu ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-ista-stage34 -R '^ista_' --output-on-failure -j 2
```

PYTHONHOME 仅用于已有嵌入式 Python 的标准库定位，不是诊断开关。ON 开发诊断采用既有 controller，完整命令约定见开发规范。未改通用 README，未升级依赖，用户四个文件的 SHA-256 核对一致；两仓库 HEAD 保持起点，没有 commit 或 push。
