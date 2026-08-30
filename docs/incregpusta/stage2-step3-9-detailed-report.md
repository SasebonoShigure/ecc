# Stage 2 Step 3–9 实现、问题与解决情况详细汇报

> 审计日期：2026-08-27
>
> 最后证据检查：2026-08-27 12:09 +08:00
>
> 审计对象：ECC parent 与 ecc-tools child 的 Stage 2 Step 3–9
>
> 分支：parent/child 均为 IncreGPUSTA
>
> 提交状态：Stage 2 仍在未提交工作树中，未推送
>
> 总结：Step 3–8 已完成实现并有成体系的验收记录；Step 9 尚未完成。最后检查时存在五个 build-tree 文件条目，其中四个为非占位草稿、step9_provenance.py 仍是两行 placeholder，且 outer driver/capture 仍缺失；不能宣称已有正式测量、三相 provenance 或阶段封板结果。因此 Stage 2 整体仍为“进行中”。

## 1. 总体结论

### 1.1 已经打通的链路

Step 3–8 已经形成以下 generation-0 CPU 参考链路：

    稳定 identity / FIFO / observation 合同
        ↓
    从 const Database 导出 detached complete input
        ↓
    在 Database 之外执行 CPU full-graph reference
        ↓
    按 stable semantic key 全量预验证并原子写回
        ↓
    由真实 session token 和 Database-exclusive guard 管理生命周期
        ↓
    在 fresh process 中与 native CPU/full 结果做独立差分

这条链路解决了正确性、隔离性、原子性和生产生命周期问题，但还不是完整的“增量 GPU STA”。

### 1.2 分步骤状态

| Step | 主题 | 状态 | 当前可以正式声明的结果 |
|---|---|---|---|
| 3 | Identity 与 Snapshot Observation Pure Contract | 已完成 | identity、FIFO、storage、observation、schema、parent parser 和隔离门禁已实现 |
| 4 | Detached Complete Reference Input | 已完成 | 可从只读 Database 原子导出 generation-0、self-contained candidate |
| 5 | DB-free CPU Full-Graph Reference Backend | 已完成 | 不读取 Database/native output 的纯 CPU 全图参考计算已实现 |
| 6 | Stable-key Timing Result Scatter | 已完成 | 全量预验证、detached preparation、no-fail publish 和失败零写入已实现 |
| 7 | Production Session Lifecycle 与 Parent Transport | 已完成 | 真实 token、独占 Database、one-shot capture、binding 和 parent 传输已接通 |
| 8 | Fresh-process Native/Reference Differential | 已完成 | 三类真实 case 的双进程数值差分、canary rerun 和负例矩阵已完成 |
| 9 | Metrics、Provenance 与阶段收口 | 未完成 | 评审候选计划和五个文件条目仍未组成七工具链；无 authoritative run、metrics 或 final review |

### 1.3 能力边界

已覆盖：

- generation 0 snapshot；
- 稳定 NodeKey、ArcKey 和六类 fingerprint；
- 完整 graph/constraint/Liberty/parasitic/timing-check 输入；
- Database-free CPU full-graph reference；
- stable-key native write-back；
- scatter 失败零写入；
- process-local session token；
- Database-exclusive authority；
- ready/invalidated/released observation；
- parent all-corner preflight 和 per-corner sink；
- fresh-process native/reference parity；
- source/object/depfile/target/schema/format/hygiene 门禁。

尚未覆盖：

- generation 大于 0；
- mutation batch；
- affected-cone propagation；
- Dual-CSR；
- CUDA/GPU backend；
- CPU/GPU 或 reference/native speedup；
- RSS、heap、allocator 等真实内存指标；
- 跨机器性能可比；
- Stage 2 最终提交与包装审计。

## 2. 审计口径

本报告交叉检查了：

- parent 和 child 实际 Git 状态；
- docs/incregpusta/stage2-step3-plan.md 至 stage2-step9-plan.md；
- docs/incregpusta/stage2-report.md；
- parent 的 sta_snapshot、sta_session、sta_signoff、module 及相关测试；
- child 的 adapter/csr、timing_csr、timing_csr_snapshot、interface 和 real_differential；
- build-ista-step8 的 CTest inventory 与 Step 9 文件；
- 当前文档 SHA-256 和冻结设计 SHA。

证据优先级为：

1. 实际代码、测试 inventory 和工作树；
2. stage2-report.md 的 as-built/final 记录；
3. 各 Step plan 的冻结合同和 As-built 段；
4. ignored build tree 中的临时文件。

两处需要特别说明的文档不一致：

- stage2-step7-plan.md 顶部仍写着“尚未编码”，但实际代码、Stage 2 报告、测试和三路复审均证明 Step 7 已完成。该行是未回填的旧状态。
- stage2-step8-plan.md 顶部主要描述 v0.14 合同，没有直接写“已完成”；完成状态来自实际实现和 stage2-report.md。

本次没有重跑完整 79 项 CSR 回归，也没有运行 Step 9。文中的测试数字是现有 as-built 记录，不是本次重新执行结果。

