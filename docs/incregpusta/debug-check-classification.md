# Stage 0–8 开发检查分类

状态：本表已同步 2026-09-08 冗余清理；当前结果见 [清理报告](stage0-6-redundancy-cleanup-report.md)，此前诊断分离结果与限制见 [实施报告](debug-checks-implementation-report.md) 和 [实测证据](debug-check-acceptance.json)。开发规则见 [development-guidelines.md](development-guidelines.md)。复杂度中的 N/E 为节点/边数，B 为累计批次数，D 为本批编辑规模。

| 调用链 / 数据 | 用途与复杂度 | 归属 |
|---|---|---|
| CsrSessionSnapshotAdapter 的实际 input、metadata、active/released 身份与状态 | 真正导出、scatter、失效和释放；O(N+E) 的功能成本 | 始终保留 |
| makeReadyObservation、prepared observation pair、Python observation mapping | 对已受控快照进行重复归约、序列化与深拷贝；O(N+E) | ON |
| 外部 reference/descriptor/level 输入校验、局部 expected value、session/generation/owner | 阻止输入错误、串会话、越界和错误提交；通常 O(D)，输入首次构造可 O(N+E) | 始终保留 |
| Stage 3 CsrExecutionAuthorization | 受控执行的 session/generation 授权；O(1) | 始终保留；完整证明另存可缺省 payload |
| Stage 3 proveCsrFullExact、coordinator rebuilt snapshot / CSR replay / native readback | 证明候选与 CPU/full 完整等价；O(N+E) 或更高 | ON；OFF 不生成 full-exact proof |
| ExpectedBeforeBinding graph/index | 描述符实际消费的受控前态，值所有权跨 candidate 生命周期；O(N+E) | 始终保留；resolver/identity 完整副本仅 ON，移除固定复制计数 API |
| DualCsrVerifiedStage / Recovery 的 expected aggregate | 重复全对象比对副本；O(N+E+B) | ON；OFF 使用 session/generation/committed identity 绑定 |
| telemetry.logical_edges_after | edge view 实际驱动 levelization 的活动边数量；维护和公共输入核对 O(E) | 始终保留；字段的历史命名不代表纯诊断 |
| 其余 updater 结构计数、容量事件、full-export/candidate/full-levelizer 访问计数 | 证明实现路径与计数恒等式 | ON |
| updater 的 detached staged graph、native rollback database | 原子发布、真实回滚必需的隔离副本 | 始终保留 |
| factory / coordinator / index stage | 最终受控 aggregate 全检 O(N+E+B) 归 factory；删 factory 分项和 publish 对同一 staged 的重复全检 | 完整证明仅 ON；公开入口及局部 descriptor/index delta 和发布条件始终保留 |
| execution_trace 的 generation、mode、恢复用 descriptor/semantic trace | 恢复需要按原模式重建每批 | 始终保留 |
| execution_trace 的完整 levels 与 mixed 审计字段 | 重复存储每批诊断结果；累计 O(B(N+E)) | ON |
| mixed builder actual_pairs、详细 arc/storage 访问计数、恒等式 | 区分 parallel 与 proxy alias 的诊断集合；O(E log E) / O(E) | ON；mapped_pairs、边界、indegree 和 cycle 分类始终保留 |
| narrow capture 的 typed node/arc/model records 与 coverage | 编辑描述符和有效载荷的真实输入 | 始终保留；coverage 检查实际容器，不依赖诊断计数 |
| narrow capture audit、全图 export 访问证明 | 证明走了局部读取路径；含 O(D) 额外计数 | ON；实际成功与审计成功分离 |
| mode recovery 的重新加载、逐批重建和 publish | 真正恢复操作 | 始终保留 |
| mode recovery 的整份 expected rebound aggregate、prefix/full equality | 恢复后的独立等价性证明 | ON |
| 性能 replay 的加载、candidate、baseline、rollback、原始时序 | 工作负载生命周期与实际结果 | 始终保留 |
| 性能 replay 的 observation / resource / exact receipt / source isolation / fresh oracle | 完整功能验收和路径证明 | ON 诊断入口；OFF 性能入口无这些输出或步骤 |

