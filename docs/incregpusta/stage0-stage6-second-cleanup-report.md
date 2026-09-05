# Stage 0–6 第二轮复杂度清理

状态：完成，2026-09-05。基线：ecc `ab27ca9`，ecc-tools `8eed90e86`；两者分支均为 `IncreGPUSTA`。按用户要求仅本地 commit、不 push：ecc-tools 提交为 `c40b57b5086acddb118e0107928c82ea21084eb3`；parent 由本报告所在提交承载，并更新 gitlink 指向该 child 提交。这是未发布的本地工作，不宣称远端可获取。

## 审查范围

检查 ecc `f783db8..ab27ca9` 和 ecc-tools `31ebf6cae..8eed90e86` 的阶段提交、累计变更清单、计划/报告及选定实现的实际调用链。父仓库累计 49 个变更文件，子仓库累计 688 个，包含 fixture、schema、测试与文档；这些是范围清单，不表示对每个文件逐行穷尽审查。

按生命周期、快照、CSR/reference、edit/replay、Dual-CSR、mixed levelization 分层寻找可删除的内部重复。符号扫描仅产生候选，删除前检查真实调用与测试；未以出现次数少或文件长为删除依据。本轮由当前 agent 按 `docs/review-guidelines.md` 复核，没有独立 subagent 审查，也没有重做 Stage 0–6 的完整阶段验收。

## 已实施的发现

以下行号为清理后的实现位置，删除项以所属模块标识。

- `chipcompiler/tools/ecc/sta_signoff.py:L139`: shrink: 删除单次中间转换的 `StaSignoffSourceItem` 和 source collector，合并为直接构建最终 immutable `StaSignoffRunItem` tuple 的预检。config 路径只解析一次，每对 corner 的 context 只规范化一次；非空输入约束保证至少一项，不再维护末端不可达的空结果分支。净减少 62 行。
- `LevelizationExecutionTrace.cpp:L15` / `MixedLevelizationTelemetry.hpp:L13`: shrink: 两份确定性字段、手工逐字段投影及两套计数恒等式合并为 mixed 模块拥有的 `MixedLevelizationDeterministicTrace`。运行遥测继承确定性计数；transaction 保持同名类型别名并只复制基类，复用 `validateMixedTelemetryIdentities()`。transaction 仍单独检查完成度、frontier、classifier 与 fallback 约束。
- `CpuIncrementalLevelizationPipeline.hpp`: yagni: 删除无状态静态类与自由函数之间的转发，生产和测试统一调用现有 `runCpuIncrementalLevelization()`。算法、失败分类及输出类型不变。
- `dual_csr_typed_json_validator.py:L189`: delete/shrink: 删除无调用的 optional、snapshot、instance、parasitics、generic-record 辅助函数及只由自测使用的 library/lane 副本。reference replacement chain 和原 library/temperature 正负例直接调用实际 `validate_reference_value()`；没有删除这些功能用例。
- `dual_csr_trace_controller.py` / `real_differential_wire_contract.py`: delete: 删除无调用的 `require_count` 与 `schema_ref`。

合计修改 14 个代码/测试文件：90 行新增、384 行删除，**net: -294 lines**。文档及用户原有修改不计入此数字。新增的 13 行原生检查放在现有 transaction test，证明耗时与 `legal_noncompact` 不进入确定性投影，确定性计数变化仍改变投影并受校验。

## 保留的行为与边界

- signoff 保留所有配置类型、文件存在性、重复 corner/pair、sanitize 碰撞、report/feature alias、max_paths 和 SPEF/context 检查；全部预检成功才返回运行项，过程不创建 artifact 或 engine。合并后共同输入（如 SDC）的检查提前，因此多个 raw 输入同时无效时，首个错误的报告顺序可能变化；raw 错误仍优先于 capability 或执行副作用。
- Stage 6 JSON 字段与确定性恢复等价不变。没有将耗时或 fresh-oracle observation 纳入 committed state，也没有把功能比较改成 hash 比较。native 内部类型调整已重编译相关消费者。
- Stage 0/1 的 baseline、独占生命周期、异常清理，Stage 2 的 snapshot identity、native/scatter 边界，Stage 3/4 的 candidate rollback、source isolation 和 fresh oracle，均保留。
- 保留 full CPU oracle、Dual-CSR descriptor/index 绑定、mixed old-level 顺序与 actual-cycle 分类、full propagation 和显式拒绝 unsupported mode。没有新增依赖、CUDA、affected-cone、物理提交或 speedup 结论。

## 验证结果