## 3. Step 3：Identity 与 Snapshot Observation Pure Contract

### 3.1 实现了什么

Step 3 建立了不依赖 Database 的纯快照合同，使 child C++、parent Python、JSON Schema 和测试语料对同一 snapshot 有一致解释。

主要交付：

1. Identity 分层

   - 通用 syntax validator 接受任意 uint64 generation；
   - Stage 2 committed validator 进一步要求 generation = 0；
   - identity 绑定 schema、session token、generation 和六类 fingerprint。

2. Analysis context 跨语言 fingerprint

   - parent 新增冻结的 StaAnalysisContext；
   - C++/Python 使用同一字段顺序、normalization 和 domain-separated SHA-256；
   - ASCII 与 UTF-8 known-answer 都有覆盖。

3. 唯一 FIFO replay

   - ordered roots 按冻结顺序入队；
   - BaseOut row order 决定边访问顺序；
   - root level 从 1 开始；
   - 每个节点恰出队一次才 complete；
   - metadata、backend 和后续 consumer 不再各写一套 Kahn/FIFO。

4. Storage 与九类 buffer extent

   - 从真实 size/capacity 派生 logical/capacity；
   - 派生 node/arc/level counts；
   - 计算 modeled host logical/capacity bytes；
   - caller 不能手填这些数字。

5. Typed observation

   - ready、invalidated、released 三态；
   - read、reference measurement、scatter rejection、scatter success、invalidation、release 六类 action；
   - static validator；
   - pure reducer；
   - before + action → after transition validator；
   - failed transition 保持原对象不变。

6. Schema 与 parent parser

   - strict JSON Schema；
   - duplicate key、NaN、Infinity 安全解析；
   - 四 lane corpus；
   - compiled-contract descriptor parity；
   - parent frozen dataclass、parser、validator、reducer、transition API。

7. Target 隔离

   - 新增 ista_timing_csr_snapshot_contract；
   - PUBLIC 只依赖 pure CSR core；
   - 不依赖 Database；
   - source/object/depfile/target property 和 consumer inventory 均有静态门。

### 3.2 遇到的问题、如何解决

| 问题 | 风险 | 解决 |
|---|---|---|
| 通用 identity 与 generation-0 committed 规则混在一起 | 当前约束和未来扩展互相污染 | 拆为 syntax 与 committed 两层 validator |
| 多个 consumer 各自计算 FIFO | 顺序、level、cycle 诊断漂移 | 提供唯一 helper，并冻结 production callsite 数量 |
| buffer/host bytes 由 caller 填写 | observation 与真实容器不一致 | storage visitor 直接读取 size/capacity |
| released 对象只能证明 shape，不能证明历史 | 非法状态跳转可能混过校验 | 增加 reducer 和 transition validator |
| first-invalidation policy 重复 | C++/Python 或不同路径 priority 不同 | 抽出共享 policy helper |
| test CMake 过大 | target ownership 难审计 | 拆分 CMake 和 exact inventory |
| 缺少 valueless variant 防御 | 极端状态可能抛 bad_variant_access | action 入口先检查 valueless_by_exception |
| 缺少 C++ UTF-8 KAT | 跨语言 hash 可能只在 ASCII 下正确 | 增加 C++/Python UTF-8 known-answer |
| callback 可绕开 descriptor | 测试只比 case ID 可能假绿 | descriptor-driven fixture/evaluator，逐字段 parity |

### 3.3 解决了什么

Step 3 解决的是“所有后续步骤是否在讨论同一个 snapshot”。它消除了 identity、FIFO、storage、状态转换和跨语言 schema 的多重真源。

### 3.4 现有验收记录

- 18 个 CSR target build；
- CSR 30/30；
- global unit/property/smoke 65/65；
- parent 293/293；
- schema/parity 2/2；
- compiled-contract parity 40 descriptors；
- C++、CMake/isolation、schema/parent 三路复审均 APPROVE，0 finding。

## 4. Step 4：Detached Complete Reference Input

### 4.1 实现了什么

Step 4 把图快照扩展为可独立计算的完整输入，核心 API 从 const Database、canonical analysis context 和 nonzero token 原子导出 detached candidate。

导出内容包括：

- graph；
- start seed 和 structural register/C2Q；
- raw constraints；
- optional output load；
- timing-check endpoint；
- present-empty timing table；
- referenced Liberty closure；
- typed parasitic semantics；
- support/unsupported reasons；
- identity 和六类 fingerprint。

构造顺序为：

1. context validation；
2. native projection；
3. intrinsic validation；
4. component/composite fingerprint；
5. token/generation binding；
6. self validation；
7. single move-return。

所有中间状态均为 local。失败时不返回 partial candidate，不创建 session、不 commit snapshot、不写 Database。

此外建立了：

- Primitives → NativeModels → Types 的 pure header DAG；
- canonical encoder 与 fingerprint payload 的共享 internal append 实现；
- raw native projection 与 canonical semantic identity 的分离；
- fresh、poison、deep candidate/raw KAT；
- 独立 Python decoder/recompute；
- public-header/include-order、const_cast absent、safe/poison 门禁。

