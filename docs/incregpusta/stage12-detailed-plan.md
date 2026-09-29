# Stage 12 详细实施计划

状态：2026-09-21 开始，2026-09-22 按用户要求采用局部稳定候选身份；2026-09-29 完成本轮实现、正确性回归及十三组修复版 1/3 参考测量收尾。原严格高性能验收未完成。基线 ECC `aa33d82`、ecc-tools `7cd621119`。
本文件落实已批准方案。2026-09-23 用户调整：本轮加速测试仅作参考，允许采样过程中 GPU 共享，不因占用或未达原加速门取消测试；实现、正确性、并发安全及完整交付要求不变。严格高性能结论仍须另行满足原性能门，本轮不宣称该门已通过。保留已有用户修改，不自动 commit/push，不改通用 README 或依赖。

## 冻结与性能门

先修复阻碍正确性预检的既有差异，完成输入资格、CPU 线程校准和 frozen manifest，再实施并行及性能优化。保留 Stage 11 二进制与输入，不能依据优化结果更换必过样本。

冻结前核对 native/full 连续十批编辑、目标模式的实际执行与公开结果、实际加载约束和输入身份。完整十批 ON oracle 差分与最终验收单独记录，可在隔离串行基线上继续运行；冻结不能把这些尚未完成的检查标为通过。冻结后的正确性失败必须修复或作为未完成项保留，不得据此更换必过输入。

- 小设计沿用 xtea/usb/zipdiv 原 ICS55 post-synthesis、无 SPEF 与 Q/D traces。
- aes/APU/BM64/picorv32a/y_huff 复用可核验产物或独立综合；从既有语义和 Q/D 编辑预检通过者中按 timing-node 数选最大原始设计，平局按名称。
- 原始设计 Q/D 各十批，每批 min(100, floor(合法位置数/10))，不足一处即预检失败。按稳定 net/sink 语义名称选择；为遵守每批同一原 net 只能编辑一次的既有契约，每个 net 最多取十个位置，再轮转分配到十批。合法位置数指该十批可调度集合，同时记录未裁剪位置数；由独立 CPU/full 验证连续编辑，不声称 greedy gain。
- 规模集为可由 native 加载的宽层汇聚、多时钟顺序网表，各约 10⁴/10⁵/10⁶ timing nodes；两类 10⁵ 为必过项。记录真实规模及资源限制。
- 每批消费 timing values、完整公开 QOR、max_paths/nworst=20 的 paths，不生成磁盘报告。主指标含编辑、提交、回传、物化及后处理；加载与清理另完整记录。
- CPU/full 以按规模选中的真实设计 Q trace，在固定 affinity 0–31 下轮转校准 1/8/16/32 线程：校准预热 1 轮、采样 3 轮，按完整 trace 消费者中位数选最低者，平局取较少线程；四模式随后采用同一冻结配置。校准另存每线程实际 CPU 时间，不替代正式 5/30 采样。
- 四模式交错运行；本轮按用户 2026-09-28 最新要求统一为每模式预热 1 次、采样 3 次，包含百万节点可选用例；工程默认仍为 5/30。所有本轮样例绑定修复后的当前二进制，旧版用例重新采样。一次 fresh process 完整 trace 是统计单位。当前版本已有更多数据时，按原始序号取前 1 次预热和前 3 次正式样本，不将额外预热改记为正式样本；全部旧版本、额外样本及旧统计保留，不能并入新版统计。配对比值中位数使用固定 seed=20260921、10,000 次 bootstrap 的 95% 区间。
- 本轮完成既定用例的参考测量，保留两个比较的中位数、置信区间及全部负结果。原严格性能门仍定义为所有必过用例的两项区间下界 >1；共享 GPU 参考结果不作为该门已通过的证明。

## 计算与所有权