| 验证 | 结果 |
|---|---|
| ECC tools 与 CLI params | 495 passed |
| parent non-PDK 回归 | 1665 passed、8 skipped、4 deselected、13 xfailed；2 个既有第三方 deprecation warning |
| 补回显式类型收窄后的 signoff/runner snapshot 相关测试 | 30 passed |
| GCC 14.3.0 / Release 原生构建 | 13 个 Stage 5/6 相关目标及 3 个生命周期目标通过 |
| Stage 5/6 联合功能标签 | 25/25 passed，含 real/synthetic fresh differential、mode recovery、active payload 与 Release timing smoke |
| Stage 0–4 focused 兼容与 real-differential | 67/67 passed，真实 fresh-process differential 约 97.5 秒 |
| parent Ruff check/format、scoped ty | PASS |
| 三个修改的 native-test Python 文件 | 实质 Ruff 检查 PASS |
| 两仓库 git diff --check | PASS |

原生两组共 92 项，无失败、未运行或跳过。timing smoke 只确认采样可执行，和其他回归并行运行，不作为性能比较证据。

所有命令从 `/home/shigure/code` 或其真实仓库子目录运行。主要复跑命令：

```bash
cd /home/shigure/code/ecc
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider test/tools/ecc test/cli/params -q
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider test/ --ignore=test/examples/test_soc.py -m "not pdk" -q
.venv/bin/ty check chipcompiler/tools/ecc/sta_signoff.py
.venv/bin/ruff check chipcompiler/tools/ecc/sta_signoff.py
.venv/bin/ruff format --check chipcompiler/tools/ecc/sta_signoff.py
nix --extra-experimental-features nix-command --extra-experimental-features flakes develop --command cmake -S chipcompiler/thirdparty/ecc-tools -B chipcompiler/thirdparty/ecc-tools/build-ista-stage34
nix --extra-experimental-features nix-command --extra-experimental-features flakes develop --command cmake --build chipcompiler/thirdparty/ecc-tools/build-ista-stage34 --target ista_mixed_id_mapping_test ista_mixed_graph_builder_test ista_corrected_mixed_kahn_test ista_mixed_reconstruction_test ista_incremental_levelization_pipeline_test ista_incremental_levelization_property_test ista_timing_dual_csr_transaction_test ista_dual_csr_production_fresh_probe ista_stage6_production_fresh_probe ista_stage6_mode_recovery_replay_test ista_stage6_active_payload_microcase_test ista_stage6_functional_receipt_test ista_csr_external_level_backend_test ista_execution_contract_test ista_lifecycle_guard_test ista_production_lifecycle_test -j 4
nix --extra-experimental-features nix-command --extra-experimental-features flakes develop --command ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-ista-stage34 -L 'ista_dual_csr|ista_timing_dual_csr|ista_timing_incremental_levelization' --output-on-failure -j 2
nix --extra-experimental-features nix-command --extra-experimental-features flakes develop --command ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-ista-stage34 -R '^ista_(full_baseline|execution_contract|lifecycle_guard|incremental_session|production_lifecycle|timing_edit_|buffer_|csr_real_differential)' --output-on-failure -j 2
```

最初尝试的 `build-ista-stage6-external-ninja-gcc14` 仅有缓存、缺少 build.ninja；最终复用实际承载上一轮测试的 `build-ista-stage34`，重新 configure 并构建当前源码。Nix 通过命令参数启用既需的 experimental features，不修改用户配置或依赖锁文件。类型检查曾发现合并流程丢失显式 Optional 收窄，已恢复原边界 guard 并通过复查。

## 文档与工作区

同步更新总实施计划、Stage 2 Step 7 计划及报告、Stage 5 报告、Stage 6 计划及报告。阶段说明仅维护在 IncreGPUSTA 专用文档中；已撤回本轮对 native iSTA README 的补充，仓库原有 README 保持不变。当前接口、数据归属与清理边界以这些补充为准；历史提交和历史验收记录保留。

保留用户原有 `CLAUDE.md` 修改和三份未跟踪报告，未改动 ecc-dreamplace 或依赖，未重写 Git 历史。总计划已移至 ECC 仓库内的 [incregpusta-implementation-plan.md](../incregpusta-implementation-plan.md)，旧位置不保留重复副本，相关链接已更新。未运行新的 GPU/PDK/ASan/UBSan 全矩阵；本轮结论限于上述实际构建、功能回归与代码复核。

本地提交时的 ecc-tools remote/upstream：`origin`：`https://github.com/openecos-projects/ecc-tools.git`；`IncreGPUSTA` upstream：`未配置`。遵照用户“不 push”要求，没有进行网络发布。