### 4.2 遇到的问题、如何解决

| 问题 | 风险 | 解决 |
|---|---|---|
| 只有 graph，计算语义仍藏在 Database | Step 5 仍会偷读 native state | 增加 constraint、seed、load、Liberty、parasitic、check DTO |
| encoder 与 fingerprint payload 各写一套顺序 | hash/wire 静默漂移 | private shared encoder internal header |
| binary64 边界描述不精确 | support 判断跨语言不一致 | 按 native binary64 边界判断并加 KAT |
| unbound raw port 与 canonical role 混淆 | fallback provenance 或 stable key 失真 | raw/full-local 与 semantic pin 分离 |
| ArcKey direct-byte 顺序和 domain 有歧义 | deep fingerprint 漂移 | 修正顺序/domain，重新冻结 deep KAT |
| 失败可能留下半成品 | 不完整输入被误用 | local 构造、分层校验、成功 single move-return |
| fresh probe 可能链接旧对象 | 验证的不是当前源码 | authoritative relink 后再运行 |
| 测试可用 const_cast 修改后恢复 | input unchanged 假绿 | const_cast absent 和 poison detector |

### 4.3 解决了什么

Step 4 解决了“reference 算法的输入是否真的完整”。完成后 Step 5 不需要读取 Database、native timing output、cache 或 singleton。

### 4.4 现有验收记录

- CSR 48/48；
- 八个 functional target 与 public-header gate；
- exact 17-module Python DAG；
- 四个 PYTHONDONTWRITEBYTECODE CTest command；
- fresh/poison/property/failure/storage 和 legacy CSR 通过；
- 最终独立实现审查 APPROVE；
- deep candidate 3410 bytes，SHA-256：
  58cf82c5347b1d6bc8f13447690d73bb826d5ff20fb7b9e0eb3865d48c4bcd65；
- deep raw 1114 bytes，SHA-256：
  ae73fa8c86ae17fc0a7b2c06cba46813f258f45023591a117f0c93df4fc3a350。

## 5. Step 5：DB-free CPU Full-Graph Reference Backend

### 5.1 实现了什么

实现 CsrCpuReferenceBackend::compute，production 不读取 Database 或 native output。

冻结 outcome 优先级：

1. malformed；
2. unsupported；
3. FIFO cycle；
4. post-FIFO invariant；
5. numeric failure；
6. success。

计算分为五阶段：

1. canonical result initialization；
2. timing table lookup 与 arc transfer；
3. slew/delay forward propagation；
4. scalar/path arrival propagation；
5. reverse FIFO required/slack propagation。

数值合同覆盖：

- unit conversion；
- axis lookup/interpolation；
- scale、multiply、divide、ceil、fold、round、subtract；
- NaN、computed Infinity、非法负 slew；
- unreached arrival 的负无穷 sentinel；
- unconstrained required 的正无穷 sentinel；
- signed zero raw bits。

测试有两条独立证据：

- literal hand KAT；
- 不调用 production backend/table/FIFO/validator 的 O(VE) slow oracle。

另外提供 bit-exact whole-result comparator，对 shape、offset、ID、enum、string 和全部 double raw bits 逐字段比较。

### 5.2 遇到的问题、如何解决

| 问题 | 风险 | 解决 |
|---|---|---|
| 计划中的 CsrResultOrError 实际不存在 | API 与代码基线不一致 | 基于真实类型定义 CsrComputationResult variant |
| unsupported 与 computation code 可任意组合 | validator 接受矛盾结果 | 冻结唯一 priority，加入 cross-product test |
| backend 可能重复 FIFO | 第二真源和重复成本 | private seam 调用 Step 3 唯一 helper |
| table cache B1 错误 | 插值读取错误区间 | 修正 cache lane，增加定点 KAT |
| interpolation/arrival addition overflow 未分类 | Inf 继续传播或 partial result | 每个实际算术步骤做 finite 检查 |
| supported/unsupported 与 cycle overlap 不清 | 同一输入返回不同错误 | support 在 FIFO/cycle 前判定 |
| clock-source name 合同不足 | path provenance 不稳定 | 补齐字段和 validator |
| comparator 未覆盖九个 identity member | identity 漂移漏报 | schema/token/generation/六 fingerprint canary |
| slow oracle 可能复用 production | 测试自证 | source/depfile/nm/undefined-symbol/cross-directory poison |
| expected inventory 从 actual 反推 | 缺对象也可能假绿 | expected 独立 hard-code，singleton ownership |

### 5.3 解决了什么

Step 5 解决了“如何不读取 native 输出而独立重算完整 timing state”，为 Step 8 提供 reference lane 核心。

### 5.4 现有验收记录

Step 5 完成时：

- 四个 exact executable；
- 五个固定 seed property；
- Step 5 exact + chained isolation 13/13；
- 当时完整 CSR 57/57；
- global unit/property/smoke 73/15/4；
- parent non-PDK 1608 passed、8 skipped、4 deselected、13 xfailed；
- 16 个 test object、6 个 production object，共 22 个 depfile singleton owner；
- 三路独立复审 APPROVE，无剩余 blocker/major/minor。

