# IncreGPUSTA 开发检查分离实施报告

日期：2026-09-05。Stage 0–6 的开发检查分离已实施，保留未提交的工作区差异供审阅。本轮不 commit、不 push，不修改通用 README、用户 CLAUDE.md 修改及用户报告，也未升级项目依赖。

开发规则见 [开发检查规范](development-guidelines.md)，调用分类和复杂度见 [检查分类](debug-check-classification.md)，机器可读实测记录见 [验收证据](debug-check-acceptance.json)。总计划位于 `ecc/docs/incregpusta-implementation-plan.md`，已加入必读规范；Stage 0–6 主计划/报告已补充当前协议，历史验收数字没有改写成本轮结果。

## 实现结果

- 新增默认 OFF 的 `ECC_INCREGPUSTA_DEBUG_CHECKS`。统一生成配置头经 CMake interface target 传给相关 native、binding 和 probe；不使用 NDEBUG/assert 控制新增诊断，不增加 Python 环境变量或运行期开关。
- Python 读取 native 的只读布尔属性 `incregpusta_debug_checks_enabled`。OFF 跳过 observation 获取、对象转 mapping、解析与复制，真实初始化、执行合同和 close 保留。
- 快照保留实际 input、scatter 所需状态和失效身份；重复 observation 归约、深拷贝与 native 已受控数据库全库复查归 ON。
- `CsrExecutionAuthorization` 取代将 full-exact 当作提交条件的 receipt。两模式都保留受控授权、session/generation 检查；完整证明 payload 仅 ON 存在，OFF 的 `hasFullExactProof()` 为 false。移动后的授权失效。授权与诊断 payload 不再重复保存绑定字段。
- Dual-CSR stage/recovery 使用 session、generation 和 committed identity 绑定；只有 ON 额外保存整个 expected aggregate。真实 staged 副本、rollback 数据、编辑记录与模式恢复继续保留。
- 重复 aggregate/index/resolver 扫描、结果重算、独立 recovery rebound/prefix/full comparison、详细 capture/访问审计和完整 levels trace payload 归 ON。OFF 不维护 full-levelizer 计数窗口，也不为未执行的 invariant 扫描读取计时器。
- `telemetry.logical_edges_after` 是例外：edge view 用它驱动 levelization，因此其维护和公共输入校验始终保留。`ExpectedBeforeBinding` 的图和索引也用于真实 descriptor 构造，不能删除。首次外部输入校验、descriptor 适用性和局部 expected-value 检查继续运行。
- 原子 publish、实际 native rollback、close 后重新加载和按保存模式逐批恢复始终运行。OFF 明确拒绝非默认 failpoint，不能静默忽略。
- 原 timing smoke 拆为 OFF 性能入口与 ON 的 `dual_csr_diagnostic_timing_smoke.py`。性能 schema 升为 `ista-dual-csr-timing-smoke/2.0.0`，单进程结果为 `ista-incregpusta-performance-process/2.0.0`。保存初始规模、最终规模、预热、原始样本、真实构建信息、请求/执行模式、fallback 和实际 rollback 结果；比较写为 `not_run`，不生成完整功能 receipt、不启动 fresh oracle、不比较 source isolation。ON 在采样前被 native 和 Python 两层明确拒绝。

## 构建与功能验收

两套构建均使用同一 GCC 14.3.0、Release `-O3 -DNDEBUG`、相同依赖及 Python 3.11.13：

| 构建目录（ecc-tools 下） | 诊断选项 | Native 回归 |
|---|---|---|
| `build-incregpusta-off` | 初次配置省略选项，cache 为 OFF | 140 passed；28 项诊断合同明确 Disabled / Not Run |
| `build-ista-stage34` | 显式 ON | 168 passed；含完整功能、属性、故障注入、fresh differential 和逐字段比较 |

最后提交授权 payload 去重后，重新严格构建相关 native 目标，并重跑 Stage 3/4 与恢复相关回归：OFF 25 passed / 9 diagnostic disabled，ON 34 passed。以上数量是本轮实测记录，不是后续门禁阈值。

OFF 覆盖真实 baseline、Stage 3 提交及错误 generation 触发的实际数据库回滚、Dual-CSR full/mixed、多批次与恢复后继续执行。保留 malformed input、stale descriptor、owner conflict、unsupported 请求、实际 cycle 分类、已知/未知 failpoint 拒绝等边界；不能只依据性能样本成功替代这些功能测试。`TimingEditRuntimeContract` 同时检查实际 instance/net 是否提交或恢复。

两套真实 `ecc_py` 均成功构建并导入：属性分别为 False/True，和对应 native probe 相符；赋值都抛出 AttributeError。现有 packaging 输出仍使用共享 `bin/`，本轮将两份已验收 binding 保存到各自 `build-*/binding/`，最终共享 `bin/` 留为 OFF。

parent focused：497 passed。parent 非 PDK 回归：1667 passed、8 skipped、4 deselected、13 xfailed。修改的 Python 文件及性能脚本 lint 通过，session 模块单独 `ty check` 通过；两仓库 `git diff --check` 通过。新增 native 文件和改动行已格式化，没有文件因本轮修改从 700 行以下跨到 700 行以上。

**全仓库 `ty check` 未通过，报告 2146 项诊断。** 本轮没有扩展到修复无关模块的类型问题；不能将此项记录为通过。详见下方失败记录。

