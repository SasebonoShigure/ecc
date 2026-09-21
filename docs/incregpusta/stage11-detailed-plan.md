# Stage 11 详细实施计划

状态：2026-09-21 功能、事务安全和默认路径剖析验收完成；实际失败与限制见[实施报告](stage11-progress-report.md)。基线 ECC `7cd666f`、ecc-tools `fec270b8a`。
范围：生产路径精简、持久存储、增量事务和按需结果；保持现有 STA 语义与全图传播。Stage 12 的并行计算和显著加速门不在本阶段。

## 设计与实施顺序

1. 冻结现有功能、输入和调用/分配/传输基线，保护已有修改。
2. 取消 CPU baseline 自动 capture/FIFO；观察仅 ON 显式请求，功能状态独立。删除重复 active_arc_mask、重复 levels、无消费者状态和同源重复证明。
3. Native Database/Liberty 和 CPU graph/index/resolver 由会话稳定持有。ExpectedBeforeBinding 在独占批次内借用，apply/扩容前完成 descriptor。reference delta 采用追加/局部替换。
4. prepare 预留容器、undo 和恢复记录；受控 apply 后只执行目标 backend，使用 committed/work 结果缓冲。成功无抛出发布，失败局部撤销，不靠第二次传播恢复。
5. CPU incremental 复用 targeted 拓扑/负载准备，删除每批额外 native full；fresh native CPU/full 仍独立作为验收 oracle。Arc 槽位与候选顺序分离，只维护受影响邻接。
6. CUDA 会话持久持有 Runtime、stream/events、容量和 scratch；只扩容不足数组。不变 Child/model/table 与实例 ChildState/load 分开，Aux 按行更新。CUDA/full 同等复用模型/容量，仍完整重建、上传、分层和传播。
7. 公共 seed 初始化直接生成稀疏记录。路径使用 N×8 行索引、排序 tag 和紧凑状态；结构可达域维护不计算锥 AT/RAT，不截断有效身份。
8. 必要 levels 与 timing 结果分开。提交无需完整 host timing；查询按现有 timing/paths/报告需求物化，同 generation 复用，新提交失效，不新增逐点 API。
9. Runner 每样本 fresh session 执行完整 prefix，close/destroy 后下样本重新加载；删除最终回滚用整库 owner。迁移 cleanup 状态、提交/物化/消费者计时及受影响 schema。
10. 分组测试、独立代码审查、完整 OFF/ON 回归、实际剖析和文档收尾；不 commit、不 push。

## 所有权与失败契约

- 一个 owner 同时只有一个 pending transaction；stage 对象 move-only，放弃必须撤销并释放 pending。
- undo 保存实际旧值、新增键和旧逻辑长度，不能用外部 expected 字段替代。rollback 不分配；真实 CUDA/撤销/清理错误 poison。
- 恢复记录及 history 容量在 apply 前准备；提交只 noexcept move、结果交换、generation/cache 切换。成功后释放本批 undo，恢复历史每批只追加一条。
- Native full 的旧派生图和 Net driver/load 缓存移到工作状态，Pin.direction 等被改标量保留紧凑旧值；完整重建失败全部恢复，不克隆 Database/Liberty。
- ArcId/native 槽位和候选顺序分别维护。复用现有 canonical key 与稳定 parallel 顺序，保持 epsilon/winner；查询中的 Arc* 不得跨编辑或扩容存活。
- ExpectedBeforeBinding 的借用在修改前结束。任意外部输入保留完整校验；内部不增加公开 skip-validation。
- 旧权威结果在计算过程中不覆盖；必要 levels/status 回传保留。pending/poison 时禁止查询。
- 物化和后处理各自成功后才标记 generation；使用 analyzePropagatedTiming，不调用会重算 RAT 的 analyze。查询准备失败不返回旧报告，普通分配失败可重试。
- 上传 staging 活到相应 stream 操作完成；先保证生命周期和依赖再减少同步。扩容只迁移相关 live prefix并如实计量。

## 涉及边界

- `IncrementalStaSession`、`StaCsrSessionContext`、STAInterface 与 Python session：显式 ON observation、状态/查询生命周期。
- Native targeted/full preparer、candidate executor、Dual-CSR updater/index/factory/coordinator/recovery：局部 undo、稳定 graph、单条恢复记录。
- CUDA Runtime、packing/patch/transfer/session、mixed levels、unpacking/scatter：模型分离、持久容量、稀疏路径、按需结果。
- 现有 trace replayer、probe、serializer/controller：fresh 生命周期及真实计时。受影响协议升 major并迁移仓内消费者，不新增框架或兼容壳。

## 测试与验收

- 同 GCC/CUDA/依赖的独立 Release OFF/ON，隔离 binding并核对实际模块及只读状态；默认无 CUDA 回归。
- 原 xtea/usb/zipdiv ICS55 post-synthesis、无 SPEF及 Q/D traces；四模式多批，独立 fresh native CPU/full 比较拓扑、timing、winner、公开 QOR/paths与适用检查，恢复后继续提交、跨构建等价。
- 无查询连续提交、首次/重复查询、查询后编辑与 Arc 扩容、完整报告和分配失败重试。
- malformed、stale/owner/unsupported、cycle/numeric/capacity、部分 patch失败、放弃、history 预分配失败、full 构建中途失败、真实 rollback；故障注入仅 ON。
- 并行弧、epsilon-chain、高扇出、同模型不同负载、多 clock/tag、空行、域变化、长批次；CPU sanitizer、CUDA memcheck/initcheck，故意硬件错误单独运行。
- 实际调用/分配/传输证明没有整库/整图事务复制、重复 native full、未变表重传、history 前缀复制及未请求 timing D2H；全图传播、levels、重置和扩容另计，不以源码/固定计数门禁替代。
- 性能 OFF、ON采样前拒绝、比较/诊断 not_run；工程默认预热5/采样30，短 smoke显式标注。Stage 11不据此宣称 Stage 12 性能通过。
- 相关 native/parent 回归、严格构建、lint/type及diff检查，所有失败如实记录。更新规范/分类/实施报告，不修改 README 或升级依赖。

## 独立设计审查

2026-09-17，独立审查已完成。已纳入：full 的 Pin/Net 派生字段撤销；history 预构造和无抛出提交；物化/报告独立完成状态；禁止 analyze 重传播；scatter 指针与 before 借用不得跨扩容。
实现后的独立只读代码审查已完成；发现的边界和测试缺口已修复并复验，记录见实施报告。

服务器构建/测试遵守共享 512 GB、swap=0、空闲 GPU与持久会话；现有远程工作不覆盖。