## 6. Step 6：Stable-key Timing Result Scatter

### 6.1 实现了什么

Step 6 将 detached CsrTimingResult 安全写回当前 native Database。

主要交付：

1. Arc fallback provenance

   - typed timing-arc delay/fallback bulk state；
   - private friend replacement；
   - legacy mutable escape hatch 明确为有损路径。

2. Semantic native timing oracle

   - 按 stable semantic key 读取允许写回的 TimingPoint、Arc、timing order 和 provenance；
   - 不使用地址作为 identity。

3. Stable-key re-resolution

   - owner/committed guard；
   - current identity drift；
   - result priority；
   - node/arc/predecessor key 解析；
   - detached preparation；
   - no-fail publish。

4. 全量 prevalidation

   在第一笔 native 写入前完成 shape、identity、fingerprint、numeric、key existence、predecessor、write count 和所有 scratch allocation。

5. No-fail publish

   publish 只做 scalar assignment 和 nothrow swap，不再分配或执行 lookup。

6. Native dynamic rerun

   scatter 后写入 guaranteed-overwrite canary，再运行 native stage，证明 rerun 真实覆盖 canary 并恢复 oracle。

### 6.2 遇到的问题、如何解决

| 问题 | 风险 | 解决 |
|---|---|---|
| publisher 可能分配或抛异常 | Database 部分写入 | 工作全部前移到 detached preparation |
| derived scalar/path overflow | 非法数值写回 | 扩展 numeric prevalidation |
| Database 副本内 raw TimingCellArc 指针悬挂 | rerun 访问无效地址 | fixture 重建/重绑 provenance |
| supported chain roots 不完整 | root 语义未真实覆盖 | 修正 roots，补 singleton/multi-root |
| disabled 与 loop-disabled 混淆 | 覆盖声明失真 | 拆成独立 fixture/witness |
| parallel fixture 重复 net load 非法 | 测试失败归因错误 | 修正 owner/load 关系 |
| capture seam 折叠 NaN/Inf/signed zero | raw provenance 被隐藏 | 改为 raw IEEE bits |
| success capture 重复约 48 次 SHA | 重复成本和 owner 混乱 | 在冻结约束下收敛到约 17 次 |
| subset normalization 把 lookup/delete 带入 publish | publish 边界扩大 | private-friend direct swap |
| rerun 可能在 baseline 上 no-op | 通过不能证明 rerun 执行 | guaranteed-overwrite canary |

### 6.3 解决了什么

Step 6 把“边校验边写”改成“先完整证明，再一次发布”，从结构上解决了 scatter partial write 和 stale result 写入新 Database 的问题。

### 6.4 现有验收记录

- Step 6 exact 11/11；
- chained gates 7/7；
- 完整 CSR 68/68；
- global unit/property/smoke 78/20/5；
- success/failure/atomicity/lifecycle/inventory 多路矩阵；
- 两路 reviewer APPROVE，无剩余 finding。

## 7. Step 7：Production Session Lifecycle 与 Parent Transport

### 7.1 实现了什么

Step 7 将 Step 3–6 的 pure/detached 能力组合成真实生产 session。

主要交付：

1. Process-local token

   - valid session 获取 nonzero monotonic token；
   - invalid context 不消耗 token；
   - valid 后续失败烧号；
   - UINT64_MAX 后 sticky exhausted；
   - 不 wrap、不 reuse。

2. Generation-0 one-shot capture

   - 构建 detached input、metadata、ready/released twins；
   - success、typed failure 和 throw-first 都永久消费 capture attempt。

3. Session context 状态机

       awaiting-capture → ready → released
       awaiting-capture → capture-failed → released

   reference/scatter 只接受 owner token；release 幂等。

4. Database-exclusive authority

   legacy run、session run、copy、reference、scatter、close/destroy 共用同一 guard，拒绝 recursion、foreign context、pending owner 和 close race。

5. Database + observation joint publish

   scatter 成功同时发布 native state 和 next observation；失败保持 native writes = 0、原 observation 不变。

6. Binding

   pybind 只读暴露 session_token 和 csr_snapshot_observation；closed getter 不触发已销毁 singleton。

7. Parent transport

   parent 核对 native handle、context、observation identity/token 和 ready/released transition。

8. All-corner preflight

   在 capability/subflow/engine/artifact 之前完成 immutable 全 corner 预检；每 corner sink 隔离，legacy harden collector 和 Stage 1 十字段 record 保持兼容。

### 7.2 遇到的问题、如何解决

