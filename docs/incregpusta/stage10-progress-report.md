# Stage 10 实施与验收报告

日期：2026-09-15。状态：**实现与功能验收完成**。xtea、usb、zipdiv 完成原 ICS55、post-synthesis、无 SPEF 输入下的四模式 baseline，以及 Q 负载、D 输入两组真实两批编辑验证。lint/type 的剩余失败如下单列，不宣称全仓检查通过。Stage 11 尚未实施。实现与验收于 2026-09-16 提交（ecc-tools 6921b6089），未 push；以下保留验收时的版本与历史记录。

## 支持范围

| 能力 | 当前支持与证据 |
|---|---|
| 顺序实例、顺序发射 | CPU reference 与 CUDA 独立计算 CK/Q、CTQ、当前 Q 负载；覆盖 rising/falling、缺表、不可达 clock 和 input/register winner |
| 时序检查 | setup/recovery required seed；发布实际传播值后由原 analyzer 计算 setup/hold/recovery/removal；D trace 验证 slew、required 随编辑变化 |
| CRPR | 保留 launch node/transition 身份；仅既有 ideal-clock contract，校正值为 0 |
| 时钟树扇出 | physical clock arrival/slew/predecessor 与 effective ideal-clock state 分开计算，保留 owner 绑定 |
| 条件时序弧 | 与 native 相同，保留全部带条件候选，按 trigger/sense/table/max/min 选择；不求值 sdf_condition |

propagated clock、clock gating/divider、case analysis、parasitic net 仍明确“不支持”。非零 propagated-clock CRPR、完整 native STA 对齐、EngineDB/IDB 与物理事务、closed-loop greedy、正式加速比均“未执行”，属于范围外或 Stage 11。full 与 incremental 仍执行全图 propagation。

## 构建与证据

本次续跑基于 ecc fc6379e303b0ecae1ccd8eaa22c0c0d655c547e5、ecc-tools 2d27eea7273250d60365a983712c69c38539c3ef 加当前未提交差异。WSL 是代码基准；同步后 6258 份代码/输入文件 SHA 全部一致，受保护的 README、CLAUDE.md、用户测试、报告与 overview 身份未变。

E 为 ecc-tools 下的 build-incregpusta-cuda-on/stage10-20260914-152556；R 为其下 resume-20260915-142734。服务器完整前缀是 /home/qianhan/code/ecc/chipcompiler/thirdparty/ecc-tools/，容器映射为 /home/shigure/code/ecc/chipcompiler/thirdparty/ecc-tools/。命令、日志、摘要和 SHA 清单已取回本地 [server-evidence](../../chipcompiler/thirdparty/ecc-tools/build-incregpusta-cuda-on/stage10-20260914-152556/resume-20260915-142734/server-evidence/)，大状态文件保留在服务器原位置；本地质量检查在 R 本身。

- 两套独立 Release：build-stage10-cuda-off-server 省略诊断选项且实际 OFF；build-stage10-cuda-on-server 显式 ON。GCC 14.3.0、CMake 3.31.7、nvcc 12.8.93/cudart 12.8.90、Python 3.11.13、CUDA arch 89；严格构建保留 -ffp-contract=off，依赖未升级。
- 冻结镜像 ecc-stage10:20260915-locked-v3，ID sha256:cac38c97fbca68a427800284886b218ad0d9db77e1e7142058ab980a7edbc193。高内存任务使用持久 tmux，容器共享 512000000000 字节内存上限、swap=0；最后两组 GPU 任务使用当时空闲的 GPU 5/6。
- binding 顺序构建、分离保存；测试核对实际模块路径及只读 CUDA/debug 状态。E/real-design-inputs.json 核对原 RTL/config、mapped.v、SDC、综合来源与 PDK；使用有序 H7CR/H7CL LEF/Liberty，显式 ss_1p08/125/__no_rc_corner__，未删寄存器、修改约束或抽取子电路。

## 三设计验收

