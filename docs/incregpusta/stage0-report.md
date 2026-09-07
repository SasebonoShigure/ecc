# 阶段 0 报告：CPU full-STA 黄金基线与验证脚手架

> 当前开发协议补充（开发检查分离）：baseline oracle 和完整 receipt 属于 ON 诊断；默认 baseline 的真实加载、运行与清理由 OFF 运行用例验收。 后续改动必读 [开发检查规范](development-guidelines.md)，双模式实测与历史验收的区别见 [本轮实施报告](debug-checks-implementation-report.md)。原阶段验收数字保留为历史记录。

> 状态：本地完成；两名独立审查者最终均为 `APPROVE`
> 日期：2026-08-19
> 范围：阶段 0 只建立现有 CPU/full STA 的可重复 correctness oracle、测试/工件契约和后续 benchmark schema，不实现增量 STA、CUDA backend 或新的生产 STA 行为

## 1. 结论

阶段 0 已完成。ECC 现在有两个自包含、无 PDK 依赖的 native iSTA case，以及能够在独立 OS 进程中重复执行 production full-STA 路径、规范化结果并与 checked-in golden 做容差比较的 harness。测试覆盖拓扑、双向邻接、timing order、level、AT/RAT/slew/slack/path state、arc delay、path groups、power、报告与 SDF 工件。

这不是增量 STA 或 GPU 实现。当前可执行路径仍只有既有的 CPU/full STA。阶段 0 没有增加 mode 选择、CSR 转换、持久 session、fallback 行为、greedy buffer insertion 或 GPU kernel，也没有改变任何生产 STA 默认行为。

论文边界按以下口径冻结：

- 论文新算法是 Dual-CSR 增量图更新与 mixed-subgraph 增量 levelization。
- 论文的 GPU timing propagation 仍是全图传播；论文没有给出 GPU affected-cone AT/RAT 传播算法。
- greedy buffer insertion 是论文 case study，将在后续阶段作为确定性 mutation workload 实现，不在阶段 0 冒充生产物理插入。

详细能力边界见 [stage0-feature-support-matrix.md](stage0-feature-support-matrix.md)。

## 2. Git 与来源状态

| 项目 | 分支 | 基线提交 | 阶段 0 结束状态 |
|---|---|---|---|
| ECC parent | `IncreGPUSTA` | `f783db8d8c4d22559993d27ddeac314fa35a58ca` | 阶段 0 变更由本报告所在的 parent commit 记录；尚未推送 |
| ecc-tools submodule | `IncreGPUSTA` | `31ebf6cae5ba8b4a472b97947acf54e1deb82daa` | 本地提交 `f1b1351a18d862b086de8b191f51ee5a1688638b`；尚未推送 |

阶段 0 已创建两级本地 commit：parent 通过 gitlink 记录上表的 ecc-tools commit。两个分支都尚未推送，因此仍不应宣称可由远端 checkout 复现；推送 parent 前必须先推送 ecc-tools commit，并确认远端 branch 可达。

## 3. 环境

| 项目 | 值 |
|---|---|
| OS | WSL2 Linux `6.6.87.2-microsoft-standard-WSL2`，x86_64 |
| CPU | Intel Core i7-13700H，20 logical CPUs |
| GPU | NVIDIA GeForce RTX 4070 Laptop GPU，driver `610.62`，compute capability `8.9` |
| CUDA compiler | `nvcc` 不在 PATH；阶段 0 未构建或验证 CUDA |
| Nix build shell | CMake `3.31.7`，Ninja `1.13.1`，GCC `14.3.0`，uv `0.8.14` |
| Harness Python | Python `3.11.13` |
| Canonical timing unit | ns；fixture SDC 数值也按 ns 解释 |

系统 CMake 为 3.28.3、GCC 为 13.3.0、系统 PATH 无 Ninja；实际 native 配置/构建使用上表中的 Nix dev shell。

## 4. 分析结论

### 4.1 ECC 中现有 STA 生命周期