| 问题 | 风险 | 解决 |
|---|---|---|
| malformed result identity 分类与 Step 3/6 冲突 | observation 与 scatter reason 不一致 | 编码前修订合同和 KAT |
| binding 未明确暴露 token/observation | parent 无法验证 owner | 收紧为两项只读 surface |
| signoff collector 与 incremental sink 混流 | corner 串值或 legacy 回归 | per-corner sink 与 legacy collector 分流 |
| throw-first 后可能再次 capture | one-shot 被异常绕过 | attempt 开始即永久消费 |
| run/scatter 成功排序缺少证据 | exclusive authority 假绿 | 增加独立排序 KAT |
| 拆分 STAInterfaceOperations 后 diagnostic/log 漂移 | legacy 行为回归 | 机械迁移并恢复精确语义 |
| init/close cleanup 同时抛异常 | released handoff 丢失 | 先提交 released/closed，再组合诊断 |
| parent failure terminal 未清空内部状态 | closed getter 看到半关闭对象 | 统一清空 native/context/observation |
| Liberty parser 不能跨顺序 session 复用 | fresh session lane 失败 | incremental lane 前重新读取 Liberty |
| CTest timeout 用字符串比较 | 数值相等配置误判 | numeric timeout comparison |

### 7.3 解决了什么

Step 7 解决了“谁拥有 Database、snapshot 何时产生、谁可以 compute/scatter、何时 release、parent 如何看到一致状态”。

### 7.4 现有验收记录

- frozen plan SHA-256：
  2996e2d8f558c7707290e7978fc9b6a1f0ce5f4ba680f201083b0829c5627313；
- native、parent、gate 三路最终复审 APPROVE；
- 四个新 KAT；
- umbrella inventory；
- controller validation；
- fresh-process session lane；
- global unit/property/smoke 84/20/6；
- parent 定向 102 项 pytest、Ruff、format、scoped type check 通过。

## 8. Step 8：Fresh-process Native/Reference Differential

### 8.1 实现了什么

Step 8 不修改 production 路径，而是在独立进程中比较两条 lane。

Oracle lane：

- 运行 native CPU/full baseline；
- 只输出 neutral timing-state wire。

Reference lane：

1. 同一 fixture 完成 full baseline；
2. poison 所有允许写回 state；
3. 导出 candidate；
4. 运行 DB-free backend；
5. stable-key scatter；
6. semantic-key readback；
7. canary；
8. native rerun；
9. 验证恢复 oracle。

真实 case：

- chain；
- diamond；
- supported_branches extended。

extended 覆盖：

- non-unate；
- parallel；
- disabled；
- loop-disabled；
- multi-root；
- multiple clock tags；
- near-tie；
- post-scatter rerun。

普通验收：

- 3 case；
- 每 case 3 repeat；
- 9 pair；
- 18 child。

controller 独立验证 argv、PID/nonce、raw bytes、六 fingerprint、generation 0、observation、semantic-key 数值、publication 和 process cleanup。

公开负例 30 项，覆盖 signed zero、NaN/Inf、near-tie、unsupported、stale identity、ArcKey、raw provenance、summary、same-fd/no-clobber、rollback 和 timeout/exit/pipe failure。

### 8.2 遇到的问题、如何解决

| 问题 | 风险 | 解决 |
|---|---|---|
| 完整 CSR 首跑只有 76/79 | 窄测试隐藏跨步骤回归 | 执行完整回归并逐项定位 |
| FIFO complete/cycle diagnostic 与 manifest 不同 | parity 失败或错误分类 | 统一双向 exact message |
| identity 比较用 else-if | 多字段漂移只报告一项 | 改为顺序独立 if，主 reason 仍按 typed priority |
| Nix loader 二进制嵌入 host Python/expat | 测试 #119 无法启动 | 仅本地 ignored binary 改 system interpreter |
| until-pass:3 首轮通过即停止 | 没有真正三次稳定性 | 改用 until-fail:3 |
| 工具文件超过行数建议 | 为压行可能删证据 | 行数降为维护性建议，reviewer 看具体职责 |
| timeout 后可能遗留 child/grandchild | 污染后续运行 | terminate → wait → kill → reap |
| publication 可能覆盖已有 evidence | 重跑破坏历史 | same-dir temp、same-fd、hardlink no-clobber、rollback |

本地 interpreter workaround 不是源码/CMake 修复，也不是 portable wheel 证明，必须继续作为限制披露。

### 8.3 解决了什么

Step 8 解决了“pure backend/scatter 是否只在 synthetic test 中自洽”。fresh process、poison、独立 decode/recompute、canary 和 native rerun共同建立了真实对照证据。

### 8.4 现有最终验收记录

| 门禁 | 结果 |
|---|---|
| Step 8 exact | 4/4 PASS |
| 普通 fresh | 9 pair / 18 child PASS |
| until-fail:3 | 3/3 PASS；27 pair / 54 child |
| Step 3–7 chained | 9/9 PASS |
| 完整 ista_csr | 79/79 PASS |
| global unit/property/smoke | 87/20/7 PASS |
| Stage 0 focused | 41/41 PASS |
| Stage 1 focused | 495/495 PASS |
| parent non-PDK | 1665 passed、8 skipped、4 deselected、13 xfailed |
| strict C++、nm、VALID depfile | PASS |
| clang-format 21.1.8 | 239 个 changed/new C++ 文件 PASS |
| schema/corpus/parity | PASS；40 descriptors |
| tracked diff/whitespace/hygiene | PASS |
| final review | 设计、Python、C++/CMake、global fix 均 APPROVE |

