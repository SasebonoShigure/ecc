# Stage 14.5：百万单元性能优化与默认路径精简

状态：本轮优化、功能回归与用户指定的 1/3 参考测量已完成，2026-10-14。基线提交仍为 ECC a8604b5、ecc-tools 7229c5955；工作区已采用经完整内部对照的 85 版，未 commit、未 push。已知全仓检查失败及正式性能未执行项见实施记录。

## 目标与边界

以正确性和真实端到端成本为依据，允许改进结构、流程和算法，不受旧总计划的具体实现方式约束。评估百万实际标准单元上 CUDA/incremental 相对同版本 native CPU/full 的百倍目标；记录真实差距，不预设成立，也不故意保留慢 CPU 路径。

保留当前公开结果、实际模式、时序语义和错误恢复契约。独立 native oracle 不与目标 backend 共用计算答案。新算法须证明失效范围及数值、winner、前驱、clock/tag、CRPR、时序检查正确，不能放宽容差。

## 实施顺序

1. 冻结第十九版完整十批成本基线，保存源码、构建和输入身份；其24/24次运行已完成。最初提交的多时钟基线因超时缺少完整结果，对应比较保持 not_run。第十九版只记录旧消费者口径，不以提交分项之和冒充后来新增的连续循环计时。
2. 沿生产调用链分类：外部输入边界、必要寻址、真实失败处理、重复证明、纯诊断。无消费者及同源重复证明直接删除；独立证明仅 ON，专用复制、遍历、摘要、序列化同时移出 OFF。
3. 优先改造结果物化，区分 CSR 数值消费与 native 产物消费，消除重复 native 构图、全图身份再投影及无消费者 timing 容器。必要 native 视图保持当前 generation、稳定 Arc 身份和原子发布，不能盲用旧槽位。
4. 按完整计时评估 net 负载/邻接维护、数据布局、报告路径共享及传播算法。候选先做针对性正确性与完整成本对照，再决定采用，不叠加无收益改动。
5. 完成独立结果对照、回归、运行剖析及协议采样；保留失败和负结果，更新检查归属与报告。

## 检查规则

不假设内部调用者会故意破坏流程已保证的状态，不为此重复全图验证。以所有权、事务顺序、稳定 ID 和失效规则保证正确性，不增加验证 token、通用校验框架或公开 skip-validation 开关。

外部输入解析、实际容量与数值失败、CUDA 状态、必要 owner/session/generation 绑定、提交、真实撤销、poison 和恢复继续执行。判断依据是调用者和消费者；混合函数拆开寻址与诊断，功能更新不得移入 ON。未执行诊断为 not_run。

## 验收与测量

- 独立 Release OFF/ON、无 CUDA、native/reference/CUDA 对照。保留 malformed、stale generation、真实 rollback、恢复后继续提交、查询失败重试和容量增长；故障注入仅 ON。
- 覆盖完整 timing/QOR/paths、winner、parallel arcs、epsilon-chain、多 clock/tag、连续不查询及查询后编辑；返回结果不能悬挂或陈旧。
- 按范围运行 native/parent、CPU sanitizer、CUDA memcheck/initcheck 和适用并发检查。旧错误也记为失败，不添加抑制项制造通过。
- 冻结 wide_2500002（1,000,000 实际单元）和 multiclock_2666692（1,000,008 实际单元）；CPU/full、CUDA/full、CUDA/incremental，8 线程、affinity 0–31，十批各100个 buffer，Release/OFF，每配置1次预热、3次采样。
- 百倍目标的主指标为 edit_sta_loop_ms：从第一次 buffer insertion 开始前，到最后一轮 STA 与提交结束。保留批次准备及提交内释放旧状态的成本，不将它们移出循环计时。
- 同时报告包含 backend setup、全部提交、末轮完整 timing/QOR/20 setup+20 hold paths 的消费者耗时；加载、初始化、清理及 cold end-to-end 单列。分解准备、传输、分层、传播、物化、报告，嵌套阶段不重复相加；初始化和末轮工作仍须优化，不能只展示循环加速比。
- 1/3 为参考测量，不替代 Stage15 正式统计门。prefix1 和剖析不计作协议样本；无物理RC、合法化、closed-loop、DEF/power/SDF发布的限制写明。
- 用实际调用、分配、传输及耗时证明 OFF 冗余消失，不用源码字符串、固定计数接口或缩减结果需求代替证据。

服务器沿用 Docker、tmux、空闲非0 GPU，共同512GB硬上限、swap=0。每十分钟检查；不覆盖活跃源码/二进制、不重采有效数据、不停止他人任务。大流使用 FIFO，保留紧凑证据，清理前核对路径和活跃依赖。README、用户CLAUDE、独立报告和依赖保持不变。

运行证据见[百万单元优化记录](million-cell-optimization-20261010.md)，状态见[实施记录](stage14.5-progress-report.md)。
