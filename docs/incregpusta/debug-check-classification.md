# Stage 0–6 开发检查分类

状态：已实施并完成双模式验收；结果与限制见 [实施报告](debug-checks-implementation-report.md) 和 [实测证据](debug-check-acceptance.json)。开发规则见 [development-guidelines.md](development-guidelines.md)。复杂度中的 N/E 为节点/边数，B 为累计批次数，D 为本批编辑规模。

| 调用链 / 数据 | 用途与复杂度 | 归属 |
|---|---|---|
| CsrSessionSnapshotAdapter 的实际 input、metadata、active/released 身份与状态 | 真正导出、scatter、失效和释放；O(N+E) 的功能成本 | 始终保留 |
| makeReadyObservation、prepared observation pair、Python observation mapping | 对已受控快照进行重复归约、序列化与深拷贝；O(N+E) | ON |
| 外部 reference/descriptor/level 输入校验、局部 expected value、session/generation/owner | 阻止输入错误、串会话、越界和错误提交；通常 O(D)，输入首次构造可 O(N+E) | 始终保留 |
| Stage 3 CsrExecutionAuthorization | 受控执行的 session/generation 授权；O(1) | 始终保留；完整证明另存可缺省 payload |
| Stage 3 proveCsrFullExact、coordinator rebuilt snapshot / CSR replay / native readback | 证明候选与 CPU/full 完整等价；O(N+E) 或更高 | ON；OFF 不生成 full-exact proof |
| ExpectedBeforeBinding graph/resolver/index | 描述符构造使用原图和索引，值所有权跨 candidate 生命周期；O(N+E) | 功能必需，不能按名称删除 |
| DualCsrVerifiedStage / Recovery 的 expected aggregate | 重复全对象比对副本；O(N+E+B) | ON；OFF 使用 session/generation/committed identity 绑定 |
| telemetry.logical_edges_after | edge view 实际驱动 levelization 的活动边数量；维护和公共输入核对 O(E) | 始终保留；字段的历史命名不代表纯诊断 |
| 其余 updater 结构计数、容量事件、full-export/candidate/full-levelizer 访问计数 | 证明实现路径与计数恒等式 | ON |
| updater 的 detached staged graph、native rollback database | 原子发布、真实回滚必需的隔离副本 | 始终保留 |
| factory / coordinator / index stage 重复全量校验、resolver.stage 重演 | 重复验证同一受控状态；O(N+E+B) | ON；局部 descriptor/index delta 和发布条件保留 |
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