禁止按函数名称批量关闭校验。新增或发现混合职责时，先从所有调用者和数据消费者判断，再拆分必要状态与诊断。未采集的计数不代表已证明为零；默认输出明确 `correctness_comparison=not_run`。

2026-09-08 补充分类：旧 `DualCsrVerifiedRecovery` 无成功消费者，整条删除；恢复唯一使用按模式重放，最终 aggregate move 交付。恢复 evidence 仅 ON 可选输出，不参与授权。Full/mixed 自产 levels 各在 backend/pipeline 保留一次 ON 完整证明，外部 levels 与 replay seam 始终验证。Stage 6 删除同源双份 receipt 与绑定比较，值等价和 level 合法性直接消费同一 canonical 对象。旧 ON timing smoke 删除，已有 controller 保留独立诊断；OFF 性能 CLI 删除三项冗余构建参数。

## Stage 7 CUDA 补充

| 调用链 / 数据 | 用途与复杂度 | 归属 |
|---|---|---|
| CUDA build/device preflight、runtime status/sync、容量乘法、finite/cycle/view failure | 确保真实支持、内存及数值安全；O(1) 或算法内 O(N+E) | 始终保留 |
| full pack/seed initialization、完整 H2D/D2H、scatter 和 native candidate | Stage 7 full 的实际功能/隔离成本；O(N+E+表+path storage) | 始终保留；不得挪用为 Stage 8 targeted |
| 受控内部 scatter 的完整结果重复一致性检查 | 已验证计算结果的独立防错证明；O(N+E+paths) | ON；公开任意输入 scatter 始终验证 |
| GPU trace input/timing observations、完整 projection、fresh CPU 子进程、source isolation | 独立正确性诊断；每 prefix 额外完整执行/序列化 | ON；OFF 无 receipt，comparison=not_run |
| 实际 bytes、allocations、launches、device/build 信息和 event/e2e | 性能事实，不是路径等价证明 | 始终保留 |
| native 安装回滚、第二批失败后的真实恢复、session poison/close | 事务功能，不依赖比较模式 | 始终保留；恢复后的完整独立等价性证明仅 ON |

本轮结果和实际调用剖析见 [Stage 7 实施与验收报告](stage7-progress-report.md)。未执行的 OOM 场景和全仓类型检查不得记为通过。

## Stage 8 targeted CUDA 补充

| 调用链 / 数据 | 用途与复杂度 | 归属 |
|---|---|---|
| NativeTargetedEditPreparer 局部适用性、稳定 ID/rank、clock 身份 | 描述符与正确原状态绑定；O(D) 局部读取，加必要地址元数据维护 | 始终保留 |
| Database 隔离复制/library pointer 重绑、Arc canonical permutation/predecessor 重映 | 正确事务和 fresh winner/load 顺序；O(N+E+timing storage) copy，O(E log E) 排列 | 始终保留；不是诊断副本 |
| device detached candidate、D2D seeds reset、changed rows/payload H2D | 原子更新和避免上批结果污染初态；D2D O(N+E+timing storage)，H2D 为本批变更及 metadata | 始终保留 |
| patch incidence/重复写、actual slot expected、table/seed 域、容量、cycle/finite、CUDA error | 输入/适用性/内存及数值安全；O(D) 或融合到算法遍历 | 始终保留 |
| origin owner/session/generation、prepared scatter 和初始/上一代 rollback owner | 正确联合发布；发布只做 noexcept 写入与所有权转移 | 始终保留 |
| canonical export/device debugState、完整 timing projection、四 pass Aux visits | 逐批独立证明；O(N+E+table+timing storage) 额外复制/遍历 | ON |
| targeted/CUDA full/fresh CPU 每 prefix 子进程、source isolation、恢复完整比较 | 独立 oracle 与生命周期证明 | ON controller；OFF 只采目标 workload |
| test-only device friend readback / Aux omission、硬件故障隔离程序 | 开发验收；读取实际设备或显式错误实验 | 仅测试程序，不链接生产路径；硬件故障机制要求 ON |

当前边界、实测字节/调用、失败及修复见 [Stage 8 报告](stage8-progress-report.md)。初始化两次 export/pack 与逐批零全量调用分开记录，不能混为一个局部成本承诺。
