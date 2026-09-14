# CPU 增量测试记录（2026-09-14）

本轮仅测试并记录结果，没有修改算法、通用 README 或用户已有文档改动，没有 commit/push。

## 结论

CPU targeted Dual-CSR 更新和 mixed levelization 在已有支持范围内的 fixture 上通过；timing propagation 仍为 full graph，不代表已实现局部 timing 传播。

此前选取的 ecc-ci-designs 门级输入 xtea、usb、zipdiv 均不能作为当前 Stage 6 CPU mixed 的成功案例：native 支持观察明确为 `reference_supported=false`。三者本轮只完成 native baseline 初始化，记录为 `baseline_only`、`incremental_batch_executed=false`，没有执行编辑批次、没有 CI 设计的 fresh 差分，也不报告增量性能。

## 环境与输入

使用既有独立 `build-incregpusta-cuda-off` / `build-incregpusta-cuda-on`，均为 Release、GNU 14.3.0、相同 Nix 依赖；本轮工作负载选择 CPU。重新构建该标签涉及的 native target、Stage 6 probe，并重新链接 ON `ecc_py` 后复测。

复用 2026-09-09 的综合网表、原始 SDC，以及 icsprout55 PDK 的 H7CR/H7CL 两组 LEF/Liberty；无 SPEF，NoParasitic。未重综合或修改 CI 输入。输入来源详见 `ci-design-smoke-report.md`。

| CI 设计 | native 节点 | 弧 | baseline levels | 实际增量批次 |
|---|---:|---:|---:|---:|
| xtea | 530 | 411 | 10 | 0 |
| usb | 3182 | 4368 | 16 | 0 |
| zipdiv | 4516 | 6501 | 30 | 0 |

三者均返回同一组不支持原因：`sequential_instance`、`sequential_launch`、`timing_check`、`crpr`、`clock_tree_fanout`、`conditional_timing_arc`。Stage 6 使用的 `ProductionFreshSessionLoader` 要求受支持的 generation-zero CSR reference；因此没有绕过入口限制生成编辑 trace。

## 实际执行的验证

- `ctest -L ista_incremental_levelization --output-on-failure`：OFF 9 项通过，6 项诊断测试按配置禁用；ON 15 项通过。重建相关 target 后再次执行，结果相同。
- ON `synthetic_two_batch.json`：逐 prefix 1/2 执行 CPU mixed，和独立 fresh 进程比较 topology/reference、timing/winner 等价及 level 合法性。均通过；没有 fallback，受控批次没有调用 full levelizer。
- ON `real_buffer_fanout.json`：真实门级组合逻辑 fixture（不是 ecc-ci-designs），1 批；同样通过独立 fresh 对照。
- `ista_stage6_mode_recovery_replay_test`：OFF/ON 均通过。覆盖连续批次、full/mixed 按模式恢复、stale descriptor 拒绝、恢复后继续提交；ON 另覆盖注入失败/poison 路径。通过 `--runtime-output` 导出，两构建的 `before_recovery`、`after_two_batch_replay`、`after_continuation` 与 generation JSON 完全一致。
- OFF `ista_stage6_release_timing_smoke`：1 次预热、6 个原始样本，每次为 CPU mixed 两批、最终 generation=2、fallback=0，实际 native rollback 完成。输出 `debug_checks_enabled=false`、`correctness_comparison=not_run`。这是小 fixture 的执行 smoke，不作 CI 设计性能或加速比结论。

## 初测复现的接口问题（历史记录，修复见下文）

三个 CI 输入通过 Python `ECCToolsModule.run_timing(cpu/incremental)` 均抛出 `StaExecutionContractError: native initial snapshot observation violates the capture contract`，不能报告通过。初次使用此前复制的 binding，随后重新链接当前 `ecc_py` 并复制至本轮独立 Python package 后复测，问题仍存在。

直接调用 native session 的相同 baseline 后，可读取 ready/generation=0 快照。相同 direct analysis context 的 native corner fingerprint 为 `762ed637a7b3f10653e1212cf54480f9d8b319108418663f301a9b45b5e97dcf`，Python `corner_fingerprint()` 为 `9e0c49b01171ddde3bf24e9ae4ebdfa92fdcc22ba4f4dcba65aff23eb1060caa`，这触发 Python 捕获契约检查。尚未修改或最终定位产生不同 payload 的原因。此问题与上述不支持 CSR reference 的限制分别记录；即使修复 fingerprint 契约，也不能据此宣称支持这些时序设计的 mixed 更新。

## 证据位置

所有本轮脚本、完整日志、原始快照、JUnit、controller 输出与 summary 位于：

`chipcompiler/thirdparty/ecc-tools/build-incregpusta-cuda-on/cpu-incremental-tests-20260914/`

- `summary.json`：版本、CI 状态与测试摘要。
- `off-ctest.xml` / `on-ctest.xml`、对应 `.log` 和 `*-build-tests.log`。
- `stage6-real/` / `stage6-synthetic/`：逐 prefix targeted/fresh 原始 JSON、stdout/stderr 和 controller verdict。
- `off-recovery.json` / `on-recovery.json`、对应日志。
- `off-timing-smoke.json` / `off-performance.log`。
- `rebuilt/*-on/result.json`：当前 binding 的 Python 失败；`rebuilt/*-native-on/result.json`：native 执行记录及不支持原因。
- `check_ci_eligibility.py` / `check_native_eligibility.py` 及 `rebuilt/` 版本是测试辅助脚本，明确只检查 baseline 资格，不是增量实现。