| 设计 | OFF/ON 四模式 baseline | Q 负载两批 | D 输入两批 | 恢复后继续提交 |
|---|---|---|---|---|
| xtea | 通过 | 通过 | 通过 | 通过 |
| usb | 通过 | 通过 | 通过 | 通过 |
| zipdiv | 通过 | 通过 | 通过 | 通过 |

baseline 共 24 个构建/设计/模式组合，各独立进程内连续运行两次，公开 QOR、timing paths、执行记录一致。未编辑 incremental 请求明确为 baseline_only，不计增量成功。证据：R/public-baselines/matrix.json、comparisons.json。

每设计另有 Q 负载和 D 输入两个 frozen trace，各实际插入两批 buffer，generation 0→1→2。原 greedy 没有选到编辑时，复用已有 --create-trace 指定合法 data net/sink/buffer；--replay 严格解析实际编辑，不把 generation-only 投影当作正确性证明。Q trace 位于 E/real-traces/设计名/functional-q-load；D trace 位于 R/d-input-设计名。

| 验收 | 实际结果与 R 内证据 |
|---|---|
| ON CPU mixed | 每 prefix 对独立 fresh native CPU/full，拓扑、timing、winner、clock/CRPR、level 与实际模式通过；cpu-v2-*/results/run-*/controller-summary.json、d-cpu-*/results/run-*/controller-summary.json |
| ON CUDA incremental | 每 prefix 同时对 fresh native CPU/full、CUDA/full；所有请求批次实际 incremental，fallback=0；cuda-incremental-*/results/verdict.json、d-cuda-*/results/verdict.json |
| OFF 真实执行 | 相同 Q/D trace 完成 CPU mixed、CUDA full/mixed、实际回滚；off-cpu-verified.json，性能比较仍记 not_run |
| OFF/ON 与公开结果 | 原始完整设备状态 14 对一致；补充验收的 72 项公开 QOR/timing paths 对 fresh native CPU/full 逐字段一致，含适用检查值；public-real-validation/comparisons.json 共 126 项完整状态、public、恢复比较全部一致 |
| D 侧变化 | 实际 slew/required 随两批插入变化并与 fresh 一致；d-input-slew-required.json |

比较脚本为 R/compare-public-real.py；这些数量是实测记录，不是固定门禁。真实 rollback、source isolation、错误 canary 和逐 prefix level 合法性仍保留。

## 恢复与公开结果

CPU 真实设计测试调用既有 replayDualCsrModesForRecovery，在新 session 按保存模式恢复第一批并继续第二批；ON 覆盖 after-swap poison，OFF 不依赖故障注入。CUDA 销毁原 session、重新加载，在新设备 session 按保存模式重建第一批并继续第二批，完整 state/public 与首次执行一致。这里证明新 session 重建，不是原地修复损坏 CUDA context，也未新增生产 CUDA recover API；设备损坏和无设备拒绝由独立注册测试覆盖。

公开结果先 scatter 实际 CPU/CUDA committed timing，清除旧 path groups，再调用 analyzePropagatedTiming 和 TimingReporter；不会第二次 native propagation 替换被测值。报告配置临时启用后恢复，fresh oracle 保持独立 native 计算。

跨构建/恢复输出拒绝覆盖任何已存在路径，包括输入及 dangling symlink。完整 readback、临时 native 副本和 public 等价只在显式测试入口使用，未进入生产或性能路径；默认 CPU/full、诊断 OFF 不变。

## 回归与性能入口