当前 build tree 的 CTest inventory 仍列出 79 个 ista_csr 测试；本次没有重跑。

## 9. Step 9：Metrics、Provenance 与阶段收口

### 9.1 计划要实现什么

Step 9 不新增 production 功能，而是对 Step 8 最终实现做窄 measurement smoke：

- 3 case；
- 每 case 6 repeat；
- repeat 0 为 warmup；
- repeat 1–5 为 measured；
- 每 repeat 2 lane；
- 预期 36 lane finals。

唯一允许采样的 timing：

- export；
- reference；
- scatter preparation。

计划输出：

- 18 timing rows；
- 18 storage rows；
- 9 aggregate rows；
- median；
- nearest-rank p95；
- modeled storage；
- comparability_status = non_comparable。

禁止声明：

- speedup；
- end-to-end/process startup/native full 性能；
- RSS/PSS/heap/allocator；
- GPU/CUDA；
- generation 大于 0；
- 跨机器可比或 statistically stable benchmark。

### 9.2 当前实际状态

Step 9 未完成，证据如下：

- stage2-step9-plan.md 状态为 v0.29 review candidate；
- 文件明确写明“双审前仍不得运行、实现或 commit”；
- 当前 candidate SHA-256：
  70c1f613a2461f28dcffec4c9a371673b6847a2f3b6d0704786cf7208314127e；
- 该 SHA 不是 approved/frozen SHA；
- 计划要求七个工具；截至 2026-08-27 12:09 +08:00，发现五个文件条目：
  - build-ista-step8/step9_capture_supervisor.py；
  - build-ista-step8/step9_reduce.py；
  - build-ista-step8/step9_context.py；
  - build-ista-step8/step9_recheck.py；
  - build-ista-step8/step9_provenance.py；
- 其中 step9_provenance.py 只有两行、41 bytes，内容为 placeholder，不能算完成实现；
- 尚缺：
  - step9_outer_driver.py；
  - step9_capture.py；
- 其余四个文件也没有已冻结 SHA、KAT、双路读码审查或 authoritative execution 证明，仍只能视为草稿；
- 没有正式 step9-evidence、authoritative run、PRE/POST/FINAL provenance、18/18/9 汇总、report publication 或 final review receipt；
- plan-review pyc repair intent/receipt 只证明 cache 修复，不是 Step 9 measurement evidence。

因此不能写“Step 9 已实现”，也不能给出 Step 9 timing、median、p95 或 storage 数字。

### 9.3 规划阶段遇到的问题

| 问题 | 风险 | 计划中的解决 | 当前状态 |
|---|---|---|---|
| Step 8 历史 review/gate 没有统一 machine receipt | 虚构历史 receipt | prior attestation 只转录有来源结论 | 合同已写，未执行 |
| 出现 15 个 CPython 3.13 pyc 和 4 个 cache dir | source hygiene 破坏 | repair intent + receipt + fresh absence | 修复存在，不等于 Step 9 完成 |
| Python/site/PATH/repo import 污染 | evidence 不可复现 | 固定 Nix Python、-B -I -S、captured loader | 未形成完整工具链 |
| controller 需要 sibling import | 与七工具 -I 隔离冲突 | controller 单独使用 -E，分别冻结 prefix | 未 authoritative run |
| 两 lane 并发影响 timing | 样本不适合作严格 benchmark | 记录 concurrency，标记 non_comparable | 声明边界已冻结 |
| 33 个 timed object flags 不统一 | 不能宣称统一浮点条件 | 记录 actual flags，不作 uniform claim | 计划层解决 |
| evidence publication 有 TOCTOU/覆盖风险 | 重跑覆盖旧证据 | no-follow、same-fd、no-clobber、fsync、rollback | 整链未完成 |
| child/grandchild 泄漏 | 后续运行被污染 | 三层 process-tree supervisor | 未完成 KAT |
| reducer 自证 | 汇总算法错误仍通过 | independent recheck 不导入 reducer | reducer/recheck 均有草稿，但未冻结、未 KAT/双审/正式运行 |
| report 修改夹带其他变化 | provenance 不清 | PRE/POST/FINAL，只允许 report delta | 未执行 |

### 9.4 已解决与未解决的界线

已在设计层解决：

- 采样字段；
- warmup/measured 规则；
- 可声明和禁止声明的内容；
- 33 个 timed object 范围；
- Nix/Python 环境；
- process tree；
- no-clobber publication；
- reducer/recheck 双路径；
- PRE/POST/FINAL provenance；
- Step 10 提交边界。

尚未在实现/证据层解决：

- 七工具完整实现；
- self-test/KAT；
- 两路工具 review；
- authoritative capture；
- context 18/36 重建；
- reducer/recheck 18/18/9 一致；
- 三相 provenance；
- report atomic publication；
- final metrics review；
- Step 9 完成判定。

### 9.5 完成 Step 9 还需要