1. 按层、同层目标节点并行，每个结果单一写入者；不统一 full/mixed 候选访问顺序。每个结果 lane 先确定数值极值，再从现有 epsilon 窗内按局部稳定身份选取候选，发布该候选的实际值和完整前驱。seed 优先，其余使用已有入边行内序号和输入 transition；舍入、epsilon、全部 tag 和 CRPR 身份保留。不得用非传递的两两 epsilon 比较冒充与访问顺序无关的选择。
2. Arc 槽位和 ID 稳定，不建立全局候选排序或额外遍历索引。当前 data-only insertion 的旧入边槽保持顺序，单元并行弧沿用 Liberty 序号，新 buffer 建立自己的行；独立 fresh native 使用自身入边和计算实现。任意外部图以自身入边行定义局部身份，不以 fresh 会重编号的 ArcId 作为跨实例 tie-break。
3. 弧初始化、clock slew/arrival、顺序发射、data slew/arrival、endpoint required、逆层 RAT、slack 分阶段。clock 按 domain/level 紧凑遍历，保留跨 owner clock arc 的 invariant 拒绝；每份可变结果单写入者。
4. full Kahn 并行前沿保留根顺序与 FIFO 唤醒序：以跨轮递增的稳定出边访问序号归并唤醒键，前沿 edge kernel 完成后，按稳定物理 slot 标记各 sink 的最后一次唤醒，再稳定压缩本轮边得到下一前沿；不逐层扫描全部节点，也不由 atomic 完成顺序决定排列。使用 CUDA 自带扫描/压缩与持久 scratch，保留 capacity/cycle/processed-count。
5. CPU mixed builder/Kahn 和 GPU reconstruction 分工不变；CUDA full/targeted/incremental 共用传播。
6. patch、undo 按唯一位置并行，依赖子阶段用同 stream 隔离；重复 seed 保留最后写入语义。错误状态原子归并，ON 审计无竞争。
7. 连续 staging＋目的位置描述合并小上传；上传源及退休设备缓冲存活至工作完成。仅在必要设备决策、结果交付和清理时等待。
8. 保留 Stage 11 局部事务、poison/恢复、按需物化。禁止浮点无序归约、整图事务复制、通用内存池、新运行期开关或 affected-cone 扩展。

主要实现边界为现有 timing_cuda 内 propagation/levelization、patch/transfer/runtime 和 packing；接口增加限于内部遍历/工作缓冲与 benchmark 线程参数。生产模式和 Python API 不扩展。现有性能入口补 native CPU/full OFF workload，不能调用 oracle 充当性能基线；统计 schema 和消费者同步迁移。

## 测试与证据

独立 Release OFF/ON、隔离 binding，另做无 CUDA 回归。保留三设计四模式、多批次、fresh native oracle、winner/paths/checks/level 与 OFF/ON 对照。
新增宽层跨 block、深链、fan-in/out、汇聚、epsilon、parallel arcs、多 clock/tag、重复 seed、空行、长批次和容量增长；测试不同 launch 形状的确定性。
验证部分 patch、Aux 扩容、放弃、rollback、恢复后继续、连续不查询和查询后编辑。CPU sanitizer、CUDA memcheck/initcheck，适用的 racecheck/synccheck；不能以 shared-memory racecheck 代替全局写入审查。
Nsight 核对活跃线程/warp、SM、传输、分配、同步和消费者分相；剖析独立于正式采样。OFF 不生成 receipt/oracle；ON 性能采样前拒绝。
完成独立设计/代码审查、相关 native/parent 回归、严格构建、lint/type/diff；保存所有实际失败，既有错误不宣称通过。

## 顺序与运行约束

冻结及设计审查 → 错误/顺序/辅助操作 → full Kahn/patch/undo → 传播 → 传输/性能入口 → 审查、回归、剖析和正式验收 → 文档收尾。
服务器使用现有 Docker、空闲非 0 GPU、tmux；项目共享 512 GB 硬上限、swap=0。运行目录独立，报告记录命令与证据，usage 只写使用方法。
按用户最新确认，启动时选择空闲非 0 卡，运行中他人进入同卡只记录占用，不取消样本或重跑。监测失败记录为证据缺失，不据此丢弃参考数据。输入、模式轮转与线程配置不变；本轮统一执行上述 1/3 协议，历史 2/10、5/20 和 5/30 结果保留。运行中的旧控制器切换须有直接授权，不得按加速比筛选结果，也不得宣称严格独占或正式高性能验收通过。