| 检查 | 实际结果 | R 内证据 |
|---|---|---|
| native 严格构建与回归 | ON 188 个启用项完成；OFF 152 个启用项完成、28 个按配置禁用。首次缺程序的 ON 18/OFF 12 项补建后全部通过 | build-native-tests.log、ctest-{on,off}.xml、ctest-{on,off}-missing.xml |
| 最后修改的 native 消费者 | 两构建重新严格编译；ON 7 项、OFF 5 个启用项通过，OFF 2 项禁用 | final-native-v2/ |
| CUDA memcheck/initcheck | OFF/ON × mixed/fallback，以及顺序 trace、恢复继续提交，共 12 次均 0 错误；故意设备错误另跑 | *-{memcheck,initcheck}-{mixed,fallback}.log、final-native-v2/*check-sequential.log |
| binding/no-device 与 parent | 两套绑定及独立无设备拒绝通过；parent test/tools/ecc 各 368 项通过 | remaining-checks.json、parent-{off,on}.xml |
| OFF 性能 / ON 拒绝 | OFF 仅 build-info、预热、目标样本，无 oracle/完整 receipt；ON 仅 build-info 后采样前拒绝 | performance-audit.json 保存实际子进程和原始样本 |
| 实际调用剖析 | OFF/ON CUDA 两批均未调用 native/CPU reference propagation；CPU/full 阳性对照命中 8 次。receipt serializer ON 命中 2 次、OFF 0 次 | call-profile-v2-{off,on,cpu-control}.{json,log} |

性能 smoke 只证明入口行为，不形成正式加速比。调用数来自断点实测，不是固定返回值或源码字符串证明。

## 失败、修复与质量检查

| 失败或发现 | 根因与处理 |
|---|---|
| xtea canonical projection 的 output_load 差异 | native 按 pin 全名排序去重后累加，validator 错用 canonical arc rank；修复共享 load 校验并加非结合浮点 literal 用例 |
| CPU winner 差分拒绝 physical clock | 旧 checker 假定 clock root 必须孤立；区分 physical/effective，保留 CRPR/source/tag/start 校验和 mutation canary |
| 新增 6 条 Pyright 诊断 | 修正已验证 JSON 边界类型、布尔错误列表等，最终新增诊断为 0 |
| 跨构建输出可能覆盖输入（审查发现） | 输出创建前拒绝任何已存在路径；OFF/ON 同输入及 dangling symlink 测试均明确拒绝 |
| 新恢复测试严格构建失败 | 补全 makeTraceBaseline 命名空间，两构建复验通过 |
| 报告 feature 默认关闭（审查发现） | 测试局部启用并 RAII 恢复；先清空 analyzer 旧 path groups，防止旧结果累积 |
| fresh 顺序 replay 报 raw.net.reset_n | 独立 oracle 的预期缓存缺 native 排序；仅修正预期 driver/load 顺序并加 literal 断言，实际观察/比较未放宽；wrong-sink canary 与三设计 fresh 均通过 |
| native 首轮缺少程序 | 初次单列未执行，补建后分别复跑，不把 skip 计通过 |
| 验收脚本/工具启动失败 | 保留 PowerShell 替换转义和 CTest 缺 command 的失败；修正后成功。服务器 Pyright 缺 Node，WSL 递归扫描误纳入 build 后被终止，改用 Git 受控源文件清单重跑 |

修改的 23 份 Python 文件：Ruff 41 条、HEAD 对照 47 条；Pyright 最终 199 个错误，新增诊断均为 0。Ruff format 仍有 15 份既有格式差异，未做无关批量格式化。R/ruff-*.json、pyright-*.json 保存结果和空的新诊断清单；lint/type 不能写“全通过”。

parent 全部 288 份 Git 受控 Python 源文件实际 Pyright 为 **836 errors、6 warnings**，保存 R/parent-pyright-sources.json 及命令；未证明全部是旧问题，也未扩展修复无关 Python 模块。两仓 diff --check 通过，528 份用户/受保护文件、6258 份已验收源文件身份均无变化，文档链接有效；结果保存在 R/final-workspace-checks.json。

独立 stage10_code_review 审查完整 native/CUDA 差异及后续 public/recovery/oracle 修正，复查 APPROVE，无剩余 blocker/major；stage10_design_review 已审查设计、Python/schema/CMake 和验收补充；最终五份文档与验收证据核对为 APPROVE，无剩余 blocker，记录于 R/final-independent-acceptance-review.json。

## 历史分组记录（2026-09-14）

以下保留当时记录和失败现场，其中“尚未完成/尚未验收”是当时状态；当前结论以上面的 2026-09-15 验收为准。

日期：2026-09-14。正在按 [详细计划](stage10-detailed-plan.md) 实施六类语义及三设计四模式验证。当前已接通六类语义的共享 CPU/CUDA 计算，并通过一个顺序小设计的独立 native CPU/full 与 CUDA/full 比较。三个 CI 设计、真实增量批次及 OFF/ON 验收仍未完成，不能将本报告解读为 Stage 10 验收通过。

## 工作区与证据

本轮开始的两仓 HEAD、原始 dirty patch 和文件身份保存于 ecc-tools `build-incregpusta-cuda-on/stage10-20260914-152556/starting-state.json`、`ecc-starting.patch`、`ecc-tools-starting.patch`。全部构建/运行日志均位于这个新的证据目录，没有覆盖此前 CUDA CI 证据。

过程中按用户单独的 commit 指令，将此前六份 Stage 9 状态/验收文档提交为 ecc `fc6379e`；本轮 Stage 10 代码与新文档继续保留工作区差异，没有 push。通用 README、用户 CLAUDE.md、独立报告与 overview 均保留。

## 已实施的内部 CPU 计算

- 共享 payload view 直接访问已有 raw nodes、referenced library cells、clock owners 与 timing-check endpoints，没有另存完整 graph。
- physical clock slew/delay 与 arrival 按 native 的 clock、FIFO、analysis 和 transition 顺序运行；effective ideal-clock seed 保持独立。复用现有 dynamic arc evaluator、单位与舍入规则。
- 将结构性顺序种子迁移为 `kDeferredSequential` / `DEFERRED_SEQUENTIAL` / `deferred_sequential`；native、Python model/recompute 与测试同步，不保留旧名别名。
- CK/Q 在 clock pass 后计算，首个 CTQ trigger、当前 Q net load、缺弧零延迟、缺表 fallback、scalar-only 未可达 clock 与 register path/CRPR 身份均保留。standalone Q 计算不修改 graph arc cache。
- scalar required 保持 input path 优先、其次 register；先选各 transition 的 tag winner，再选 transition winner，保留 epsilon。首个 setup/recovery check 即使缺少当前 transition 也不尝试后续 check；check table 两轴均按时间换算，不按 capacitance 取整，也不按 child trigger 过滤。
- 最终路径物化保留 CRPR node/transition；结果 shape 接受真实 physical clock 值和 predecessor。六类 unsupported 推导已迁移；propagated clock、clock gating/divider、case analysis 与 parasitic net 的拒绝继续保留。公开入口现已通过下述顺序小设计独立 native 对照，尚未取得三设计及真实增量验收。

## 独立审查与已执行验证

详细设计由 `stage10_design_review` 独立只读审查，结论 APPROVE。另一位 `stage10_code_review` 逐组审查 clock、sequential seed、timing checks / final result，内部 CPU 组及随后 CUDA clock、sequential/check、真实设备 contract、支持/结果校验/小设计 baseline 各组均完成只读审查与复查。第七组结论 APPROVE，无剩余 blocker/major；这些结论不覆盖尚未完成的三个 CI 设计与真实增量批次。

使用现有 GCC 14.3、Release、debug-check ON、相同 Nix 依赖，未升级依赖。命令从 ECC 根执行 bare `nix develop --command`，原生目标经 CMake 的严格警告和 `-ffp-contract=off` 编译。

| 组 | 实际结果 | 原始日志 |
|---|---|---|
| CPU clock | 严格构建；初次 numeric contract 失败，修复测试后复验 2/2 | `cpu-clock-build.log`、`cpu-clock-test.log`、`cpu-clock-retest.log` |
| clock 审查建议 | 改比实际 path_rows，溢出场景使用独立 work；严格构建和 2/2 | `cpu-clock-review-retest.log` |
| sequential seeds | 严格构建；CK/Q、falling trigger、负载重算、无可达 clock 的定向 contract 2/2 | `cpu-sequential-build.log`、`cpu-sequential-test.log` |
| timing checks | 严格构建；lookup、CPU reference、generic view 三项 contract 3/3 | `cpu-check-build.log`、`cpu-check-test.log` |
| 最终 clock/register 结果 | 严格构建；forward/backward/物化保留 physical predecessor 与 CRPR，三项 contract 3/3 | `cpu-result-build.log`、`cpu-result-test.log` |

初次 clock numeric contract 未触发溢出的原因是测试修改了 raw arc 后仍使用先前构造的 FlatCsrEdgeView；该 view 已保存旧 payload。重新构造 view 后溢出正确返回 numeric failure。首次失败日志保留。一次自动接线脚本对 CMake 源路径的格式断言失败，核对实际 `${CMAKE_CURRENT_SOURCE_DIR}` 格式后补入新文件，再执行上述严格构建。

已补齐“timing check 的 clock node 不同于 instance 主 CK”行为用例，使用独立的 period/arrival/slew 区分两者，且首个主 CK check 按 native 选择规则设为 Setup。该内部边界用例通过；完整多时钟真实设计验收不在当前证据中。

## CUDA 计算与公开结果迁移

- NodeState 保存 device physical clock 及 raw effective seed，PathState 保存 CRPR；full/mixed 共用设备 clock、sequential seed、data 和 required pass，解包读取实际下载结果。
- CTQ/check 只打包原始表与角色，追加到现有 child/table 池；graph arc 的 ranges 保持独立，targeted append 基于完整池 offset，Q 每批在设备读取当前 net load。没有 CPU timing shadow，没有新增独立所有权或策略框架。
- 结果 validator 按实际 clock owner 检查 effective ideal-clock state；physical state 保留源 lane 存在性、数值、owner、合法 input/output lane 与前驱 arrival 递推。clock-only net 的 graph-cache mask 同时追踪 physical slew 和 data slew 的实际 presence。
- deferred seed 不再解引用不存在的预计算 arrival/slew；仍验证唯一 root、CRPR 身份、ideal launch 和实际路径存在。CTQ 数值由独立 fresh native 比较证明，validator 不重跑 CTQ/传播。
- 删除六类语义的旧拒绝专用测试，保留剩余 unsupported 运行前置检查、malformed、clock owner/波形/身份边界。诊断 token `deferred_sequential` 的 Python 消费者及 exact reason 推导已同步。

## 本组实际失败与修复

| 场景 | 实际失败及修复 | 证据 |
|---|---|---|
| CUDA clock owner | 新设备用例证明错误 owner 被静默跳过；改为 invariant，健康重跑成功，相关 4/4 | `cuda-clock-conflict-before-fix-test.log`、`cuda-clock-conflict-after-fix-test.log` |
| CUDA sequential/check 接线 | 严格构建及原有 5/5 | `cuda-sequential-build.log`、`cuda-sequential-test.log` |
| CUDA 设备独立 literal contract | 初次 0/2，fixture 将 negative-unate 编码 2 误写为 non-unate；修正为 3，补齐 CK 存在但不可达分支后 2/2 | `cuda-sequential-contract-test.log`、`cuda-sequential-contract-retest.log` |
| 顺序设计发布 | 首两轮 `shape_mismatch`；修复孤立时钟/预计算 seed 旧约束，再由失败字段确认 clock-only net cache mask 遗漏。第三轮完整比较通过 | `sequential-baseline-first/`、`sequential-baseline-second/`、`sequential-baseline-trace/`、`sequential-baseline-third/verdict.json` |
| physical 前驱 transition | 审查发现相同数值的 rise/fall 可掩盖错误前驱；实际计算结果 mutation 在修复前被错误接受，补初始化 lane 绑定后被拒绝。同时覆盖清空 physical state | `physical-transition-before-fix-test.log`、`support-validator-clean-test.log` |
| 旧支持测试迁移 | 成组回归先 8/10、后 9/10，失败是已淘汰 conditional/fanout 拒绝及旧 unsupported fixture；删除专用否定断言，前置拒绝测试改用 propagated clock，最终 10/10 | `support-validator-test.log`、`support-validator-final-test.log`、`support-validator-clean-test.log` |

临时 scatter violation 输出仅用于定位失败，采集完成后已移除。辅助测试迁移脚本曾因预期一个调用点但实际有两个而在写入前中止；核对两处用途后分别完成迁移，没有通过跳过检查处理失败。构建目标清单第一次在普通 WSL 环境调用不存在的 Ninja 后改为读取现有 build.ninja，实际构建仍统一在既有 Nix shell 中执行。

## 独立顺序小设计证据

新增测试输入 `baseline/fixtures/sequential.{v,sdc,lib}` 与 `sequential_cells.lef`，原 Stage 0 输入和 golden 不变。设计实际含 8 个实例、27 个 timing point：时钟缓冲/分支、上升及下降沿触发器、input/register 竞争路径、reset 检查与两条条件 CTQ candidate。

复用已有 `run_cuda_baseline.py` 和 native probe，每个 CUDA fresh 进程对独立 native CPU/full 比较完整 snapshot 及 QOR、timing paths、power、SDF；chain、diamond、sequential 均各完成两次 CUDA 对照。运行输出确认 setup、hold、recovery、removal 四类检查、rise/fall register CRPR 身份、非零 physical clock buffer delay、ideal effective clock/CRPR=0，以及 RN/!RN 两个条件候选。该结果是 full baseline 证据，不是增量批次成功。

最后一组严格构建和 10/10 CTest 包含 public input/result validator、support/export、CPU/CUDA contract、targeted/mixed session 与上述 independent native baseline。更广 CSR 消费者严格构建完成，首轮 70/73；三项失败分别为旧 clock unsupported fixture、conditional wire 元数据及缺失 PYTHONHOME。修复后 3/3，通过记录覆盖该组全部 73 项。原始日志 `csr-consumer-build.log`、`csr-consumer-test.log`、`csr-consumer-fix-test.log` 保留。conditional wire 仅迁移已支持原因及绑定 identity，raw 输入、graph/library/timing 未变，前后 SHA 记录在 `conditional-wire-migration.json`。

## 代码质量与未取得的证据

本轮 Python lint 最初发现新增行长错误，已用现有 Ruff 修复。另两条 UP035/FBT003 及该文件的格式差异来自 `dual_csr_reference_model_validator.py` 既有内容，已用 HEAD 内容通过 stdin 重跑确认；完整修改文件 lint 尚不能宣称通过。证据为 `python-ruff-check.log`、`python-ruff-format-check.log`、`python-ruff-existing-baseline.log`。没有升级工具或依赖。

尚未完成：三设计四模式 baseline 与真实多批 frozen trace、OFF 独立构建及 OFF/ON 跨构建等价、CUDA 内存检查、涉及新语义的故障恢复与继续提交、性能入口及无 CPU shadow 剖析、相关 parent/native 全回归与 lint/type、最终完整独立审查和文档同步。没有把 baseline 或定向测试计为真实增量验收通过。


## 真实工艺多文件输入（第八组）

原 trace 类型只能表达一份 cell LEF/Liberty，无法完整重放三设计的 H7CR/H7CL 工艺。已将 `SourceArtifactRefs` 与测试 loader 的 `FreshBaselineArtifacts` 改为有序非空列表和现有 `StaAnalysisContext`。加载不排序/去重，拒绝重复 canonical 路径；每份文件使用 ordinal 加 basename 的独立证据，支持不同目录同名文件。targeted/fresh 只共享机械文件展开，实际计算仍独立。

真实 frozen trace 升为 v2，JSON、canonical identity、注册 schema 和四份现有 trace/template 已同步。Stage 5/6 process/verdict、OFF 性能协议及 Stage 0 goldens 不变。real JSON 强制完整 context；CLI 允许重复 cell LEF/Liberty，任一显式 context 参数要求三项同时完整，否则沿用现有测试 slow/25 默认。三设计本轮明确使用 ss_1p08/125/__no_rc_corner__，与旧 CI 报告未显式指定 context 的 direct/unspecified 区分。

独立设计复核 APPROVE。独立代码审查最初指出 JSON 超过 700 行、first-empty 名称消费者遗漏；现已将 artifact 成对编码移入局部实现文件并迁移消费者。新增两文件完整 roundtrip、顺序/context 身份变化、空列表/重复路径/缺失 context 行为测试。审查复核 APPROVE（限定本组），真实设计结果仍待验收。

严格构建首轮因 CLI 参数遮蔽失败，修复后又发现旧 CUDA device comparator 仍读取已淘汰的 check_present，已改为完整 check table 比较并补 clock_eligible；第三轮构建通过。20 项受影响 CTest 全部通过，包括 schema、source isolation、first/terminal empty、fresh oracle、实际回滚以及 CUDA full/targeted/mixed 和 Stage 6 冻结差分。证据 `multisource-build-first.log`、`multisource-build-second.log`、`multisource-build-third.log`、`multisource-test-first.log`。修改的 source isolation/controller lint 通过。

Python 类型检查两模块共 14 条错误已由 HEAD 原始模块逐条复现，保存 `python-pyright-existing-baseline.log`，本轮未增加该组类型错误；全仓类型检查仍未完成，不能宣称通过。

三设计原始 RTL/config/综合网表/SDC/综合来源及 5 份 PDK 文件的 SHA 均与旧 CI 记录一致，保存 `real-design-inputs.json`。xtea 首轮参数误用 seed=42，在加载前被 real seed=0 契约拒绝；修正后的第二轮完成原双库 native 加载，但因没有被选择的编辑返回 empty_accepted_batch，尚无增量成功证据。两个尝试目录与日志全部保留，正在分析 data-only 编辑适用性及真实 trace 的构造条件。

## 功能 trace 与真实设计增量接线（第九组，进行中）

三个设计的原 greedy 选择流程均返回 empty_accepted_batch，不是算法 unsupported。Stage 10 的功能验证不要求改善 greedy gain：独立审查同意复用已有 --create-trace 与独立 semantic replayer，显式选择合法 data net/sink/buffer，实际执行两批，再把已有编辑及 generation 投影为 ReplayProgram。保留完整 artifact 的原校验入口，另以 --replay 接受严格解析的功能输入；不伪造 generation-only 选择凭据，也不修改原输入和约束。

xtea 原网表 x_0_（寄存器 Q）到 x_0__OAI21X0P5H7L_B0:B0 使用 BUFX1H7L/A/Y，独立 native CPU/full 已实际完成两批插入，generation 0→1→2。证据 real-traces/xtea/functional-q-load/native-trace.json、projection.json 及同目录命令和日志。该结果尚不构成 CUDA 或共享 CSR incremental 通过。

开放 buffer 选择后，独立审查发现旧校验只看方向和 positive-unate 弧，OR2 被错误接受。真实 CLI 修复前 exit=0 并写出 trace，保存 non-buffer-before-fix/；独立 replayer 自身补齐二端口及 identity function 限制，不依赖生产 buffer validator。第一次构建遇到原库非 const getter，改读局部副本；CTest 沿用原 ISTA_TEST_PYTHON_EXECUTABLE。修复后严格构建及正确 BUF、derived tamper rollback、OR2 拒绝 3/3，日志 ctq-projection-rebuild.log、non-buffer-after-fix-test.log。该段独立代码审查 APPROVE。

xtea 第一轮三路径 fresh CPU/CUDA full/CUDA incremental 均失败：两条在 diagnostic canonical projection，incremental 在既有 CTQ payload 刷新时被 blanket clock arc 拒绝。已限定允许同实例 CTQ 的已有 payload 更新并保留 clock-network 编辑拒绝，第二轮三条路径都进入投影，但同样报 reference_payload.arcs.output_load。原始两轮日志分别保存在 first-replay-attempt/、second-replay-attempt/。三条路径均未计为成功；正在排查 canonical projection 用 ArcKey 顺序重建 native rank 后改变负载累加顺序的问题。

一次第二轮命令启动误用系统 Python 3.12 搭配嵌入式 Python 3.11 的 PYTHONHOME，在任何设计采样前因 encodings 缺失退出；改用既有 ECC .venv Python 后完成上述三个子进程。未升级或更改运行时依赖。