- `STAInterface::runSTA()` 执行 delay、建图、clock、timing、power、分析、报告和 SDF 的全量流水。
- `STAInterface::updateTiming()` 名称虽然包含 update，但当前仍会重建 timing graph 并执行全量 clock/timing propagation，不是论文意义的增量 STA。
- ECC 的 `run_timing` production wrapper 在一次运行后销毁 native STA 状态；当前没有可直接承载多轮结构 mutation 的通用持久 session。
- iCTS 的 `FastSTA` 是 clock-tree 专用能力，不覆盖论文所需的一般 pin/arc 插入、删除和 Dual-CSR 更新。
- 仓库中没有现成的通用、迭代式 timing-driven buffer insertion 消费者。后续需要新增确定性的 semantic greedy buffer insertion harness，再在更晚阶段接入真实物理事务。

### 4.2 重复 build 与 reset 风险

新增 `GraphBuilderStateTest.cpp` 证明：对于同一个未修改设计，连续两次 `GraphBuilder::build()` 后，arcs、双向 adjacency、start/end points、timing order 和 level 完全相等，没有静态 append。

这不等于 mutation reset 安全。现有代码仍可能在删除 pin 或改变 endpoint 角色后保留 stale `TimingPoint`/start-end 状态，`TimingAnalyzer` 的 path groups 也没有完整 reusable reset 证明。因此阶段 0 correctness oracle 强制每次 repetition 使用 fresh OS process；same-process 重跑只能是诊断项，不能替代 golden oracle。

## 5. 修改内容

### 5.1 Parent 仓库

- `docs/incregpusta/stage0-feature-support-matrix.md`
  - 冻结阶段 0、后续四模式、edit/fallback、full-graph propagation 和能力声明边界。
- `docs/incregpusta/stage0-report.md`
  - 本报告。

### 5.2 ecc-tools 子模块

- `.gitignore`
  - 新增根级 `/build-*`，避免所有阶段构建目录进入提交。
  - 将未锚定的 `test` 改为 `/test`，避免静默忽略 `src/operation/iSTA/test/**`。
- `.github/actions/build-wheel/action.yml`
  - 显式配置 `CMD_BUILD=ON`、`BUILD_TESTING=ON`。
  - 构建三个 native test/probe 目标，并以 CTest label 运行 `ista_unit` 与 `ista_smoke`。
- `src/operation/iSTA/test/CMakeLists.txt`
  - 要求 Python >= 3.11。
  - 增加 schema/controller、GraphBuilder state 和 full baseline 测试及 labels。
- `src/operation/iSTA/test/GraphBuilderStateTest.cpp`
  - 对未修改设计的重复 build 做完整图状态等价检查。
- `src/operation/iSTA/test/baseline/StaFullBaselineProbe.cpp`
  - 通过 production `dmInst` 输入链与 `STAInterface::initSTA/runSTA` 执行 full STA。
  - 在 `destroySTA()` 前导出稳定语义键、typed sentinel 和 correctness contract 所需的 native snapshot（含拓扑、时序、约束、库单位和 power 摘要）。
- `src/operation/iSTA/test/baseline/README.md`
  - 记录 harness 前置条件、operator 步骤、record/verify 边界和安全要求。
- `src/operation/iSTA/test/baseline/baseline_contract.py`
  - 严格 manifest/snapshot 契约、稳定 hash、数值容差比较和原子 JSON 写入。
- `src/operation/iSTA/test/baseline/baseline_artifacts.py`
  - 严格 `validate_golden`、结构化工件比较、文本 token 化和 SDF 数值容差比较。
- `src/operation/iSTA/test/baseline/run_baseline.py`
  - fresh-process orchestration、全部 case 验证后再发布 golden、生成路径 containment 门禁。
  - 在任何写入前只读检查 `TMPDIR/TEMP/TMP`；禁止 output/session/result/default temp 落入 checked-in golden。
- `src/operation/iSTA/test/baseline/manifest.json`
  - 冻结 case、输入 SHA、source baseline、topology、repetition、tolerance 与工件契约。
- `src/operation/iSTA/test/baseline/fixtures/**`
  - 两个 tiny gate-level case、最小 Liberty/LEF/SDC，无 SPEF、无外部 PDK。