1. 双审并冻结 v0.29 exact SHA；
2. 只读绑定 Step 8 plan、cleanup 和 pyc repair evidence；
3. 在固定 Nix 环境完成七工具；
4. 运行 self-test/KAT 和两路读码审查；
5. 生成 prior attestation 和 PRE provenance；
6. 执行 3 × 6 × 2 authoritative run；
7. 重建 18/36 context；
8. reducer/recheck 独立得到相同 18/18/9；
9. 生成 POST provenance；
10. 原子更新 stage2-report.md；
11. 生成 FINAL provenance；
12. 两路 final review APPROVE；
13. 仍不 commit、不 push，再进入 Step 10。

## 10. 跨步骤解决的关键问题

### 10.1 从地址身份转为语义身份

Step 3–6 逐层使用 canonical NodeKey、ArcKey、component fingerprint 和 semantic-key re-resolution，避免把 pointer、Database vector index 或临时 rank 当成跨阶段 identity。

### 10.2 从“测试能跑”转为“测试独立”

Step 5 slow oracle 和 Step 8 opaque lanes不读取 production output，不共享 backend/table/FIFO/validator；source/object/depfile/nm 门禁检测依赖越界，解决 reference 与 oracle 共享同一错误而一起通过的问题。

### 10.3 从“失败后恢复”转为“首写前证明”

Step 6/7 把 scatter 分为 validation、resolution、detached preparation、no-fail publish。所有可能失败的工作在首写前完成，成功时只做不可失败的发布。

### 10.4 从静态 shape 转为可验证历史

Step 3 reducer/transition、Step 7 state machine、Step 8 process transcript共同证明对象是如何到达终态，而不只是终态字段看起来合法。

### 10.5 从窄单测转为 full-chain fresh-process

Step 8 首次完整回归 76/79，实际发现 FIFO diagnostic、identity overlap reporting 和 runtime closure 三类问题，说明全链路门禁不是形式上的重复。

## 11. 主要文件与职责

### 11.1 Parent

- chipcompiler/tools/ecc/sta_snapshot.py
  - context、identity、observation public model/API。
- chipcompiler/tools/ecc/_sta_snapshot_validation.py
  - strict parser、validator、reducer、transition。
- chipcompiler/tools/ecc/sta_session.py
  - token/observation transport 和 terminal cleanup。
- chipcompiler/tools/ecc/module.py
  - analysis context 与 observation sink。
- chipcompiler/tools/ecc/sta_signoff.py
  - direct/all-corner immutable preflight。
- test/tools/ecc/test_sta_snapshot*.py
  - context/schema/transition/known-answer。
- test/tools/ecc/test_sta_session_snapshot.py
  - session transport。
- test/tools/ecc/test_module_timing_snapshot.py
  - module sink。
- test/tools/ecc/test_sta_signoff.py
  - corner isolation。

### 11.2 Child

- source/module/timing_csr_snapshot
  - Step 3 storage、observation、transition。
- source/module/timing_csr
  - identity/FIFO/validator 和 Step 5 backend。
- source/data_manager/adapter/csr
  - Step 4 complete input、Step 6 oracle/scatter、Step 7 snapshot adapter。
- interface
  - Step 7 exclusive guard、session context、lifecycle。
- interface/python/py_ista
  - Step 7 binding。
- test/reference_input
  - Step 4 independent projection/recompute。
- test/timing_scatter
  - Step 6 success/failure/atomicity/rerun。
- test/csr_session
  - Step 7 fresh-process session。
- test/real_differential
  - Step 8 probes、wire、controller、self-test。
- CheckCsrStep3...Step8
  - source/object/target/workflow/isolation gates。

### 11.3 Step 9 build tree

截至最后证据检查，存在：

- step9_capture_supervisor.py；
- step9_reduce.py；
- step9_context.py；
- step9_recheck.py；
- step9_provenance.py（两行 placeholder）；
- step9-plan-review-pyc-repair-intent-v1.json；
- step9-plan-review-pyc-repair-receipt-v1.json。

仍缺 step9_outer_driver.py 和 step9_capture.py。现有 ignored build-tree 文件没有完整 freeze/KAT/review/run/provenance 证据，不构成 Step 9 交付。

## 12. 当前遗留问题与风险

1. Step 9 未完成

   没有 authoritative metrics 和三相 provenance，Stage 2 不能标记为完成。

2. Step 7/8 plan 顶部状态过时

   实际实现完成，但元数据没有完全回填，容易误导。建议在 Step 9 final publication 时校正状态，不改冻结正文语义。

3. Step 8 本地 interpreter workaround 不可移植

   只修改 ignored local binary，不是源码/CMake 修复，也不能证明其他机器/wheel runtime closure。

4. 只有 generation 0

   当前 session/reference/scatter 只证明 full-baseline generation 0，不是 mutation 后的真正增量 STA。

5. 没有性能结论

   Step 8 controller/CTest runtime 不是 benchmark。Step 9 即使完成，也只能报告 non_comparable 的内部描述性 timing。

6. 工作树未提交

   parent HEAD 为 ee2563b，child HEAD 为 a7355b；child 在 parent 中显示 dirty submodule，但 gitlink 未前移。

