# Stage 13：生产集成与正确性 CI

状态：主体实现与服务器物理正确性验证完成；GPU CI 接入待确定，整阶段未关闭。日期：2026-10-01。当前 Stage 13 实现于 2026-10-08 按用户授权本地提交，未 push。基线为已提交 Stage 12：ECC d91e536、ecc-tools 42b64be72；原始工作区身份、补丁和备份见 /home/shigure/code/stage13-20260928-163421/baseline.json。Stage 12 的共享 GPU 参考测量已收尾，原正式性能门仍为 not_run。

## 已批准边界

显式 incregpusta_experimental preset 在 CTS、基线合法化后、routing 前运行 TIMING_OPT。普通 preset/post-synthesis/signoff 仍默认 CPU/full。保留四模式、默认诊断 OFF、局部事务、持久设备存储、按需物化和并行传播。不修改通用 README、用户报告、依赖或 ecc-dreamplace，不自动 commit/push。

原生 CPU 寄生语义不替换为 Elmore：支持范围内的 Arnoldi/DMP、有效电容、阈值、slew、fallback 与 CRPR 必须由 reference/CUDA 对照。合法且计算成功的 greedy 批次沿用既有正 gain 规则提交，不因实际 WNS/TNS 退化增加收益回滚策略；如实记录负结果。正式生产性能属于 Stage 14。

## 实现边界与数据流

1. **寄生模型**：在 timing_csr/timing_cuda 中加入树形 RC 的结构模型与 backend 计算，native DelayCalculator 保持独立黄金实现。只允许结构/负载相关的 RC 预处理；slew 相关求值在目标 backend 完成。模型缓存按 net 拓扑、负载、analysis/transition 失效，不能用 native 计算后的 gate/wire delay 或 slew 作为 CUDA 输入。保持原生模型阶数、迭代界限、阈值、舍入与 fallback 选择。Arnoldi 特征值、pole/residue 取决于实时 drive resistance，必须在目标 backend 求值，不能混入 CPU 结构准备。
2. **RC 构建**：iZH 的物理编辑边界直接复用底层 FLUTE（不调用会移动重合 terminal 的 CTS Router），以合法化 pin 坐标及 PDK 层参数生成有稳定节点身份的树。水平/垂直各选 routing 允许范围内最低可用信号层，可显式覆盖；参数缺失、非有限或单位非法拒绝。只估计线电阻、对地电容，pin 电容按 native 约定仅加一次。零长度、重合 pin、无负载和退化树有明确处理；耦合与完整 via 不在范围内。
3. **固定时钟**：使用真实 clock arrival/slew 与 launch/capture 路径、CRPR。初始化完成后固定 clock 拓扑与已有实例位置；编辑限制为 data-only。支持判定按实际能力解除，clock gating/divider、范围外寄生继续 typed rejection。
4. **生产 session**：IncrementalStaSession 承接稳定语义批次、合法化坐标和 expected generation；提取现有 probe 必需的 guarded execution/生命周期编排到生产 owner。新增生产批次应用、当前 generation 查询、最终报告与恢复入口，不暴露任意 mutation callback 或 failpoint。probe 改为调用生产入口，oracle 计算保持独立。
5. **共同事务**：EngineDB 继续指向唯一 native IDB。候选/几何准备后，独占批次预留容量与撤销空间，再 apply IDB/RC/native/CSR、计算并原子发布。撤销保存真实旧值、新增键和原逻辑长度；成功只保存本批恢复记录，不保留 undo 或复制历史前缀。公开查询在 pending/poison 时拒绝。
6. **合法化**：父仓库窄适配复用 DREAMPlace greedy legalization 底层算子；已有实例和历史 buffer 都是固定障碍，仅本批新 buffer movable。缓存几何和容器容量，避免重建完整 PlacementEngine；核验 site、row/orientation、边界、障碍和位置合法后再交给共同事务，不调用不存在的 run_incremental_lg。
7. **greedy**：提取现有 selector 的实际排序/gain/冲突筛选到生产共享边界，诊断 receipt 仅 ON；移除生产候选对测试固定 RC 常量的依赖。使用当前 RC/负载/Liberty，稳定语义身份 tie-break。默认 top-k=100、rounds=10、max_buffers=1000，cell 来自 PDK buffers 且排除 dont-use。每轮通过现有摘要查询物化必要结果，不构造未消费的 timing/paths 返回对象；选正 gain、同批不冲突候选；无候选/合法位置/预算耗尽明确停止。
8. **父流程与产物**：rtl2gds builder 新增 preset，runner 只增加 TIMING_OPT 分派，新逻辑留在专用小模块。复用 sta backend/update_strategy/fallback_policy 配置，默认 CPU/full/error。报告用 analyzePropagatedTiming；power/timing/SDF/交给 routing 的 DEF、netlist 同 generation，临时目录完整准备后发布 manifest。失败不发布旧/部分结果，普通报告失败可重试，不撤销设计提交。