本轮未运行全仓 lint/type check 或全部 parent 回归，未修改生产代码；不将本轮结果扩展为 Stage 0–9 的全面验收。


## 2026-09-14 corner fingerprint 修复与复测

根因已定位并修复：Python 原先以通用 `analysis-context` payload 计算 corner fingerprint；native 生产 `cornerPayload()` 使用 `reference-corner-payload` domain/schema，另编码一个 empty marker。对 direct context，旧 Python 值为 `9e0c49...`，生产值为 `762ed637...`。该问题也能在受支持的 chain fixture 复现，与 CI 设计不受支持的原因无关。

生产修改仅在 Python `corner_fingerprint()`：保留 canonical 输入检查，按 native 生产 payload 编码，复用现有 UTF-8/长度前缀和 domain helper；合法非空 context 的 empty marker 为 false。通用 `canonical_analysis_context_bytes()`、native identity/schema 和 session 比较保持原语义。OFF 继续不采集 observation。

新增生产 KAT 在修复前出现 3 个 hash 失败，旧格式指纹拒绝测试也失败（共 4 failed / 1 passed）；修复后均通过。native 组件测试同时使用 `makeReferenceCornerFingerprint()` 和 `makeReferenceInputIdentity()`，覆盖 direct/ASCII/UTF-8。Python 通用 payload KAT 保留；另验证旧格式、其他 context 的指纹和空 context 被拒绝。测试 mock 补齐既有 native protocol 的 resolver，消除该 mock 的类型不匹配，不更改生产接口。

真实 native smoke 增加 observation 是否存在及 released 状态核对和原始结果保存，作为后续可重复的生产边界回归入口。没有更改生产 fallback 或放宽 snapshot contract。

### 实测结果

| 验证 | 结果 |
|---|---|
| Python context/snapshot/session/module timing 五组回归 | 158 passed；最后调整测试 mock 后 session snapshot 单独复跑 28 passed |
| Release/OFF fingerprint + Stage 6 + binding CTest | 9 passed，3 项 ON 诊断禁用，0 failed |
| Release/ON 同组 CTest | 12 passed，0 failed，含 Stage 6 synthetic/real fresh 差分、active payload、恢复及 ON 性能入口拒绝 |
| 修改的 native 组件测试严格编译 | OFF/ON 均通过 `-Wall -Wextra -Werror -pedantic -ffp-contract=off -fsyntax-only`，使用各自 compile_commands 的实际依赖和配置；常规 target 构建/链接也通过 |
| chain、diamond、xtea、usb、zipdiv | 每设计 OFF/ON 各 2 次，共 20 次 CPU/incremental baseline；全部正常完成、发布输出并关闭 |
| 重复与跨构建结果 | 每设计的 execution record、QOR、timing paths 全对象一致；诊断字段不参与功能比较 |
| Ruff lint/format | 修改的 4 个 Python 文件通过；初次闭包 loop variable / 随后的行宽问题均已修复 |
| 类型检查 | 生产 `sta_snapshot.py` 与真实 native smoke 通过；4 个修改文件合查仍报 3 条既有 malformed-input 测试诊断，均为 `test_sta_snapshot_context.py` 故意传错类型的用例，不宣称合查通过 |
| 差异检查 | 两仓库 `git diff --check` 通过 |

chain/diamond 的 ON 快照为 released 且 reference_supported=true；xtea/usb/zipdiv 的 ON 快照为 released 且 reference_supported=false，仍保留原 6 类不支持原因。OFF 不产生诊断快照。20 次记录均为 `baseline_only`、`incremental_batch_executed=false`；此次修复恢复了 baseline 的 Python 生命周期，不构成时序设计 mixed 更新支持。

所有构建均沿用 Release、GNU 14.3.0 与相同 Nix 依赖。OFF/ON 的 `ecc_py` 顺序链接，分别复制到本轮隔离 package，保存 SHA-256；运行时验证 native 只读开关。普通性能路径未加入额外诊断或 fresh 对照。

### 复测入口与证据

本次修复证据目录为 `chipcompiler/thirdparty/ecc-tools/build-incregpusta-cuda-on/fingerprint-fix-20260914/`，与初测目录分开保存：

- `run_acceptance.py`、`check_ci_eligibility.py`、`exit-codes.json` 和 `summary.json`；运行命令为在 ecc 根目录进入 `nix develop --command python3 <证据目录>/run_acceptance.py`。脚本使用独立结果目录，重跑应换一个新目录并复制两个脚本。
- `off/on-native-regression.xml`、对应日志、构建日志及 strict compile 日志。
- `off/on-chain`、`off/on-diamond`、`xtea/usb/zipdiv-off/on` 的 `result.json`、完整日志、报告与 timing paths。
- `off/on/python/ecc_tools_bin` 隔离 binding 及 `off/on-binding-sha256.txt`。
- `before-fix-pytest.log`、`pytest.log`、`ruff-*.log`、`production-type.log`、`changed-files-type.log`。

最小可重复生产回归命令为：选定隔离 package 的 PYTHONPATH，在 ecc 根目录执行 `.venv/bin/python test/tools/ecc/native_sta_smoke.py --backend cpu --strategy incremental --case chain --output-root <新的构建产物目录>`，diamond 同理；设置 WSL/native 所需运行环境后进入 Nix shell。该入口通过公共 wrapper 调用实际 native baseline，成功包含捕获和关闭，不使用 mock 替代。

本轮未运行全仓类型检查，没有修改通用 README、用户已有 CLAUDE.md 改动或三份历史报告，没有升级依赖，没有 commit/push。