- `src/operation/iSTA/test/baseline/golden/{chain,diamond}.json`
  - checked-in CPU/full golden，包含 snapshot、artifact contract 和 provenance。
- `src/operation/iSTA/benchmark/schema/incremental_sta_samples_v1.schema.json`
- `src/operation/iSTA/benchmark/schema/validate_incremental_sta_samples.py`
  - 冻结未来 benchmark v1 记录格式。
  - 拒绝零 edit 的 incremental 性能、fallback/baseline speedup、correctness 自相矛盾、反序统计、NaN/Inf、重复键和未知字段。

没有修改 production STA 算法、ECC Python timing wrapper 或用户配置接口。

## 6. 黄金基线

| Case | 实例/Pin/Arc | Topology SHA-256 | Config SHA-256 | Snapshot diagnostic SHA-256 | Worst slack / TNS |
|---|---:|---|---|---|---:|
| `chain` | 3 / 9 / 7 | `94c0754e0583a40f7ee61e7d44d306f62845d5899bc7109e757ed4549a8b5aa0` | `dfbd8ca5e2445a785f012659c842d68b790ea55227c75ec08282b3b2d4dd9228` | `6dd7f0d6d15cd34c22d12a0aebcb43e705423503c8f4251c38337956b6727059` | 0.078067576348279 / 0 |
| `diamond` | 4 / 12 / 11 | `da8b4d75814db8570c6da233759238849002c0d366bfadb60caf14f521b1d165` | `682fdea85fc8e65a7adecc16686da4d28c9dbe8362c27c0973ed85c1fe217f80` | `3d75bdec898f695574f116c0be660029e4f05a2a7a3afa7894f8b4a5a7e9a608` | 0.032953216374269 / 0 |

两个 case 均有 1 个 path group、2 条 timing path、0 个 violating/unconstrained endpoint。最终安全重录后 checked-in golden 字节哈希保持不变：

- `chain.json`: `a29b1afe4353f34da3c6bbfa6712d58650bd5e85b97884b2df735c18087c74f7`
- `diamond.json`: `dfed7bc52f3e5e985127eed3a1a6d76e91649f8704f50188d08a2f0b4b8fea16`

## 7. 正确性与测试结果

### 7.1 Native 配置与构建

~~~bash
cmake -S chipcompiler/thirdparty/ecc-tools \
  -B chipcompiler/thirdparty/ecc-tools/build-ista-stage0 -G Ninja \
  -DCMD_BUILD=ON -DBUILD_TESTING=ON -DCMAKE_BUILD_TYPE=Release \
  -DCOMPATIBILITY_MODE=ON \
  -DPython3_EXECUTABLE="$PWD/.venv/bin/python"

cmake --build chipcompiler/thirdparty/ecc-tools/build-ista-stage0 \
  --target ista_arc_timing_arc_delay_test \
           ista_graph_builder_state_test \
           ista_full_baseline_probe
~~~

构建通过。构建目录被 `/build-*` 忽略。

### 7.2 契约与 native 测试

| Gate | 结果 |
|---|---|
| Benchmark schema self-test | 54 checks passed |
| Baseline controller self-test | contract 15 + golden 9 + artifact 4 + path 6，全部通过 |
| Draft 2020-12 `check_schema` | 通过 |
| Ruff check / format-check | 通过 |
| CTest `ista_unit` | 4/4 passed |
| CTest `ista_smoke` | 1/1 passed；内部为 2 case × 3 fresh processes |
| Final local golden verify | 2 case × 5 fresh processes，全部通过 |
| ECC STA ownership pytest | 43 passed |
| ECC full pytest without external PDK | 1414 passed、8 skipped、4 deselected、13 xfailed |

最终本地验证命令：

~~~bash
ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-ista-stage0 \
  --no-tests=error --output-on-failure -L '^ista_unit$'

ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-ista-stage0 \
  --no-tests=error --output-on-failure -L '^ista_smoke$'

.venv/bin/python -m pytest \
  test/tools/ecc/test_module_timing.py \
  test/tools/ecc/test_sta_artifacts.py \
  test/tools/ecc/test_sta_qor.py \
  test/tools/ecc/test_runner.py -q