7. 用户既有改动必须保留

   CLAUDE.md 的既有修改和 stage1-stage2-meeting-report.md 未跟踪文件不能混入 Stage 2 提交或被格式化覆盖。

## 13. 成果与不足

### 13.1 已形成的成果

- 稳定、跨语言一致的 snapshot contract；
- self-contained reference input；
- 独立 CPU full-graph reference；
- 失败零写入的 stable-key scatter；
- 真实 production session lifecycle；
- parent all-corner context/observation transport；
- fresh-process native/reference differential；
- isolation、inventory、fault matrix 和 hygiene 体系。

### 13.2 尚未形成的成果

- mutation/generation 大于 0；
- affected cone；
- Dual-CSR；
- CUDA/GPU；
- speedup；
- 可比较 benchmark；
- Step 9 final report；
- Stage 2 local commit 和包装审计。

当前成果更准确的名称是：

“Generation-0 CSR reference foundation、production session integration 与 native parity validation。”

不应称为：

“增量 GPU STA 已完成”或“已获得性能加速”。

## 14. 建议后续顺序

1. 先审查 v0.29 的复杂度和可实现性，避免继续无限扩展合同。
2. 冻结 Step 9 exact SHA。
3. 完成剩余五个工具和七工具 KAT。
4. 执行 3 × 6 × 2 authoritative run。
5. 由 reducer/recheck 独立生成 18/18/9。
6. 生成 PRE/POST/FINAL provenance。
7. surgical 更新 stage2-report.md。
8. 校正文档顶部过时状态。
9. 两路 final review 无 finding 后宣布 Step 9 完成。
10. Step 10 只做本地提交和包装审计，不自动 push。

## 15. 可追溯信息

### 15.1 Git 基线

- parent：
  ee2563b2d27165d9324d82103cdf28bddb414956
- child：
  a7355b216b801f72a99d92e77765f49c744148b3
- branch：
  IncreGPUSTA
- 状态：
  Stage 2 未提交、未推送

### 15.2 冻结设计 SHA

- Stage 2 总计划编码前：
  052ae59be69c4ad097d716d279275d19b75940ca07567e481f565d95b9f7aa64
- Step 3 v0.4 approved design：
  188d1184ec0e16f62339c484df515aed08fe5e722fc32fc1f308adcb44e2b050
- Step 5 v0.2 approved design：
  d8850b74cd6995f1f050efbda0e0ed08d2c930ace1163690a105995cdc15112b
- Step 6 v0.7：
  d36e4831626093b8a12813ac2053bdd0a6baae4b77c22ebefed2ecfd94804daa
- Step 7 v0.3：
  2996e2d8f558c7707290e7978fc9b6a1f0ce5f4ba680f201083b0829c5627313
- Step 8 v0.14：
  604dd5427d2ba1003ff4e22ae0ab3e5760148331fd1fcebf1e33ae2d9c402be2

### 15.3 当前文档 SHA

本次审计时：

- stage2-step3-plan.md：
  b33f76b74b3698c68c7572d010c552d3107210a99251330d454bbd5b5745be13
- stage2-step4-plan.md：
  cfbdbb5c64918d023ad56da16efa84095770a2c9caac02b84f10c344107ed0f4
- stage2-step5-plan.md：
  b2366304244210e9056ee3accd4a3c7b9f4d2cabc763f283c776dccf94e7e31d
- stage2-step6-plan.md：
  d36e4831626093b8a12813ac2053bdd0a6baae4b77c22ebefed2ecfd94804daa
- stage2-step7-plan.md：
  2996e2d8f558c7707290e7978fc9b6a1f0ce5f4ba680f201083b0829c5627313
- stage2-step8-plan.md：
  604dd5427d2ba1003ff4e22ae0ab3e5760148331fd1fcebf1e33ae2d9c402be2
- stage2-step9-plan.md：
  70c1f613a2461f28dcffec4c9a371673b6847a2f3b6d0704786cf7208314127e
- stage2-report.md：
  026ba999791ec0c5e502e24a1ba48a7691e6a8f4218b8c3ed0925dd4918cea5f

Step 3/5 当前文件含 as-built 回填，所以当前文件 SHA 与编码前 approved design SHA 不同。Step 9 当前 SHA 仅表示 review candidate bytes，不能标记为 approved/frozen。

## 16. 最终结论

Step 3–8 已经完成一条严谨的 generation-0 CPU reference 与 native parity 基础链路，实际解决了 identity 漂移、FIFO 多真源、输入不完整、数值异常、oracle 自证、scatter 部分写入、session ownership、跨语言 transport、fresh-process 隔离和全局回归假绿等问题。

Step 9 尚未完成。最后检查时只有四个非占位工具草稿、一个 provenance placeholder，outer driver/capture 仍缺失；没有正式测量、三相 provenance、18/18/9 汇总或 final review。

最准确的项目状态是：

“Step 3–8 完成；Step 9 待评审、待完整实现、待运行；Stage 2 仍进行中。”