## 失败与恢复

准备失败不改变 canonical 状态；apply/backend/放弃失败按反向局部记录撤销。撤销、清理失败或设备状态损坏 poison 全会话，禁止旧缓存与后续编辑。恢复以基线 post-CTS checkpoint 和已提交物理编辑历史重放至最后 generation；损坏 CUDA context 用新进程，恢复成功后还须验证继续新提交。不每批保存整库 checkpoint，不让生产成功路径自动撤销。

不同层只由共同 owner 发布可见 generation；对外成功应答在所有层完成提交后产生。committed 标记是逻辑提交点，必须在标记前完成计算、共同资格检查、恢复记录写出和全部分配，标记后以无抛出操作完成各层 owner 切换与 generation 发布。失败注入只在 ON；OFF 非默认 failpoint 必须拒绝。

## 正确性与交付门

先通过 RC/clock 小例及 fixed physical trace，再启用 closed-loop greedy。xtea/usb/zipdiv 原 RTL/约束/ICS55 不改，独立生成 post-CTS legalized checkpoint。四模式真实 Q/D 多批次；ON 每批 fresh native/full 比较物理连接和坐标、RC、拓扑、timing、winner、checks、CRPR、QOR/paths、levels 与实际执行。baseline/no-candidate 不计 incremental 通过，不静默退回 full。

覆盖模型单位、Arnoldi/DMP fallback、阈值、多 clock/tag、parallel arc、负载变化、容量增长、无合法位置、部分 apply、放弃、history allocation、publish 前后失败和真实 rollback；覆盖连续不查询、重复查询、查询后编辑、报告失败重试、恢复后继续提交及输出。

独立 Release OFF/ON 隔离 binding，核对真实加载模块；另跑无 CUDA、CPU sanitizer、CUDA memcheck/initcheck 及适用并发检查。调用/分配/传输剖析证明未回退到整库复制、重复 full、历史复制或未请求完整 D2H。权限限制保留，不改驱动安全配置。OFF 不运行 oracle/完整 receipt；未执行标 not_run。

复用现有工作流增加 CPU-fast、native source-build、手动 CPU integration/GPU correctness，不注册 runner。服务器实测与未运行的托管 workflow 分开记录。严格构建、parent/native 回归、修改文件 lint/type、两仓 diff check；保留实际失败与修复。独立代码审阅通过后才进入完成态。

## 执行顺序与审阅

冻结基线 → 独立设计审阅 → RC/clock/backend → 物理事务与 fixed trace → preset/greedy/产物 → 独立代码审阅和完整验收 → 文档收尾。运行目录独立，usage 只写用法。服务器共用 512 GB 硬上限、swap=0，非 0 空闲 GPU 与 tmux。

设计审阅第 1 轮：request-changes；独立 RC 数学子模块无剩余 blocker，可先实现。以下约束已修订，第 2 轮独立设计复审 approve（2026-09-29）；生产实现仍须遵守以下约束。代码审阅：RC/事务/合法化分组已审阅并修复；完整实现最终 Spec/Standards 审阅已通过；最后一项 greedy 多余结果复制已修复并复审。受影响回归和剖析已完成，实际失败及未执行项见实施报告；GPU CI 接入选择尚未关闭。

## 设计审阅修订：发布与接入约束