## 跨构建比较与性能路径证据

显式开发验收运行 `ista_stage6_mode_recovery_replay_test --runtime-output <file>`，对两套构建比较实际功能投影，排除计时、session 实例身份和诊断字段。以下 JSON 对象完全一致：双批次恢复前、按 full→mixed 模式重放后、以及单批恢复后继续下一 mixed 批次。原始结果保留在各构建目录 `acceptance/functional.json`，这一步没有加入普通性能入口。

Stage 5 和 Stage 6 的 OFF smoke 各完成 1 次预热及 6 个原始样本。输入均为 6 个 node slots、5 个 arc slots、2 批次；实际到 generation 2，输出 12 个 node slots、14 个 arc slots、fallback 0，native 最终 rollback 完成。两条 ON 性能拒绝用例通过。

性能行为测试检查每个样本仅调用一次 `performance` 子进程，并检查 ON 在创建运行目录或调用采样子进程前被拒绝。GDB 对同一 synthetic 双批次工作负载测得如下实际函数入口次数：

| 调用 | OFF | ON |
|---|---:|---:|
| DualCsrUpdater::stage（含两层重载） | 4 | 4 |
| aggregate validation | 1 | 13 |
| 完整 exact receipt | 0 | 1 |
| source physical snapshot | 0 | 2 |
| full-levelizer diagnostic window | 0 | 2 |
| native 全库复查 | 0 | 2 |

OFF 的一次 aggregate validation 来自公共 coordinator 初始输入边界。OFF 中 receipt、计数窗口、native 全库复查符号未被链接到该 probe，GDB 相应断点保持 pending；不能把 pending 解释成已执行的验证。两模式目标进程均正常退出，目标 updater 确实运行。GDB 只用于调用证据，其耗时不进入性能样本；本轮不据此声称加速比。原始命令、日志和计数保留在各构建目录 `call-profile/`。

## 实际失败、修复与限制

1. 新 Python fixture 初稿漏传既有参数，出现 2 failed / 70 passed；补齐 fixture 后 72 passed，后续 parent 回归通过。
2. optional receipt 迁移期间出现 aggregate 初始化和 probe 访问适配编译错误；补齐结果初始化及 ON 分支访问后严格构建通过。新增恢复用例还暴露 namespace shadow 和缺少 updater include，均已修复。
3. pybind 初次构建误取系统 Python 3.12 头文件；两 cache 的 `PYTHON_EXECUTABLE`、include、library 对齐仓库 Python 3.11 后通过。嵌入式 binding 测试的 Python 标准库前缀未定位到 uv runtime，测试环境显式提供该 runtime 的 PYTHONHOME 后通过；这不是 IncreGPUSTA 调试开关。
4. OFF session baseline 曾仍强制读取 observation；改为保留实际 ready snapshot 检查，ON 才读取诊断对象。释放用例曾错误要求容器指针必须为空，已改为检查真实 released 生命周期状态。
5. 首次关闭 updater 计数时误将 functional active-edge 数量一并关闭，导致 full stage 拒绝；追踪到 edge view 消费者后恢复其始终维护与校验，双模式功能和跨构建比较通过。
6. 原测试中的 full-exact receipt、完整 observation、审计计数和注入故障要求曾导致 OFF 回归失败；按检查用途分离 ON 诊断套件，混合职责的 updater/backend/native 拒绝用例保留 OFF 功能部分。原 preloader 输入拒绝曾被诊断 CLI 前置阻断，已保留该输入边界入口。
7. 新增的额外第三批 fixture 在 ON/OFF 均因 narrow capture 的 batch binding 不满足而被拒绝。本轮采用既有受支持的“两批模式重放”和“一批恢复后继续第二批”场景验收；没有声称该额外第三批输入通过，也没有放宽必要绑定检查。
8. lint 发现的新增长行和嵌套 with 已修复。全仓 `ty check` 的 2146 项诊断仍在，修改 session 模块的独立类型检查通过；无关类型问题不在本轮修复范围。
9. 自动审批曾拒绝范围过大的批量字符串核心改写，该脚本没有执行；之后改用单模块精确补丁、审阅差异并检查补丁适用性，未留下审批阻塞。

## 复核入口

从 `/home/shigure/code/ecc` 使用裸 flake `nix develop --command ...`，不要使用 `path:.`。本轮保留两套已配置的构建目录，可执行：

```bash
nix develop --command cmake --build chipcompiler/thirdparty/ecc-tools/build-incregpusta-off --target ista_stage6_mode_recovery_replay_test ista_timing_edit_transaction_test -j 4
nix develop --command ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-incregpusta-off -R '^ista_' --output-on-failure
nix develop --command ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-ista-stage34 -R '^ista_' --output-on-failure
```

当前 uv Python 的嵌入式测试另需在上述 ctest 命令前设置 `PYTHONHOME=/home/shigure/.local/share/uv/python/cpython-3.11.13-linux-x86_64-gnu`。Native probe 的 `build-info` 显示实际选项值。ON 的显式诊断 timing smoke 保留旧丰富输出，正式性能入口不会自动调用它。

本轮日志位于 `/tmp/incregpusta-*.log`；持久验收摘要在本目录 JSON，原始功能/性能/剖析产物在上述 build 目录。未建立源码字符串、对象清单或固定测试数量门禁。审查为本轮直接代码审查，不伪称新增独立 subagent 审查。