.venv/bin/python -m pytest test/ \
  --ignore=test/examples/test_soc.py -m "not pdk" -q
~~~

PDK integration tests不是 hermetic stage-0 gate，最终全回归以 `-m "not pdk"` 明确排除 4 项外部 PDK case。远端 CI 尚未运行。

## 8. Review 与修正循环

1. 初版详细计划经过三轮独立审查后批准。
2. 第一轮实现审查发现 missing golden、SDF 浮点精确 hash、manifest 输入集合不完整、schema 字段漂移/弱交叉约束、snapshot null、过大 controller 等问题。
3. 修正后拆分 controller/contract/artifact ownership，增加严格 snapshot/golden/schema 语义与负向测试。
4. 第二轮审查继续发现零 edit incremental 可声明 speedup、`pass=true` 可与 mismatch/超 tolerance 共存、统计量反序、golden provenance 未门禁、manifest semantics 未冻结、生成路径可进入 golden 等问题。
5. 修正后，聚焦复审又发现默认 `mkdtemp` 及 CPython `gettempdir()` 的写前探测风险；最终改为先只读解析并校验 temp 环境，再创建目录。
6. 两名未参与实现的审查者最终均给出 `APPROVE`，无 blocker、major 或 minor；其中一名使用原 false-green 样例逐项确认拒绝，并独立复跑 schema/controller/CTest/Ruff/diff gate。

任何一次审查或正确性测试失败后都先修正，再重新审查与测试；没有以 skip、mock GPU 或 compile-only 代替通过条件。

## 9. 性能与观测

阶段 0 不报告 incremental/GPU speedup。最终诊断 artifact：

~~~text
/home/shigure/code/ecc/chipcompiler/thirdparty/ecc-tools/
  build-ista-stage0/stage0-final-verify-result.json
~~~

该目录被 `/build-*` 忽略。结果记录两个 case 各 5 个 fresh processes、topology/config/snapshot hash 和 controller elapsed time。elapsed 只包含当前小 fixture 的 harness 诊断，不是 STA kernel benchmark，不得用于论文性能结论。

阶段 0 的实际执行是既有 CPU/full baseline：

- mutation batch：无；
- incremental batch：未执行；
- fallback：0；
- GPU：未执行；
- propagation：full graph；
- 性能 speedup：不适用。

typed requested/executed/fallback telemetry 要到阶段 1 才进入生产接口；本阶段不伪造该能力。

## 10. 已知限制

- 尚无 `IncrementalStaSession`、typed mode、CSR conversion、CPU incremental、GPU full/incremental 或 greedy buffer insertion。
- fixture 只覆盖组合 data path；尚未覆盖 sequential、SPEF/RC、propagated clock、多 corner、constraint mutation 和真实 PDK。
- static repeated build 已验证，但 reusable mutation/reset 仍不安全；oracle 必须保持 fresh process。
- RTX 4070 可见，但本环境没有 `nvcc`，没有 CUDA build、kernel correctness 或 GPU 性能结果。
- parent 与 ecc-tools 的阶段 0 commit 均只存在本地，远端 branch 可达性与远端 CI 尚未验证。
- stage-0 golden 是极小 correctness fixture，不代表真实设计性能或容量。

## 11. 阶段 1 入口门禁

阶段 1 应先分析当前公开 API、Python/Tcl boundary 和 session ownership，再提交详细计划与独立设计审查。最小目标是：

1. 引入 typed `backend/update_strategy/fallback_policy` 请求与实际执行记录；
2. 保持默认 `cpu/full` 行为和现有 artifact contract 不变；
3. 建立可显式创建/销毁但尚不执行增量算法的 session 生命周期骨架；
4. 为无 mutation 的 incremental 请求记录 `baseline_only`，不得生成 incremental speedup；
5. 使用本阶段 golden 对默认模式做差分回归；
6. 继续执行“分析 → 详细计划 → 独立审查 → 修改 → 独立复审 → 修正 → 正确性测试 → 阶段报告”的强制闭环。