- **唯一完成点**：独占 guard 内各层完成 apply/计算并保留 undo；提前准备返回值、历史容量和恢复记录。标记前检查共同 generation、事务状态及 CUDA publish 的同一资格判定。原子发布 committed 标记后，无分配、无设备调用地完成 CUDA/native/IDB commit、历史追加、可见 generation 和缓存失效，释放 undo 后再解除 guard。复用现有 commit，不新增延迟释放层；清理旧状态的成本仍计入提交。
- **恢复记录**：完整写出并关闭的本批记录包含基线/配置身份、前后 generation、实际模式及全部编辑/坐标；同目录原子 rename 为 committed，不覆盖已有 generation。标记前失败撤销；标记后 publish 拒绝或其他不变量失败必须先 poison、保留标记、禁止查询和继续编辑，恢复包含该批，不能返回旧 generation 当作普通失败。guard 内不允许另一个恢复 owner。验证 rename 前后、层间及应答前退出的恰好一次恢复。此契约覆盖 worker 失败，不宣称无 fsync 的文件具备断电持久性。
- **driver 单写入者**：每 driver 的 child/input-transition 求值按原生确定顺序在唯一 owner 中完成，sink 只读完成数据。native 的 output-pin/analysis/output-transition/driver-slew 缓存碰撞须由相同 slew、不同 child 的针对性用例固定覆盖行为；不能用线程结束先后来决定选择。
- **propagated/ideal 分离**：propagated 的 effective clock 使用真实物理 arrival/slew/前驱，ideal 保持原行为。同步修改 seed、clock-to-Q、endpoint required、CRPR、validator 和 CUDA，覆盖非零公共 clock path 以及不同 launch/capture transition；不只删除 unsupported。
- **合法化几何**：工作数组新 buffer 为 movable 前缀，已有实例和历史 buffer 固定；缺失 row/site 洞与 placement blockage 表达为障碍。输出按真实 row 设置 orientation 并复核。底层算子的 pos.clone 是必要几何工作副本，计入实际分配，不能称为零复制。
- **产物消费**：不可变 generation 目录准备所有 DEF/netlist/报告，原子切换 manifest。routing 的 TIMING_OPT 输入解析和公开产物查询读取 manifest 并核对 current generation；禁止固定旧路径绕过。新设计提交立即使旧 manifest 不再代表当前 generation，报告失败可在已提交设计上重试。普通 preset 沿用原产物路径。

## RC 局部事务接入约束

- 复用原有 raw/graph 事务；在 apply 前准备受影响旧网的 replacement 与新网。native ParasiticNet 使用 map node 转移保存真实旧对象，不假定其支持无抛出的 move/swap。
- 旧 CSR tree 借用 committed owner，新 tree 每个受影响 net 只准备一次；刷新未移动 sink、driver cell 和 Q deferred seed。不能重建一个值相等的新 owner 充当 expected。
- CUDA 对受影响 net 保留 committed/work 容量及实际旧 descriptor；新上传完成前不释放旧 buffer。局部撤销包含 RC 索引、bindings 和现存 CTQ seed，不能仅恢复 Arc。
- NoParasitic、旧 full-record 拒绝与受控 pre-route tree 更新明确区分；四模式迁移实际执行路径，不以删除 gate 代替 RC apply。首组验证覆盖 Q/CTQ、未移动 sink、容量增长后放弃、部分上传失败及 rollback 后连续提交。

### 物理 RC 与 IDB 接口复核约束

FLUTE 输入先按真实坐标合并位置，再以零电阻边保留每个重合 terminal 的独立身份，不移动 pin。整数坐标、跨度和长度先检查溢出；对角边按固定水平/垂直次序拆段。层宽按 LEF DBU 转微米，R 使用 Ω/□、面积 C 使用 pF/μm²、周边 C 使用 pF/μm；不乘数据库精度因子或 CTS coupling factor，不在 RC builder 加 pin cap。缺失层参数须有初始化后的明确标记；DEF/LEF DBU 不一致须拒绝或显式归一。

IDB 的公开 create/connect/removeSafe 存在中途分配，不能作为无抛出 apply/undo。新增专用 prepared 批次只取得必需的受限容器访问，提前构造对象、名称 map 节点、受影响 pin 引用及索引；真实旧连接与顺序留在 undo。禁止直接改公开 vector 而遗漏私有名称 map 或高扇出 pin index。
