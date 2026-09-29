# Stage 12 实施记录

更新：2026-09-29。状态：本轮实现、正确性回归及参考测量已收尾；原严格高性能验收未完成。基线为 ECC aa33d82、ecc-tools 7cd621119；本轮按用户授权本地提交，native 提交为 ecc-tools 42b64be72，未 push。全部十三组参考数据绑定修复版 1ca4e4e8，每模式 1 次预热、3 次采样；百万节点四模式重测及全矩阵复核已完成。旧版本、额外样本和历次失败保留，不并入当前统计。严格性能门仍为 not_run。

## 当前修复版参考结果（1/3）

共享服务器参考结果不构成严格性能验收。时间为完整 trace 的消费者耗时中位数（ms），四项依次为 CPU/full、CPU/incremental、CUDA/full、CUDA/incremental。主指标包含编辑、提交、必要回传、物化及报告后处理；加载和清理另记。加速比为逐轮配对比值的中位数，方括号为固定 seed、10,000 次 bootstrap 的 95% 区间，不是两列时间中位数相除。

| 用例 | 四模式消费者中位数（ms） | CUDA/full 对 native CPU/full | CUDA/incremental 对 CUDA/full |
|---|---|---|---|
| picorv32a-q | 38733.938 / 20274.367 / 31043.243 / 6280.601 | 1.249× [1.244, 1.264] | 4.937× [4.835, 5.020] |
| picorv32a-d | 38938.083 / 17552.552 / 30935.550 / 6354.178 | 1.259× [1.255, 1.265] | 4.867× [4.864, 5.000] |
| wide_100000-data | 76966.716 / 85367.806 / 62363.485 / 15950.293 | 1.232× [1.212, 1.234] | 3.910× [3.805, 4.079] |
| multiclock_100000-q | 129009.297 / 42897.139 / 104060.817 / 23190.897 | 1.239× [1.238, 1.247] | 4.486× [4.076, 4.641] |
| xtea-q | 31.621 / 14.300 / 65.994 / 22.139 | 0.486× [0.414, 0.493] | 3.452× [2.883, 3.645] |
| xtea-d | 32.942 / 14.120 / 56.520 / 17.366 | 0.568× [0.562, 0.583] | 3.253× [2.591, 3.514] |
| usb-q | 485.577 / 152.180 / 531.429 / 124.354 | 0.912× [0.906, 0.919] | 4.274× [4.193, 4.325] |
| usb-d | 499.047 / 158.456 / 539.062 / 131.827 | 0.927× [0.805, 0.971] | 4.140× [4.026, 4.509] |
| zipdiv-q | 822.736 / 220.276 / 873.587 / 190.728 | 0.943× [0.942, 1.016] | 4.591× [4.483, 4.953] |
| zipdiv-d | 834.304 / 231.194 / 868.978 / 199.523 | 0.934× [0.927, 1.041] | 4.355× [4.227, 4.905] |
| multiclock_10000-q | 7694.347 / 5292.182 / 6474.297 / 2255.270 | 1.184× [1.163, 1.188] | 2.864× [2.863, 2.900] |
| wide_10000-data | 6471.360 / 8668.938 / 5568.822 / 1611.657 | 1.161× [1.156, 1.213] | 3.436× [3.392, 3.501] |
| wide_1000000-data | 1215356.140 / 1246637.512 / 997746.809 / 207562.606 | 1.228× [1.218, 1.257] | 4.652× [4.136, 4.842] |

小设计 CUDA/full 的负收益和 zipdiv 区间跨 1 的结果保留；宽层一万、十万及百万节点的 CPU/incremental 消费者中位数仍高于 native CPU/full。p95、MAD、原始计时、输入身份和 GPU 占用均保留在归档中。三个正式样本仅供参考，不能据此宣称稳定的生产加速结论。

百万节点的四模式生命周期中位数如下。加载包含 9.14 GB frozen replay 的解析；backend setup 已包含在原始 workload/cold 计时中，不能重复相加。各列中位数也不要求相加等于总量中位数。

| 模式 | 加载和初始化（s） | backend setup（s） | 清理（s） | cold end-to-end（s） |
|---|---:|---:|---:|---:|
| cpu/full | 945.119 | 6.402 | 26.248 | 2193.565 |
| cpu/incremental | 961.536 | 213.640 | 16.973 | 2444.283 |
| cuda/full | 1037.220 | 5.018 | 14.563 | 2105.083 |
| cuda/incremental | 957.390 | 6.514 | 15.994 | 1185.988 |

## 核验范围与剩余限制

- 独立 Release OFF/ON、默认无 CUDA 严格构建、native/parent 回归、隔离 binding、三设计 Q/D 与恢复检查通过。四个必测用例的逐批 native CPU/full 拓扑、timing、winner 和 levels 对照，以及大规模 OFF/ON 状态对照见下文证据；最终 ordinal 修复另完成 v185 回归和 v190 十批对照。
- 本轮采样与最终核验均退出 0。十三组共 208 次运行（含预热）的原始 SHA、实际模式、generation、无 fallback、清理状态、构建与线程配置、完整 trace 统计均已复核；这是实测记录数量，不是固定数量门禁。采样后对各轮保存的最终公开结果另作四模式比较，全部通过；该比较不证明未保存的中间 generation，逐批证明来自独立诊断。
- CUDA memcheck/initcheck/racecheck/synccheck 及独立硬件故障检查已执行。Nsight Systems 确认多 block、每 block 256 线程的传播及传输行为；NCU 性能计数器仍因 ERR_NVGPUCTRPERM 不可读，按用户要求记录。racecheck 不替代全局写入归属审查。
- CPU sanitizer 的原始 logger ODR 启动失败和限定 logger suppression 补验分别保留，不能宣称未抑制全通过。全仓及部分修改范围的 mypy 仍失败；失败分类见下文。请求 8 个 CPU 线程不代表实际使用 8 个 STA worker。多时钟百万节点预检超时及此前 CUDA 初始化错误也未抹去。

## 最终证据

服务器运行目录为 /home/qianhan/code/stage12-20260921-055547/reference13-new-v236；采样驱动退出 0，十三组全部完成。reference13-readback-v237.py 在现有 Docker 和共同 512 GB/swap=0 限制下复核，退出 0，未启动 STA 或 oracle。WSL 与服务器 130 个相关源码身份一致。

reference13-evidence-v237.tar.gz 已取回 WSL 的 ecc-tools/build-stage12-work/20260921-055547，SHA-256 为 cb5355e364d3c8566040317bf73b16b62a02c2009c338f3bfaa9fb4491dc08ca；513 个登记成员逐一核对大小和 SHA，通过后解包至 reference-evidence-v237。其中 reference13-readback-v237/readback.json 保存十三组统计及核验范围，samples.json 记录服务器原始输出的路径和 SHA。百万节点 samples.json SHA 为 2dbc9d23c0ce5ca3b7000c488749d7e98a3c5fd186c4c6850fcba585c7ff0a37。最终逐项收尾记录为同一运行目录下 completion-audit-final.json。

以下保留历次实施与测试记录；其中“进行中”“未完成”和旧采样协议只描述各自记录时点。

## 输入准备与预检记录（历史过程）

- 五个原始设计使用原 ICS55 配置独立综合并完成 Q/D 各十批 native CPU/full 预检。节点数为 aes 97,520、BM64 49,339、y_huff 41,981、picorv32a 29,183、APU 12,459；aes、BM64、y_huff 的 CSR baseline 数值资格预检失败；picorv32a 的 Q/D 四模式十批执行通过，按节点数成为最大执行成功候选，但随后与独立 fresh CSR/full 的 timing 比较失败，尚未取得正确性资格。APU Q/D 四模式执行通过，但 Q 的独立数值比较也失败。当时尚无取得正确性资格的真实候选；后续修复与实际冻结结果见下文，选择没有参考耗时。
- 固定宽层、多时钟规模网表已经生成。旧输入的两类十万规模（100,002、100,004 节点）完成 native 十批及四模式十批执行；宽层百万规模完成 native 十批，多时钟百万规模在 7,202 秒超时。随后发现生成 SDC 的部分集合写法未被当前 reader 展开，旧输入结果不具备预期约束，不能用于性能验收。已改为显式端口列表，在独立 synthetic-v2 目录重新生成全部规模；六份网表的 SHA-256 保持不变，只修改约束表达。小规模实际加载检查通过，两类一万、十万规模的新输入均完成 native 十批预检；新版宽层百万规模完成 native 十批（1,000,002 节点，4,237.700 秒）；多时钟百万规模（1,000,004 节点）在 7,202.468 秒超时。十万宽层的旧实现 targeted 完成，但独立 fresh 在 3,600 秒超时；日志保留。
- 同一 OFF probe 可运行 native CPU/full、CPU/incremental、CUDA/full、CUDA/incremental，并逐批取得 timing、完整公开 QOR 和限定数量 paths。默认正式采样仍为预热 5、采样 30，完整 trace 为配对单位。
- 消费者样本单列加载/会话初始化、backend setup、提交、查询物化、消费者读取、清理和 cold 成本。CPU/full 的 analyze 位于提交区间，其他模式位于查询/后处理区间；主消费者区间可比，分项不视为相同工作。
- 统一 samples v2 保存原始文件、二进制 SHA-256、实际 GPU UUID/driver/runtime、线程与 affinity、固定轮转和配对 bootstrap。普通性能的正确性/详细诊断均为 not_run。

## 已发现并修复的问题

- 连续大批次会访问前批创建的邻接节点。CPU targeted capture 原来强制将它解释为 ExistingNodeRef，导致第二批拒绝。现按真实 creation-token binding 解析，保留 slot、key、高水位和 tombstone 检查。原失败、小回归及修复后十批结果均保留。
- 测试 loader 的 baseline 仍执行功耗分析并写 power/SDF，原 timing report 选项不足以兑现无文件工作负载。现在通过现有测试会话注入点使用内部 timing-only 编排；生产默认顺序、授权、状态推进及失败处理保持原行为。已验证独立 fresh 对照、public 输出和实际目录无额外报告。
- trace 生成曾遇到 canonical edit 顺序、real replay comparability、seed 与 token ordinal 不匹配；已修正生成器并重新预检，未放宽 parser。
- 容器不提供 taskset，首次 affinity 启动未执行工作负载。已改用 Python 标准库 sched_setaffinity/exec，真实子进程测试与服务器 affinity 均已核验。
- replay parser 曾通过虚构 Stage 3 trace 复用 value codec，每批复制完整 pre/post identity，再 dump/parse。现直接共用内部 codec，保留外部 closed schema、重复 key、身份及 token 校验，并明确校验 accepted driver 必须来自早先实际 round。现有 wire 格式不变，输入自身重复 baseline 的成本仍需实测。
- 独立审查发现采样后未复验输入、cleanup 早于 replay/临时目录析构。已保存采样前 manifest 身份并在统计前复验全部输入；批次数检查后立即释放完整 replay DOM，对象存活检查确认子进程运行时不再持有；内层作用域释放完成后计量清理，显式清理失败阻止成功记录。新增篡改 canary 和实际目录清理检查，独立复审通过。
- 规模启动的 GDB 栈停在 JSON DOM 回调解析器；其每个对象结束都会扫描父数组，导致对象数组二次遍历。三个入口改用公开 SAX 拒绝重复键，再普通 DOM 解析；不修改 vendored 库。保留 typed error、Unicode 等价键、嵌套和各入口注释规则，严格构建及现有契约通过，独立审查无阻断项。四万个对象的独立解析对照为旧路径 333.878 ms、新路径 39.837 ms，结果完全相同；这是解析开销证据，不是 STA 性能验收。旧规模运行在 2,711 秒时取消并保存原因；随后完成修复入口重跑。
- 解析修复后，十万规模 GDB 栈进入负载捕获：每个 pin 重扫计划请求及 committed nodes，另有 capacitance、start/end 和 arc multiplicity 的重复搜索。改为单批局部索引、resolver 槽位加完整 key 核对，保留输入、旧值、新增声明和跨集合 ref 冲突检查；删除两个无调用 helper。全局 start/end、旧 capacitance 仍有一次扫描，未声称所有工作只与编辑数量有关。严格构建及针对性测试通过后，独立审查发现非法 NodeKind 在有序集合比较器抛异常的 typed-error 回归；已改为先验证再插入并补两请求 canary，修复后的无 CUDA、OFF/ON 严格构建与对应测试均通过。新的 GDB 栈随后定位到 arc bijection 对每个语义组重扫全部请求/候选；已改为一次分组，保持组序、native candidate 顺序和并行弧 stable-ID tie-break。新增多组并行映射、非等价歧义和缺候选用例通过，独立审查无阻断项；修复后同输入四模式十批运行完成。原先 180 秒仍停在捕获中的 GDB 单批运行，修复后在期限内正常退出并写出消费者结果；GDB 驱动在程序已结束后执行 kill，自身退出码为 1，不能误记为工作负载失败。剖析下的约 42.3 秒消费者耗时仅用于定位，不属于正式样本。
- 合成设计生成器原先使用 all_inputs/all_outputs 和通配端口名，当前 native reader 不展开这些集合，导致预期 input transition、output load 及部分 output delay 缺失。改用显式端口列表，不扩展 SDC parser。实际 native 导出的全部输入 transition、输出 delay/load 和 clock binding 均核对通过，两类小规模输入的公开 QOR 和 paths 非空。旧结果保留并作废性能资格；新版规模输入与 trace 重新预检后才能冻结。
- 独立审查发现冻结脚本仍引用旧合成输入、先选最大执行成功候选才检查正确性、将可选百万规模失败视为全局阻断，并缺少六条小设计 trace 的身份。现改为先筛独立正确性合格集，再按节点数和名称排序；必过规模绑定新版 trace/SDC/网表与实际约束验证，可选失败另存状态，xtea/usb/zipdiv Q/D 保存具体文件身份。实际拒绝检查确认当前没有合格真实设计时不会写出 frozen-inputs.json。复审补齐实际 replay 与 sidecar 一致性、generation 元数据前后摘要、校准 Q trace 身份，以及四模式实际执行验证；最终静态复审无遗留阻断。弱证据版本 v3 在首个用例完成前取消，保留原因，v4 重新运行，尚未取得通过 verdict。
- CPU/CUDA baseline 原来以笼统“timing unavailable”掩盖底层失败；现在保留已有 computation token，未改变数值规则。
- 准备中的编译、lint、脚本转义、错误 target/CLI 参数和环境启动失败保留原日志；修正后分别重跑。Nsight 容器缺 importer，已用服务器现有同版本 importer 成功转换原始 qdstrm。

## 真实设计资格与优化前证据

AES Q 在 native CPU/full 十批通过，但 CPU/incremental、CUDA/full、CUDA/incremental 的未编辑 baseline 失败，不能入选必过真实设计。临时诊断定位到 NAND3 弧：输入 slew 3.468687733 ns、负载 0.150687463 pF，均远超相应 Liberty 表最大轴 0.795659 ns、0.0136827 pF，正表格双轴外推得到 slew -0.566435197 ns，触发 numeric_failure。原输入不修改、不截断外推、不放宽必要检查；已经提取最小数值回归。BM64、y_huff 也被既有 numeric_failure 拒绝，完整错误保留；未将这些拒绝计为 CUDA 功能通过。

提前启动的 AES 线程校准已停止并明确作废，没有正式样本或配置选择结果。picorv32a Q/D 四模式执行通过后，使用修正清理计时的 OFF probe，按原校准规则完成新运行，固定 affinity 0–31；1/8/16/32 线程的完整 trace 消费者中位数分别为 66,048.918 / 62,689.779 / 59,128.460 / 61,850.743 ms，该候选的校准选择为 16 线程。因其后独立正确性预检失败，此配置尚不能作为最终冻结结果；若最终候选改变，须按原规则重新校准。该结果不代表加速验收。所有校准档位的 /proc 活动抽样均只观察到一个活跃线程；请求 16 不等于 STA 使用了 16 个 worker。

picorv32a Q 十批的 CPU mixed 与独立 fresh 在 graph/reference 逐字段一致后，弧 graph_delays.values[314749] 比较失败：0.06046321937698816 与 0.06046335678287189，超过原 1e-9 数值阈值。完整输出和失败 verdict 已保存。最早观测到的差异涉及一个 NOR2 输出及四个扇出节点，slew 差约 8.53e-7 ns。APU Q 的 graph_delays.values[137269] 同样失败：0.0982476579194514 与 0.09824775731460604。未放宽 tolerance，也未将执行成功记为等价性通过。

八节点实际 CPU backend 复现确认了既有语义冲突：同一图的 full FIFO 为 0,1,6,3,7,2,4,5，mixed 为 0,1,6,7,2,3,4,5；两个候选 slew 为 0.1 和 0.1000005，现有 epsilon 折叠分别保留 0.1000005 和 0.1。保留各模式旧候选顺序不能普遍保证原 1e-9 独立等价门。从原始 execution_trace 提取真实混合层遍历顺序后，两设计的 Liberty 候选折叠均精确重现观测差异：picorv32a 为 mixed B→A、full A→B，得到 0.1395596320521876 / 0.1395604850765842；APU 为 mixed B→A→C、full B→C→A，得到 0.3335972975198598 / 0.3335981435612793。公开 receipt 的 level_nodes 已按语义名称规范化，不能拿它推断实际访问顺序。用户已明确不统一候选顺序，采用 stable ID 等局部机制。实现改为每节点结果 lane 先确定数值极值，再在原 epsilon 窗内按 seed、已有入边行内序号和输入 transition 选择实际候选，不新增全局排序、ID 表或前驱重映。CPU reference、独立 native、CUDA 各自实现该规则；当前支持的 data-only insertion 保留旧行槽位及 Liberty 并行弧序号。

优化前 wide_10000 十批 Nsight 记录显示 full/incremental 的 propagate 均为 grid=1、block=1；incremental 的 patch/undo 也为单线程。此一次剖析中，incremental 有 4,457 次 cudaMemcpyAsync，full 有 233 次，保存原始时间线及 SQLite 摘要。该运行用于定位和前后对照，不是正式性能验收。修正约束后又以 synthetic-v2/wide_10000 重新采集 OFF 十批、完整 QOR/paths 的 Nsight 基线；实际执行记录和公开结果非空检查通过，传播仍为 grid=1/block=1。full/incremental 的 cudaMemcpyAsync 分别为 233/4,457 次，stream synchronize 为 65/93 次，cudaMalloc 为 78/72 次。原始 qdstrm 经现有同版本 host importer 成功转为 SQLite；两次均不属于正式性能样本。

Nsight Compute 已尝试服务器现有 2025.1 CLI；GPU 4 被他人占用时按规则拒绝启动，改选空闲 GPU 7 后，驱动以 ERR_NVGPUCTRPERM 拒绝硬件计数器。用户已明确本轮记录权限阻塞，不修改驱动/容器安全配置。SM/活跃 warp 计数器证据标为未取得；Nsight Systems 时间线可继续使用。额外 CPU perf 采样也被现有 perf_event_paranoid=4 拒绝，未改系统参数。

## 并行改造前的验证记录（历史）

最新捕获修复 v21 已完成顺序严格构建及全部已启用 ista 回归：默认无 CUDA 145 项、CUDA OFF 158 项、ON 185 项，以及单独运行的 5 项故意硬件故障测试全部通过。三模式 binding 重新构建、隔离保存并核对实际加载路径与只读状态；parent 364 项及四模式实际 smoke 通过。回归驱动首轮遗漏尚未构建的 target，并使用了共享目录里前一模式 binding，造成未执行/配置断言失败；日志保留，修正驱动并顺序构建隔离后完整重跑通过。本轮 CPU sanitizer 的 Release/O3 配置在 CsrFifoLevelization 的 vector 初始化处触发 GCC 14 array-bounds 严格警告，构建失败。同 GCC 的 O1/调试符号配置保持严格警告并完成构建，但七项测试均在启动时被 libidb/libtcl 中重复的 logger singleton 定义拦住，原始 ASan 检查记为失败。相关源码与链接文件均与 Stage 11 基线相同；Stage 11 也已有同名 ODR 抑制记录。另以仅匹配 _log_instance 的 ODR 抑制补跑七项测试，ASan/UBSan 全部通过，未关闭内存、泄漏或未定义行为检查；这项补充结果不替代无抑制检查。CUDA contract、mixed、fallback 分别通过 memcheck、initcheck、racecheck、synccheck 共十二项，所有报告为零错误/零 hazard；传播尚未并行化，不能据此宣称未来并行实现无竞争。ON benchmark 实际在读取不存在的输入之前拒绝采样，未产生结果文件。新版百万规模预检结果见上。旧语义的规模资格测试已保存超时及部分日志并取消，后续使用修复后的独立二进制重新验证。

Release OFF/ON 的 prerequisite probe 构建、native/full 事务、已创建 peer 回归通过；省略 CUDA/debug 选项的默认构建及 ecc_py 产物构建通过，当前默认构建全部已启用的 ista 回归通过，诊断专用测试按 OFF 禁用；CUDA OFF/ON binding 已顺序构建并隔离，实际导入状态、四模式 smoke 和无设备拒绝通过；默认隔离 binding 的 parent 回归、chain/diamond 的 CPU/full 与 CPU/incremental 真实运行及 CUDA unavailable 拒绝通过；ON 两批 full/targeted 与独立 fresh 比较及 public 检查通过。修改 Python 的行为测试、schema 统计自检、lint 和差异检查通过。修改文件 mypy 同口径基线为 64 个错误，当前为 63 个，保留两份完整日志；未宣称类型检查通过。原始全仓 mypy 被第三方文档的重复 conf 模块阻断；排除 thirdparty 后 ECC 自有目录检查报告 247 个错误、涉及 48 个文件，完整日志单独保存。独立代码审查未发现 timing-only 修复的新阻断项。

新增跨前沿 FIFO 唤醒序、跨 block 汇聚及重复执行、深链、epsilon-chain 和负 slew 外推 contract 在现有 CPU/CUDA 实现通过；直接 codec 的 contract 和 Stage 6 frozen replay 回归通过。真实设计独立对照已暴露上述数值失败，修正约束后的固定规模资格仍在进行；候选 picorv32a 线程校准已完成，但最终 host 配置尚未冻结；优化前 Nsight 基线已保存。当前精简 Docker 不含 CUB；已复制服务器现有 CUDA 12.8 自带 CCCL 2.7 头文件到独立运行目录并逐文件核验，扫描、压缩、分段/全局排序及 max 原语在原 GCC/CUDA 下严格编译通过，无依赖升级。完整输入/线程 manifest 尚未冻结；并行计算、传输合并、最终 OFF/ON/noCUDA 回归、sanitizer、正式性能门均未完成，不作加速结论。

## 局部稳定候选改造记录（历史）

- 数据 slew 的 epsilon-chain 用例在旧 CPU 核心上复现错误；修复后 CPU 和 CUDA contract、full/mixed session、fallback 的针对性检查通过。测试曾错误打乱受约束的输入根顺序，已改用现有合法层序注入入口；不放宽生产校验。
- Arrival/path 改为目标节点汇集候选，CPU 与 CUDA 的数值 contract 通过。两项 ON 会话检查的旧出边审计已迁移为真实入边审计，复跑通过；时钟路径采用相同规则，保留 clock-stop、owner 和 CRPR 前驱。所有候选 scratch 限于单个节点并复用；没有保存全图候选索引。
- Release 链接曾读到 sanitizer 的第三方解析 archive：这些 archive 输出在共用源码目录，独立 build 目录不足以隔离。保留污染产物与错误日志，从 Release 自有对象恢复后构建、数据 slew 回归通过；后续 sanitizer 必须隔离源码输出，不能仅隔离 binding。时钟新代码一次因旧 DTO getter 非 const 编译失败，修复限定符后重跑。
- v34 的 CPU/CUDA 候选契约、full/mixed session、fallback 全部通过；CUDA contract/mixed/fallback 各自的 memcheck、initcheck、racecheck、synccheck 十二次检查通过。新增时钟 epsilon-chain 在六种合法层序上保持完整值及前驱一致。一次设备非法读取定位为新增手写测试 fixture 漏填入邻接，补齐 fixture 后重跑通过；未删除生产边界检查。
- v35 默认和 OFF 回归除 binding 配置混用外通过；v38 通过独立链接隔离产物，确认真实路径和 CUDA/debug 标志，binding、parent 及四模式 smoke 通过。删除共用 binding 的尝试被自动审批拒绝且未执行；之后直接链接到新隔离目录，不删除既有产物。
- v37 实际完成 picorv32a、APU 的 Q/D 四模式共十六个十批工作负载；驱动将 mode 写为 cpu-full 而验证器要求 cpu/full，导致其原始 verdict 误报失败。v39 使用正确标签复验保留的原始输出，十六项公开 QOR/paths、请求与实际模式、无 fallback、生命周期和计时字段均通过，没有重复生成或替换原始样本。完整 topology/timing/winner 的独立资格仍由 v40 验证，不能以公开汇总通过替代。
- v41 ON 严格构建完成，183 项非 binding/故意硬件错误回归中两项 Stage 5 差分仍读取旧 probe，报 traversal 计数不符；其余通过，另五项故意硬件错误和隔离 ON binding 通过。构建驱动曾只提取 CTest 的首个命令，漏掉 Python controller 参数内间接调用的 probe；v44 补构建后两项 controller 通过；另两项测试因 CUDA build 中缺少 GPU 标签，被错误放入无设备容器执行。补齐标签后 v45 的十六项设备回归全部通过。v51 默认/OFF 的完整间接 probe 严格构建与非设备回归通过；原始失败日志保留。
- 独立并行设计复审确认入边 gather 不需要统一 full/mixed 候选顺序；现有 endpoint 与每弧 ChildState 已有唯一归属，无须新增分组或锁。待实现项为按层调度、同 stream 阶段依赖、线程局部 status 后原子归并及 ON 无竞争审计；现有 mixed reconstruction 的共享 status 读取也须迁移。
- v40 已完成 picorv32a Q 十批完整资格：CPU/incremental 与独立 fresh/full、CUDA/full 与独立 fresh、CUDA/incremental 与 full 每批比较均通过，原候选差异消失；D 与剩余输入资格仍在进行。新的 CPU/full 校准 v4 在 affinity 0–31 下得到 1/8/16/32 请求线程中位数 40,693.620 / 40,212.114 / 40,532.814 / 41,435.313 ms，按既定规则选择 8；最终输入资格尚未冻结，此结果不作为加速验收。
- GDB 原生栈进一步定位到独立 fresh 的 resolver coverage：每条 arc 重扫全部 bindings，每个 node/net 反向线性搜索。改为单次局部名称/端点分组，组内继续执行原完整身份匹配，不删除覆盖检查，不建立长期索引；同端点并行弧组仍需匹配，未宣称最坏复杂度线性。独立复审通过。新增错 parallel ordinal、重复 node name、缺失 net canary；首次 fixture 错用完整数值导出而被 net projection 正确拒绝，随后图/数值记录类型转换编译失败，修正后 v54 无 CUDA、OFF、ON 三套严格构建与三项相关测试通过。隔离 fresh probe 的真实 picorv32a prefix 1 正常完成（147.222 秒，含输入和诊断序列化，不是性能样本）。
- 修复后 GDB 栈已越过 resolver coverage，进入测试 oracle 的结果转换：NodeKey/ArcKey、native node/arc 及 tag 查找仍逐项线性搜索有序表。现直接使用标准 lower_bound，保留完整相等与范围检查，不新增索引或复用计算过程。调用者及 canonical 排序契约的独立复审通过；v63 三配置严格构建、scatter 契约/原子性/属性回归通过。新增 canary 曾误用无 path 的 parallel fixture，随后又错误要求 predecessor 与 seed path 位于同一节点；改用现有 diamond 并分别验证两类真实消费者后通过。隔离 probe 的 picorv32a Q 十批在 431.941 秒完成；v64 与修复前保存的完整 fresh graph/timing 精确一致。该耗时含加载和诊断输出，不是性能样本。
- Python descriptor replay 对每条 appended arc 扫全部 BaseOut/BaseIn/Aux，改为每个 descriptor 各扫描一次，仍保留实际出现次数、错误端点和 foreign-row 检查。新增重复及跨行 canary、200 组旧/新行为对照、Stage 5/6 六项 controller 回归通过，独立审查无阻断。10 万行、300 条 appended arc 的同次调用剖析由 37.581 秒降为 0.071 秒；仅证明诊断扫描开销变化。ruff 通过，单文件 mypy 修改前后均有 13 处既有错误；新增检查中的闭包及类型问题修复后未增加错误。
- 两个 fresh probe 角色实际调用同一独立 native CPU/full replay 和 serializer。后续资格驱动保留一份 fresh 结果分别对照 CPU/CUDA，删除重复子进程；未共享 targeted 计算。v55 的完整 targeted 输出保留，尚未完成的旧线性 oracle 运行取消并记录原因；v69 复用原始输出、重新执行全部验证，使用修复后的 oracle 和批次邻接扫描。所有这些调整仅影响开发验收，不进入 OFF 性能。
- 完整候选代码独立复审未发现阻断：native、CPU CSR、CUDA 的极值窗口、实际 winner 值及 predecessor/tag/CRPR 身份一致；并发安全仍待共享 status 和 ON 审计改造。full Kahn 采用前沿稳定出边位置与 CUB 稳定压缩，无须排序或持久全局 rank。
- patch/undo 独立并发审查确认，host 的物理槽位、Arc 写集合、Aux 行及 incidence 校验已提供唯一写入位置，无需再建全局去重表。需将 payload→slot、Aux 内容→metadata 分成同 stream 阶段，status 读写统一适配并发，restore 不受失败 status 阻止。原“第二项 payload mismatch”不能证明并行线程已发生部分写入，测试改为前序 Base remove kernel 先完成修改、后续 payload kernel 再失败；ON 直接观察成功修改和恢复，随后重新计算检查设备状态。v73 OFF/ON 严格构建及 full/mixed 会话全部通过，独立复审通过。
- v71 在候选修复后的 OFF 二进制、显式端口 wide_10000 输入上补采串行 Nsight Systems，请求 8 线程、affinity 0–31；完整消费者结果与 schema 校验通过。full/incremental 的传播仍为 1×1，异步复制 233/4,457 次、stream 等待 65/93 次、分配 78/72 次。原始时间线、二进制和输入身份均保存，未把单次剖析作为性能样本。
- 上述针对性结果不替代三设计、真实候选、全部回归和最终性能验收；该轮传播仍为单线程。Nsight Compute 权限阻塞继续按用户要求记录，不修改系统权限。

## 证据

本地工作记录：chipcompiler/thirdparty/ecc-tools/build-stage12-work/20260921-055547。
服务器运行根：/home/qianhan/code/stage12-20260921-055547，保留源码快照、输入身份、生成与预检命令、原始输出、失败及重跑日志。所有任务通过现有 Docker/tmux，项目共同硬上限 512 GB、swap=0。usage 不保存验证日志。

### 诊断回放复制收尾（v75）

回放只复制会修改的外层映射、节点记录和 Base 槽位；只读 model/table/key 不再递归复制。计划格式规范化也只复制会替换的容器。新增实际 net_name 撤回、故意损坏 payload 后全部原始输入不变的 canary；没有删除比较。独立代码审查确认共享记录没有写入者。

同一份 10,002 节点、十批原始 receipt 的控制器剖析从 146.979 s 降到 60.437 s；这是 ON 诊断耗时，不是 STA 性能结果。修改前 deepcopy 累计约 90.593 s。Stage 5/6 自测及六项控制器/冻结差分回归通过，修改文件 ruff 通过；transaction validator 的独立 mypy 修改前后均为既有 9 个错误；descriptor validator 新增的自测类型推断错误已修复，复验剩 8 个错误（修改前 13 个），未宣称类型检查通过。证据位于运行目录 validator-profile-v74/、validator-profile-v75/ 和 descriptor-regression-v75/。


### 输入冻结与首组并行实现（2026-09-22）

输入清单已写入运行目录的 frozen-inputs.json，SHA-256 为 709cf14b071c56a7334a577fb7d8d3706bfb1d35c07864b4a407aef5d3f99944。必过对象固定为 picorv32a Q/D 十批、wide_100000 与 multiclock_100000；CPU 请求 8 线程，affinity 0–31。十批合法编辑、四模式公开结果预检及合成约束核验已完成；完整最终正确性与正式性能验收仍为 not_run。历史文件字节哈希未采集，不以 mtime 代替；冻结依据包括原生语义绑定、保存的 native trace、命令与实际模式记录、当前输入完整 SHA。

picorv32a D 的优化前十批 targeted/fresh/CUDA full/incremental 差分通过（stable-real-qualification-v56）；与此前 Q 证据共同保留。仍在运行的规模完整证明使用隔离的串行 probe/validator，避免协议迁移污染基线。

parallel-patch-v80 的 Release OFF/ON 严格构建及各四项 CUDA 契约通过。已并行化独立 patch 写入、实际 undo capture/restore 和唯一 seed 初始化；共享 status 使用原子读写，helper 可使用线程私有 status 后归并。新增 513 条编辑、32/128/256 线程 launch、并发多错、真实部分修改回滚、事务放弃及重复 end 拒绝。独立静态审查无阻塞；此组结果不代表传播或 Stage 12 已完成。

并行 full Kahn 首次构建（parallel-kahn-v81）因 Nix 拆分 Toolkit 未暴露 CCCL 头文件失败。修复 CMake 查找并复用此前已校验的 CUDA 12.8 CCCL 副本，不下载或升级依赖；后续结果以实际运行记录为准。


parallel-kahn-v82 已在 Release OFF/ON 严格构建及各四项契约通过；保留 FIFO 前沿、cycle 和失败恢复。parallel-propagation-v84 将弧初始化、clock/顺序发射、按层 slew/arrival、endpoint 与逆层 required/slack 并行化，OFF/ON 同组回归通过，独立并发审查未发现阻塞。候选仍为节点局部选择，不建立跨模式排序表；clock 清单准备、按 domain/level 排序、上传、CUB scratch 和层次 launch 均属实际算法成本。

parallel-transfer-v85 的 OFF/ON 严格构建与同组回归通过：patch 上传区持久复用，追加 BaseOut/BaseIn 分别连续上传，Aux 通过描述符批量发布；扩容旧缓冲在必要同步点统一释放。后续宽层/launch 形状、CUDA sanitizer、真实设计、跨构建及正式性能验收仍须完成。

遥测区分 explicit_kernel_launches（本工程显式启动）、device_algorithm_calls（实际 CUB 调用，不含 scratch 查询）和 levelization_decision_bytes。前两项不得相加解释为 GPU 总 kernel 数，实际总数另由 Nsight 提供。当前 CUDA full trace/verdict/performance 为 v4，targeted/incremental 为 v5；消费者原始记录为 ista-consumer-sample/2.0.0，合并样本仍使用 samples v2，旧串行证据保留原格式。

### 并行版首轮完整回归（v86–v90）

跨 block 宽层、汇聚、并行弧、epsilon-chain 和 payload/slot/undo 的不同 launch 配置测试通过。独立审查未发现并发或生命周期阻断项；审查发现真实 clock/顺序发射/check 的 launch-shape 覆盖不足，已复用真实 replay 的恢复流程，以原执行 256、恢复执行 37 线程逐批比较完整设备状态及公开结果，正在运行三设计 Q/D 与多时钟规模用例。

v88 严格构建与回归：Release ON 183 项、OFF 156 项、默认无 CUDA 144 项通过；故意硬件错误单独运行通过。并行版本 contract、mixed、fallback 的 memcheck/initcheck/racecheck/synccheck 共 12 个执行均通过；这些结果不能替代全局内存写入归属审查和真实规模对照。v87 驱动误写了不存在的构建目标，构建未启动即失败，v88 修正并保留原日志。

三种 binding 已顺序构建、隔离到 bindings/parallel-v89 并核验真实路径与只读状态；CUDA 两种 binding 的无设备拒绝通过。修改 Python 的 ruff 通过，统计/schema 自检与性能入口行为测试通过。v90 同口径类型检查仍失败，完整当前/基线日志在 parallel-local-v90；不宣称通过。

冻结前串行 wide_100000 的十批诊断、实际约束及四模式公开结果对照最终通过，原始证据保存在 qualification-inputs-v69。其结果只作为优化前正确性基线，不是新并行版本或性能验收。正式 5/30 性能门和全部真实规模最终验收尚未完成。

CPU ASAN/UBSAN 的 v91 原始运行仍被已有 logger 单例 _log_instance 的 ODR 冲突阻断；仅屏蔽该符号的补充运行 13 项通过，不能把它写成未屏蔽运行通过。测试配置将 LEF/DEF 输出重定向到独立目录；随后统一 CMD_BUILD，使 sanitizer 测试程序也写入其构建目录。Release 三构建本来已使用独立测试输出，未受该公共 bin 中测试程序的影响。

本次修改 Python 的同口径 mypy：基线 104 个错误、当前 98 个，完整日志均保留；全项目自有代码及测试在明确 package bases 后为 270 个错误、60 个文件（244 个源文件）。直接调用最初被重复 conftest 模块阻断，原始失败也保留。不改动本阶段以外的类型问题。

独立性能入口复审未发现阻断：native CPU/full 使用实际工作负载，四模式消费者计时覆盖相同结果需求，完整 trace 配对与缺样本拒绝有效，OFF 不启动 oracle。CUDA/full 预热和正式样本均校验协议、批次及遥测；ON 的 native/controller 两级入口已实际验证采样前拒绝。正式性能结果仍未取得。

### 并行运行剖析（v94）

相同 wide_10000 十批输入、8 请求线程和 affinity 0–31 的 OFF Nsight Systems 已完成。传播实际使用 block=256、多个 grid 规模；CUB 内部 kernel 也出现在时间线中。incremental 的异步复制从串行基线 4,457 次降到 546 次，stream 等待从 93 次降到 88 次；分配从 72 次变为 81 次，新增持久前沿/传播 scratch 属于真实成本。full 的复制从 233 次变为 1,092 次、等待从 65 次变为 458 次，主要为并行 Kahn 的必要前沿决策读回；没有在每个传播层加入 host 等待。两模式最后几批的容量分配为零或仅实际扩容。

此次 full/incremental 消费者耗时约 7.66/1.77 秒，GPU kernel 总时长远小于消费者时长，后续继续剖析主机提交和物化。单次带剖析运行不作加速验收；硬件计数器仍受权限阻塞，不能据 launch 形状宣称测得 SM 利用率或活跃 warp。原始 qdstrm、host importer 产物和 SQLite 保存在 parallel-profile-v94。

### 主机导出瓶颈与最小修复（v98–v99）

Pico Q 的四模式 1 次预热、1 次采样完成，消费者样本分别为 CPU/full 43.67 秒、CPU/incremental 21.83 秒、CUDA/full 44.94 秒、CUDA/incremental 7.66 秒。CUDA/full 尚未显示正收益；这是短 smoke，性能门仍为 not_run，不从单样本区间推断正式置信结论。

复用现有分阶段输出进一步发现，CUDA/full 十批导出耗时 35.72 秒、native 构图 4.69 秒，消费者合计 48.49 秒；这一独立剖析不与前述样本混算。受控 exporter 末尾还执行完整 validator，重复遍历并重新生成身份。已将该证明移入 ON，并在原 clock reachability 遍历中补齐不同 owner 的必要拒绝；新增 raw-native 重叠时钟 canary，公开 validator、数值边界和失效指纹保持。三文件独立复审通过，随后 v99、v101 的三套严格构建与回归通过。

首次主机阶段剖析因 GPU 5 已被他人占用而由 launcher 拒绝，未抢占；改用当时空闲 GPU 1 后完成。证据保存在 parallel-smoke-v94、parallel-host-phases-v98 和对应启动日志。
### 最新回归与消费者短样本（v99–v110）

v101 使用导出修复后的代码完成 OFF、ON、默认无 CUDA 的严格构建、已启用 native 回归、顺序构建并隔离的 binding、parent 回归和四模式 smoke。xtea、usb、zipdiv 的 Q/D 在 OFF/ON 下完成 full/mixed 完整状态、恢复后继续提交，以及每个 prefix 的公开结果对照；结果与 v89 保存的独立 native oracle 一致。多时钟一万节点十批的正常 256 与恢复 37 线程布局逐批完整相等，覆盖两个实际 clock/tag、非零 clock-to-Q、寄存器 endpoint check 和完整 QOR。公开路径是每种 analysis 最多 20 条，部分路径的 check_type=none；辅助证据脚本最初错误要求选出的路径都有 setup/hold 寄存器 check，失败记录保留，v110 按实际结果分类，未改变数值比较或生产行为。

v103 的四项输入导出、支持范围及 poison 相关 ASAN/UBSAN 测试在无抑制情况下通过；这不替代前述 v91 中受已有 logger ODR 冲突阻断的较大测试组。v109 在实际 full 两批消费者入口设置函数断点：OFF 完整 validateReferenceInputForSession 调用为 0，ON 为 6，两者进程正常退出且公开结果相同。v104 同一证据已通过，后续等待脚本状态竞态误触发重复目录拒绝，保留失败并使用独立 v109 目录重测，没有覆写已取得的原始证明。

导出修复后 picorv32a Q 的四模式 1/1 短 smoke：CPU/full 41.413 s、CPU/incremental 22.312 s、CUDA/full 31.105 s、CUDA/incremental 6.507 s；对应单样本比值约 1.33 和 4.78。分阶段导出耗时由 35.716 s 降至 19.700 s。短 smoke 的 performance_gate=not_run；不能将单样本退化区间当作正式 95% 置信结论，也不替代冻结必过用例的 5/30 验收。原始结果在 parallel-export-perf-v100。

### 规模诊断 root seed 扫描（v107–v115）

实际 multiclock_100000 receipt 有 12,504 个 seed、50,016 条根路径。旧比较器对每条根路径扫描所有 seed；32 条真实根路径的 cProfile 记录 800,352 次 canonical/JSON 编码，总计 3.685 s，其中编码链累计 3.273 s。现仅在一次路径比较内按 canonical seed node 分组为列表，保留同节点全部 tag、重复项、原匹配顺序及 matches == 1，不增加全局候选索引。相同 32 条匹配包含分组准备耗时 0.077 s。此结果仅说明 ON 验收工具开销，不属于 STA 加速。

既有完整比较 self-test 和新增同节点不同 tag、重复匹配 seed canary 通过，独立复审通过，ruff 与两仓库差异检查通过；两文件同口径 mypy 修改前后均有 8 个既有错误。最后覆盖本阶段全部 13 个修改 Python 文件时，ruff 通过，mypy 仍报告 105 个错误、涉及 8 个文件；新规模生成器、性能行为测试和 parent 会话测试未报类型错误。首次文件发现误包含用户原有报告中的源码副本与渲染脚本，因重复模块及其 lint 问题失败；原日志保留，未修改这些报告。未宣称类型检查通过。后续回读 type-audit-v208 确认两份源码基线均对应 ecc-tools 7cd621119：九文件同范围 104→98 的诊断多重集没有新增项，winner 的八条诊断前后相同；扩展范围的 105 条来自 98＋新纳入的既有八条−一条导入错误，不能解释成新增七个类型缺陷。后来调整过的 parent 会话测试单文件补查通过；整体类型检查仍未通过。保留的旧规模原始结果重新执行完整验证；已通过的逐 prefix 原始档案核验 SHA 后复用，其余 prefix 仍由独立 native CPU/full 进程计算。旧二次扫描进程的中断原因、排队竞态和未完成输出保留，未计为通过。

当前持久会话依次为 stage12-qualification-v111（串行规模资格收尾）、stage12-fresh-v112（独立逐 prefix oracle）、stage12-scale-v113（并行 full/mixed 与 oracle 比较）和 stage12-formal-v114（全部前置通过后正式采样）。正式采样继续固定原 manifest、5 次预热、30 次采样、四模式轮转及整条 trace 配对；不修改必过对象。GPU 选择使用真实 compute process 与利用率，驱动空闲显存不作为占用进程；正式采样额外保存外来进程监测，受污染的运行不能通过资源条件。所有任务共用 512 GB 硬上限、swap=0。Stage 12 仍未完成。

截至本次检查，parallel-fresh-v93/picorv32a-q/verdict.json 已记录十个 prefix 的 CPU incremental 与独立 native CPU/full 全量对照通过。multiclock_100000 的串行资格续跑已越过同项完整比较并进入 CUDA/full 原始工作负载；其整体 verdict、并行规模验收及正式性能门仍未取得。

### 全部必过正确性与旧资源监测重跑（2026-09-23，后续已切换参考测量）

parallel-fresh-v93 和 parallel-scale-v113 的最终 verdict 均通过：picorv32a Q、D、wide_100000、multiclock_100000 各十个 prefix 分别完成 CPU incremental 与独立 fresh native CPU/full，以及 CUDA/full、CUDA/incremental 与该独立结果的完整比较。CUDA 两路径相互比较、真实 mixed 执行、无 fallback 和设备图检查也通过。串行 multiclock_100000 资格续跑 qualification-resume-v111 同样通过；这些结果分别属于正确性验收与历史基线，不是性能样本。

原 parallel-formal-v106 完成了 picorv32a Q/D 的 5/30 数据，但监测记录显示所选 GPU 上存在外来计算进程。整轮性能验收资格已标为 invalid_for_acceptance；原始样本、数值统计、占用记录和未完成的 wide_100000 输出均保留。没有将正加速比计为通过，也没有依据结果挑选样本。

用户确认本轮无法协调独占 GPU，使用空闲非 0 卡并持续监测。clean-formal-v119 按原 manifest、8 请求线程、固定 affinity、四模式轮转、5 次预热和 30 次完整 trace 采样重新执行。每 2 秒核对设备进程与本次容器 cgroup；观察到外来或无法确认归属的进程、监测失败，整个用例尝试即失去验收资格，仅停止已核验属于本次尝试的容器，再从预热开始重跑。进程退出后仍执行末次占用查询。记录表述为“观测时刻未发现干扰”，不宣称轮询能够证明间隔内绝无短进程。

监测行为测试覆盖运行中占用、退出边界占用和查询超时，均拒绝受影响尝试并完整重跑，未停止外来容器。首次宿主启动因 Python 3.10 不提供 hashlib.file_digest 失败，尚未采样；改用同一 SHA-256 的 read_bytes 计算后重新启动。实际首个尝试也捕获到外来进程并按规则换卡。任务由 tmux stage12-clean-formal-v119 持续执行，主日志为服务器运行根下的 clean-formal-v119.log，各尝试单独保存命令、原始数据、占用及 verdict。

硬件计数器权限阻塞继续保留；规模 OFF/ON 扩展比较、可选规模性能和最终无干扰性能统计另行收尾。当前不标记 Stage 12 完成，不提交或推送。

补验脚本经独立静态审查后，已在 tmux stage12-supplement-v123 排队；当前状态为等待 clean-formal-v119 正常结束，尚未执行补验计算。随后依次运行：

- scale-cross-build-v120：复用正式样本的最终第十批结果核对四模式公开 QOR/paths；对两个十万节点输入，通过现有 full/mixed 会话入口比较 OFF/ON 全部设备图、timing、逐批 public、恢复和继续提交快照。完整字节比较后进行无损压缩并复验 SHA。正式样本没有保存前九批 public，不能据此声称四模式逐批 public 全部比较过。
- threads-final-v121：同一最终 OFF 二进制、固定 8 请求线程和 affinity，分别采集四模式线程 CPU ticks；100 ms 采样只报告实际观测，不把活跃状态当成精确 worker 数，不重新校准配置。
- crossover-formal-v122：复用原冻结六条小设计 trace 和三个可用非必过尺度输入，派生测量清单，继续使用同一 5/30 和 GPU 干扰拒绝规则。原 mandatory manifest 不变。小规模负收益照实保留；多时钟百万规模保留原预检超时，不伪造结果。

队列主日志为服务器运行根下的 supplement-queue-v123.log，逐项状态和占用背景保存在 supplement-queue-v123/。前两项属于独立正确性／线程剖析，不把其占用日志当作正式性能资源通过证明。启动前已再次核验共享 MemoryMax=512000000000、MemorySwapMax=0，服务器证据盘剩余约 391 GB；大快照补验在每次运行前另查空间。补验归档和差异检测小自测通过，两仓库 git diff --check 通过，README 与已有用户报告保持不变。

### 用户调整为共享 GPU 参考测量（v124–v126）

用户随后明确“测试过程中 GPU 被别人占用没关系，现在的加速测试只是作为参考，不用严格独占 GPU”，并授权停止本任务旧监测器、等待队列和重复的 Q 采样。自动审批最初拒绝中断，取得明确授权后执行；仅停止已按 PID/命令和容器参数核验的本任务进程，未停止其他用户进程。旧 v119/v123 退出和部分数据保留，原因记为策略切换，不计为算法或工作负载失败。

reference-samples-v124 不再因占用或监测异常取消采样；仍从空闲非 0 卡启动，记录共享情况并保持固定输入、线程、5/30 与四模式轮转。复用 v106 的完整 picorv32a Q/D：核对本轮 manifest/probe SHA、完整 case 配置、全部 140 个原始文件，调用既有 v2 验证器复核配对和统计。错误 manifest、二进制、线程配置 canary 均被拒绝；外来进程、监测异常和负加速的行为检查确认保留参考数据。独立复审通过。原始文件中 performance_gate 的数值判定保留为历史记录，新索引明确 performance_use=reference_only、strict_performance_acceptance=not_run，不把数值阈值观察当作严格验收。

参考结果（共享 GPU）：picorv32a Q 的 CUDA/full 对 native CPU/full 配对加速比中位数 1.309，95% 区间 [1.298, 1.319]；CUDA/incremental 对 CUDA/full 为 4.764，[4.732, 4.786]。D 分别为 1.306，[1.300, 1.316] 和 4.761，[4.748, 4.781]。上述区间不排除共享设备的系统性影响，不宣称独占条件下的结论。

当前持久会话替换为 stage12-reference-v126。reference-queue-v126 依次运行剩余 mandatory 参考测量、scale-cross-build-v125、threads-final-v121 和 optional 参考测量；各阶段串行。线程剖析使用的留存 probe 与当前参考 probe SHA 已核对相同。新队列仍共用 512 GB 硬上限、swap=0；原清单和未提交代码保持，未 commit/push。正确性补验和最终交付仍须完成；本轮参考测量不阻断于 GPU 共享或原加速比门槛，原严格高性能门单列为未验收。

public-reference-v127 已额外核对复用 Q/D 的全部 35 组运行：四模式的最终 generation=10、公开 QOR/paths 及结果规模完全一致。该检查直接读取已保存消费者结果，不启动 oracle，不修改性能样本，也不扩大为前九批 public 的证明。新 wide_100000 参考工作负载已在 GPU 5 启动，实际 controller/native 进程及共同内存限制均已核验；后续阶段尚未完成，目标保持进行中。


scale-cross-state-v128 已在 GPU 6、独立 CPU affinity 80–95 启动两个十万节点的 OFF/ON 完整状态补验，与 GPU 5 参考采样并行，共用 512 GB / swap=0 限制。它只用于正确性；后续 scale-cross-build-v125 等待其退出成功，再核对 manifest、二进制、trace、完整 case/mode 矩阵及压缩档案 SHA 后复用，避免重复计算。证据复用行为检查拒绝缺模式、身份不匹配、档案变化及失败退出；独立审查发现的 verdict 写入与进程退出竞态已改为先等待退出记录。wide_100000、multiclock_100000 的 full-levelization 和 mixed 四组路径均已完成 OFF/ON 十批完整图、timing、public、恢复及继续提交的逐字节比较，八份无损归档完成 SHA 复验，补验进程退出码为 0。scale-cross-proof-v134 复用现有验证函数，核对成功退出、完整四组矩阵、manifest、二进制、trace 和八份归档身份，结果通过；此步骤不重跑工作负载。这里的 full-levelization 属于 Dual-CSR 会话路径，CUDA/full 重建路径另由 parallel-scale-v113 的独立逐批比较覆盖。

当前工作树重新核验：126 个 native 改动文件与服务器构建源一致；parent 会话测试的一处 Mock 写法曾未同步，现已保留远端旧文件并同步。当前该模块 35 项测试及 ruff 通过，127 文件再次核对全部一致。此差异只涉及测试代码，无需重建 native 二进制。日志和同步身份保存在 parent-current-v129、source-sync-v130 与 deployment-v130，不覆盖旧记录。

### 完整参考结果与初始化失败续跑（2026-09-26，v125/v121/v136–v146）

reference-evidence-v138 已复验八组完整结果的 v2 schema、冻结输入/二进制身份、每组 140 个原始文件哈希及配对统计，并取回 47 份小型证据文件。每模式预热 5 次、采样 30 次；每个样本为完整 trace。picorv32a 与十万规模为十批，xtea/usb 为两批。下表为消费者耗时中位数（秒）；p95、MAD、加载、初始化、清理及 cold end-to-end 均保留在各 samples.json。

| 用例 | CPU/full | CPU/incremental | CUDA/full | CUDA/incremental |
|---|---:|---:|---:|---:|
| picorv32a-q | 39.105759 | 20.810263 | 29.864537 | 6.296911 |
| picorv32a-d | 39.092272 | 17.667616 | 29.952734 | 6.273686 |
| wide_100000-data | 79.140375 | 365.969408 | 61.309738 | 36.848718 |
| multiclock_100000-q | 132.549358 | 43.869171 | 104.784214 | 23.148557 |
| xtea-q | 0.031181 | 0.014424 | 0.061014 | 0.017862 |
| xtea-d | 0.032225 | 0.014364 | 0.062555 | 0.017554 |
| usb-q | 0.487672 | 0.150381 | 0.535879 | 0.124549 |
| usb-d | 0.485404 | 0.158586 | 0.531301 | 0.126129 |
| zipdiv-q | 0.825550 | 0.222313 | 0.878108 | 0.175671 |
| zipdiv-d | 0.809937 | 0.211639 | 0.861165 | 0.182446 |
| multiclock_10000-q | 7.522615 | 5.301095 | 6.443023 | 2.215853 |
| wide_10000-data | 6.458186 | 11.103420 | 5.499610 | 1.749570 |

配对加速比中位数及 bootstrap 95% 区间：

| 用例 | CUDA/full 对 CPU/full | CUDA/incremental 对 CUDA/full |
|---|---:|---:|
| picorv32a-q | 1.309 [1.298, 1.319] | 4.764 [4.732, 4.786] |
| picorv32a-d | 1.306 [1.300, 1.316] | 4.761 [4.748, 4.781] |
| wide_100000-data | 1.289 [1.287, 1.293] | 1.664 [1.654, 1.672] |
| multiclock_100000-q | 1.258 [1.251, 1.266] | 4.537 [4.476, 4.556] |
| xtea-q | 0.519 [0.503, 0.525] | 3.346 [3.263, 3.529] |
| xtea-d | 0.526 [0.506, 0.565] | 3.559 [3.379, 3.695] |
| usb-q | 0.913 [0.901, 0.924] | 4.315 [4.248, 4.370] |
| usb-d | 0.911 [0.896, 0.928] | 4.202 [4.137, 4.370] |
| zipdiv-q | 0.949 [0.927, 0.960] | 4.948 [4.887, 4.974] |
| zipdiv-d | 0.940 [0.933, 0.948] | 4.735 [4.671, 4.771] |
| multiclock_10000-q | 1.167 [1.151, 1.175] | 2.915 [2.898, 2.929] |
| wide_10000-data | 1.169 [1.160, 1.182] | 3.152 [3.125, 3.177] |

以上均为用户授权的共享 GPU 参考结果。xtea/usb 的 CUDA/full 负收益如实保留，不是功能失败；四个主要用例的正数值观察也不转换为严格高性能验收。严格性能门继续为 not_run。

scale-cross-build-v125 退出成功：四个主要用例的全部 35 组运行，最终 generation=10 的四模式公开结果一致；同时核对并复用 v128 的 OFF/ON 完整状态证据。该公开结果检查仅覆盖最后一批，逐批完整 timing/winner 仍由独立诊断证据证明。

threads-final-v121 四模式均退出成功，请求 8 线程、affinity 0–31。CPU/full、CPU/incremental 的 peak live/running 观测均为 1/1；两个 CUDA 模式为 4/1，记录的 CPU ticks 主要来自主线程。100 ms 轮询可能漏掉短生命周期线程，不能据请求值宣称 CPU 基线使用了 8 个并行 STA worker。

旧 reference-queue-v126 已退出（1），其 running 状态文件未代表仍在执行。zipdiv Q 的 sample-26/CUDA-full 报 cudaGetDeviceCount: initialization error，退出 1、未超时、未生成成功 consumer.json；旧部分结果和占用日志完整保留。v136 在同一空闲 GPU 1、相同冻结命令下连续三次重放成功，并完成两个批次及生命周期清理。初始化失败的具体原因尚未查明；没有据此修改生产计算代码，也没有把诊断重放加入性能样本。

续跑会话为 stage12-reference-resume-v137，日志为服务器 reference-resume-v137.log。它再次核验并复用四组已完成的 xtea/usb 结果，为 zipdiv Q 重新采集完整配对样本，并补齐 zipdiv D、multiclock_10000-q、wide_10000-data、wide_1000000-data。原失败组不覆盖、不与新组拼成跨日配对。source-sync-v137 核对 127 个相关本地/服务器文件一致；新脚本语法检查和四组实际复用校验通过。共同 512 GB 硬上限、swap=0 仍有效。扩展采样和最终交付仍待完成，未 commit/push。

zipdiv Q 的 v137 完整 5/30 采样已成功结束，未再出现初始化失败，原失败记录继续保留。其统计加入上表，CUDA/full 的小规模负收益未筛除。optional-public-v139/v140 另在采样外复用现有比较器，校验 xtea/usb Q/D、zipdiv Q 全部 35 组四模式的最终 generation=2 公开结果与原始文件身份，均通过；这不补写 OFF 性能样本的 correctness 字段，也不代表未保存的第一批 public 已被本次检查覆盖。七份新增小型证据已取回 reference-evidence-v140 并核对 SHA。续跑现进入 zipdiv D，剩余三个规模点随后执行；计划相关五份文档的相对链接检查通过。

reference-phase-summary-v141 在采样外汇总原始 30 次完整 trace，保留四模式的提交、物化、报告/读取、分配和传输计数。以下为 CUDA/incremental 十批合计的分项中位数（秒）；各项分别取中位数，不能要求其和与总耗时中位数严格相等。consumer_read_ms 包括报告后处理，以及 timing values、公开 QOR 和 paths 的实际读取。

| 用例 | 提交 | 结果物化 | 报告与读取 | 消费者总耗时 |
|---|---:|---:|---:|---:|
| picorv32a-q | 1.120 | 3.151 | 2.011 | 6.297 |
| wide_100000-data | 25.066 | 7.693 | 4.182 | 36.849 |
| multiclock_100000-q | 1.448 | 9.343 | 12.359 | 23.149 |

多时钟规模与 picorv32a Q 的剩余主要成本位于结果消费侧；宽层汇聚规模仍以提交为主。上述完整消费者成本始终计入主指标，未以 kernel 时间代替端到端结果。v141 同时重新读取最终构建/回归退出状态、逐批独立比较 verdict 和 sanitizer 原始摘要；未将 disabled 测试、NCU 权限阻塞或既有类型检查失败改记为通过。

zipdiv D 的 v137 完整 5/30 采样已退出成功（约 1,009 秒，含所有进程生命周期），其消费者统计加入上表。至此三个小设计六条 Q/D trace 的参考采样全部完成；optional-public-v142 校验六组全部 35 轮运行的原始身份及最终 generation=2 四模式公开结果，均通过。新增五份证据取回 reference-evidence-v142 并核对 SHA。续跑当前进入 multiclock_10000-q，随后为 wide_10000-data、wide_1000000-data；扩展规模采样仍未完成。

multiclock_10000-q 完成十批完整 trace 的 5/30 参考采样，退出 0，整组生命周期约 1,936 秒。optional-public-v144 校验全部 35 轮的 generation=10 四模式公开结果一致，并复核前六组小设计结果的原始文件身份；新增统计加入上表，五份小型证据取回 reference-evidence-v144。该规模点的两项正收益仍只作共享 GPU 参考。reference-resources-v143 直接读取 cgroup 控制值及实际控制进程/STA 进程归属，确认共同 512 GB 硬上限、swap=0；slice 的累计历史事件不用于推断本轮发生 OOM。队列已进入 wide_10000-data，随后执行 wide_1000000-data，尚未完成本轮交付。

wide_10000-data 完成十批完整 trace 的 5/30 参考采样，退出 0，整组生命周期约 2,130 秒。optional-public-v145 校验八个已完成可选用例的全部 35 轮最终公开结果及原始文件身份，均通过；wide_10000-data 对照的是 generation=10。新增统计加入上表，六份证据取回 reference-evidence-v145。当前共有十二组完整参考结果，最后的 wide_1000000-data 已在启动时空闲的 GPU 1 上运行，尚未完成。

百万点输入准备另记为剩余工具开销：冻结 replay 为 9,141,864,441 字节。现有 plansJson 在每批写入完整 baseline，parsePlans 检查一致性后只保留 edits 和 expected_generation；运行中的生产 EditBatch 没有保留这些重复 baseline。Python 控制器为核对完整批次数一次性解析整个文件，其进程 VmHWM 为 43,800,260 KiB（约 41.8 GiB），随后 RSS 降至约 27 MiB；首个 native CPU/full 预热已成功执行十批并清理，原始 consumer/status 位于 reference-optional-v137/wide_1000000-data/runs/warmup-1/cpu-full：消费者总耗时 1,163.317 秒、加载初始化 959.104 秒、cold end-to-end 2,155.527 秒、退出 0。这只是一个预热，不计作完整统计。运行早期观测 RSS 为 71,005,720 KiB（约 67.7 GiB），不是最终峰值，也未将其全部分配归因于解析器。证据为 million-input-observation-v146。控制器准备发生在子进程采样前；native replay 解析计入 load_initialize_ms/cold_end_to_end_ms，均不能冒充 CUDA kernel 耗时或从整组执行记录中隐去。本轮保持冻结输入继续采样，未在运行中变更 replay 格式。


### 服务器重启后的整组续跑（2026-09-26，v147–v148）

服务器本次启动时间为 2026-09-26 09:54:37 UTC（北京时间 17:54:37）。旧控制器、STA 进程、tmux 和容器均已消失；最后一条占用记录为 09:43:24 UTC，CPU/incremental 没有完整输出或退出记录。不能将此项记为成功、已确认超时、算法失败或 OOM；当前用户无权读取系统内核日志，重启原因未确定。reference-interruption-v147 保存原文件身份和存留状态，十二组已完成结果及百万点 CPU/full 的单次预热均保留。

用户确认恢复百万点整组四模式 5/30。v148 再核对 127 个本地/服务器文件一致、原 probe 和 manifest 身份，以及八个可选完成组的全部原始身份；只在新目录重跑 wide_1000000-data，不将中断前单次预热拼入新统计。会话 stage12-reference-resume-v148、日志 reference-resume-v148.log，启动 GPU 为 1。启动前内存检查曾因重启后的临时单元失效而拒绝运行；现由持久会话加载并检查实际 cgroup 限制，另修正 systemctl 分页造成的启动等待。实际控制器和容器共同 memory.max=512000000000、memory.swap.max=0 已验证，证据为 reference-resources-v148。原输入、二进制、8 请求线程、affinity 0–31、5/30 及每子进程 10,800 秒超时保持不变。Stage 12 仍在进行，严格性能门 not_run，未 commit/push。


### 百万节点首次预热超时（2026-09-27，v150）

v148 的 CPU/incremental 首次预热在 10,800 秒触发子进程超时，原始状态为 exit_code=null、timeout=true；外层整组退出 1。服务器启动时间仍为 2026-09-26 09:54:37 UTC，本次不是再次重启。未生成该模式的完整 consumer.json；本轮两种 CUDA 模式和正式样本尚未执行，不能生成百万点四模式统计。CPU/full 单次预热成功记录及此前十二组完整参考结果继续保留。million-timeout-v150 保存命令、日志、状态和原文件 SHA，十一份证据取回 reference-evidence-v150 后逐文件复验通过。

已找到现有 ista_stage6_production_fresh_probe 的 OFF performance 入口，可使用冻结 replay 和单批 prefix 输出准备、更新、mixed 分层、传播及发布耗时。该入口的线程和消费者配置与四模式 benchmark 不同，只用于独立定位，不替代原统计。当前尚未确定具体慢函数，未修改生产代码或冻结二进制；完整四模式 5/30 目标保留，Stage 12 继续进行。


### 独立 CPU mixed 单批定位（2026-09-27，v151）

使用现有 OFF/Release/GCC 14.3.0 的 ista_stage6_production_fresh_probe，复用冻结的一万、十万节点 replay，各运行首批一次。两次退出 0，实际 executed_mode=mixed-stage6，generation=1，清理完成；完整比较和诊断字段仍为 not_run。任务使用 CPU、tmux stage12-cpu-scale-v151，共同 512 GB/swap=0 限制已核验。下表是单次分项定位结果，不能替代四模式 benchmark 的 5/30 统计；该 probe 的 loader 默认配置与公开结果消费者也不同。

| 首批耗时（ms） | 一万节点 | 十万节点 |
|---|---:|---:|
| 批次准备 | 433.322 | 3,204.728 |
| native 编辑准备与执行 | 73.598 | 3,096.970 |
| 回读与 descriptor 构造 | 418.066 | 29,771.110 |
| Dual-CSR 更新 | 107.401 | 1,016.415 |
| 完整传播 | 14.462 | 163.497 |
| 提交合计 | 1,052.434 | 37,300.007 |

十万节点的 post_candidate_capture_ms 占提交约 79.8%。该区间同时覆盖 NarrowTimingRecordReader::read 和 TimingEditDualCsrDescriptorBuilder::build，尚不能归因于某一个函数，也不能直接认定百万节点超时的具体原因。后续先测量这两个函数，再检查重复查找、重复工作或临时对象分配。原始命令、分项、状态和构建信息保存在 cpu-scale-diagnosis-v151，cpu-scale-observation-v151 汇总证据；二十一份文件取回 reference-evidence-v151 并核对 SHA。生产代码、冻结输入和二进制未改动。


## 百万节点超时后的查找修复（v152–v164）

GDB 对相同 frozen wide 输入的单批 OFF 调用计时，将热点定位到 descriptor builder 中的逐弧全表查找、并行弧重复分组，以及电容证据/committed capacitance 的重复搜索。改为本次调用内借用只读记录的索引，每个并行弧组只验证一次；记录遍历顺序、完整身份、旧值、组重数及连续 ordinal 检查保留，没有修改传播候选顺序或关闭必要验证。committed capacitance 索引仍需一次全表遍历，未宣称全部准备成本只与编辑数相关。

| GDB 函数耗时（毫秒） | 1 万节点修复前 / 后 | 10 万节点修复前 / 后 |
|---|---:|---:|
| descriptor builder | 266.947 / 49.190 | 24,574.944 / 614.914 |
| arc coverage | 153.561 / 9.557 | 16,122.975 / 105.189 |
| node-model evidence | 26.896 / 7.786 | 2,082.119 / 96.739 |

前后分别来自 `cpu-capture-profile-v155`、`v160`；原始命令、函数计时、退出状态和二进制身份单独保存。中间只修改弧查找的 `v158` 将十万节点 builder 降至 3,204.786 ms。以上是单批剖析，不是完整 trace 的配对统计或百万节点完成证据。

新增回归检查电容记录乱序、重复身份、相同 ref 下完整请求不一致及错误 Liberty 值。规范与语义两项独立静态审查均无阻断项；`parallel-final-v159` 的 OFF/ON/default 严格构建、native、隔离 binding 和 parent 步骤已通过，三设计 Q/D 重核随后全部通过。四个 mandatory 用例逐批独立 native 对照仍在执行；CPU sanitizer 结果见下文。

实际工具失败均保留：`v152` 缺少 GDB Python support，复用服务器同版本文件后 `v153` 正常完成；`v157` 原生程序成功，但脚本错误要求一个优化后未命中的内部函数断点，改为只要求 reader/builder 入口计时后 `v158` 通过；sanitizer `v162` 使用了不存在的 target 名，改为 CMake 已注册名称后在 `v163` 重跑。没有将这些失败记为通过。

修复后 129 个相关源码文件与服务器逐项 SHA 一致（`source-files-v164.json`）。既有十二组完整参考测量继续绑定原二进制，不标成修复后的测量；下一轮百万节点使用新二进制，保留原 frozen manifest、四模式、5 次预热与 30 次完整 trace 采样。

CPU ASAN/UBSAN 的 v163 重建成功；四项测试均在启动时遇到已有 logger `_log_instance` ODR 冲突，未取得无抑制通过。仅针对该符号应用既有窄抑制后，四项实际测试通过；原失败、抑制内容和新日志均保留，不将补充结果称为无抑制通过。

v161 的 picorv32a Q 原生十批运行成功（602,542.139 ms），随后比较脚本直接传入原始 timing，将 full/mixed 合法的 level_nodes 排列差异误作数值错误，前置检查失败使 v165 未启动任何采样。v169 已复用现有 validate_functional / validate_stage6_fresh：分别验证完整层合法性，再比较 timing/winner；没有放宽 tolerance。原生输出、命令和二进制身份复验后复用，不重跑已成功的十批工作负载。

v169 的 picorv32a Q/D 均已通过全部十批独立 native CPU/full 对照，包括拓扑、timing、winner 和各自 level 合法性。D 的新原生运行退出 0、未超时，耗时 628,253.743 ms；原始输出保留服务器并记录 SHA，小型身份及逐批结果分别取回 `reference-evidence-v174`、`v175` 并核对 SHA。wide 100k 也已通过全部十批独立拓扑、timing、winner 和 level 合法性检查；原生诊断运行退出 0、未超时（1,324,046.971 ms），六份小型证据已取回 `reference-evidence-v176` 并核对 SHA，完整输出保留服务器。multiclock 100k 随后也通过全部十批独立比较，原生运行退出 0、未超时（1,066,383.736 ms）；v169 最终退出 0。四组各十批的最终 verdict、multiclock 输出身份及相关十份小型证据已取回 `reference-evidence-v177` 并核对 SHA；原始诊断输出留在服务器。

前置验证均成功后，服务器 tmux `stage12-reference-v170` 已于 2026-09-27 06:33（北京时间）在新目录 `reference-optional-v170` 启动百万节点完整四模式 5/30。新 OFF probe SHA 为 `8758202defb513cc3012896570a1374d2f47047f731263d6b36cd57e87ebd62d`，冻结 manifest 不变；启动选择空闲 GPU 1，继续观测共享占用。实际 controller 与 driver 的 cgroup 均归入共同 512 GB/swap=0，启动身份与资源证据已取回 `reference-evidence-v178` 并核对 SHA。

首轮预热已完成的原始耗时如下（毫秒；不属于 5/30 统计）：

| 模式 | 原生进程 wall | 消费者区间 |
|---|---:|---:|
| cpu-full | 2,266,377.262 | 1,225,136.734 |
| cpu-incremental | 7,677,726.541 | 6,434,226.120 |
| cuda-full | 1,952,584.890 | 986,552.008 |
| cuda-incremental | 5,251,725.921 | 4,299,776.989 |

四种模式均退出 0、未超时、完成清理及十批提交，最终 generation 10；每批实际模式与请求一致，无 fallback。四模式最终公开结果在采样外与 CPU/full 比较通过。该证明只覆盖首轮预热的最终公开结果，不能代替所有前缀的完整 timing/winner 对照或整组统计；OFF 样本中的比较和诊断仍为 `not_run`。原始样本及命令、状态、比较证据分别取回 `reference-evidence-v179`、`v193`、`v196`；完整首轮四模式原始样本及独立比较另归档到 `reference-evidence-v203`，均已核对 SHA。

首轮四模式已完成，当前进入第二轮预热，尚无完整百万节点四模式统计；旧失败和已有十二组结果保留，v170 仍绑定 `8758202d…` 冻结二进制。采样成功退出后，`stage12-public-v173` 将复用 `optional-public-v139.py` 核对全部 35 轮保存的四模式最终公开结果；该检查尚未执行。

首轮旧冻结版本的 CUDA/incremental 消费者耗时高于 CUDA/full；该负结果保留，不能据此宣称百万节点增量加速。这是一次预热，不能替代整组统计或代表后续 ordinal 修复版本。

## Targeted 弧序号投影清理（验收中）

`targetedArc()` 原来为每条弧重扫同源出边，以重新计算 parallel ordinal。冻结的百万节点宽层设计中，`data` 网扇出为 200,000，每个批次的 100 次编辑均包含一次对该网的编辑；修改前后投影该网负载弧时形成平方级扫描。现在直接读取已有 `native_arc_ids → arc_refs` 绑定中的 ordinal，保留当前图的 key base 投影、边界和事务检查，没有新增排序框架或缓存。诊断依据与源码身份保存在 `reference-evidence-v181`，不将静态复杂度分析当成百万节点耗时占比。

新增测试复用现有事务 fixture，核对合法 parallel cell 的非零 ordinal，以及连续两批中新增、重绑 native slot 和负载变化后的 patch key 与独立 export 一致。v182 首次使用的重复 net 弧夹具被 ON 完整 reference 合约正确拒绝，原失败保留；改成原生 full 构建的并行 cell 图后，v183 的 Release OFF、ON、默认无 CUDA 定向测试全部通过。两项独立静态审查均无阻断项。v185 已退出 0：三种严格构建、native、隔离 binding、parent 及三设计 Q/D 状态和公开结果对照全部通过。运行前后原 v170 程序及其项目共享库 SHA 不变；v185/v186 的命令、日志、实际导入路径和构建状态已取回 `reference-evidence-v189` 并核对 SHA，大型原始状态输出保留服务器及其摘要。

v184 使用同一冻结输入、8 个请求线程和 affinity 80–95，分别对旧、新 OFF probe 的 `NativeTargetedEditPreparer::prepare()` 入口/返回做 GDB 计时；每个用例只执行一个相同 prefix：

| 实际 baseline 节点数 | 准备阶段旧 / 新（ms） | 消费者区间旧 / 新（ms） |
|---|---:|---:|
| 10,002 | 76.127 / 55.538 | 1,071.266 / 1,051.887 |
| 100,002 | 2,925.382 / 1,187.136 | 11,154.532 / 10,318.727 |

四次进程均退出 0；旧、新保存的公开结果经现有比较器核对一致，未放宽 tolerance。这是单次、带断点的定位剖析，不是 5/30 统计、独立 native 全字段 oracle 或百万节点完成证据。旧 probe SHA 为 `8758202d…`，新 probe 为 `1ca4e4e8…`；完整身份、命令、日志、原始结果及 v182/v183 记录共 93 份文件已取回 `reference-evidence-v187` 并逐项核对 SHA。

v186 的 ASAN/UBSAN 构建成功；targeted edit 与 resolver 两项均在无抑制启动时遇到既有 `_log_instance` ODR 冲突。仅对该符号应用原有窄抑制后，两项补充测试通过，不能称为无抑制通过。新验证使用独立输出和 CPU affinity；v183 已核对原 v170 程序及其项目共享库 SHA 不变。v170 的采样结果仍属于原冻结二进制，不归入此次 ordinal 修复后的性能数据。

v190 复用现有逐批验证入口，对当前 ordinal 修复版本重新执行 picorv32a Q/D、wide 100k 和 multiclock 100k 的全部十批；每批与身份已核验的独立 native CPU/full 原始结果比较拓扑、timing、winner，并分别验证 level 合法性。picorv32a Q 的十批现已全部通过，原生运行退出 0、未超时（584,258.909 ms）；15.45 GB 原始输出保留服务器并记录 SHA，逐批 oracle 身份、比较结果和运行记录已取回 `reference-evidence-v192` 并核对 SHA。D 的十批随后也全部通过，原生运行退出 0、未超时（566,680.713 ms）；15.55 GB 原始输出保留服务器并记录 SHA，七份小型证据已取回 `reference-evidence-v198` 并核对 SHA。wide 的十批也已全部通过，原生运行退出 0、未超时（1,123,903.371 ms）；27.08 GB 原始输出保留服务器，SHA 为 4e7b3babeee91ae11b19967c1efe9cb9858e3b7b6178802355275a737f17ce1d，比较及运行证据已取回 `reference-evidence-v204` 并核对 SHA。multiclock 的十批现也全部通过，原生运行退出 0、未超时（966,506.350 ms）；24.59 GB 原始输出留在服务器，SHA 为 b4d7f44aa757b08adfda31e6aa7997bcb66f08f0154992b18228328e25d2e1b1。v190 控制器已正常清理并退出 0，四组各十批的 oracle 身份及最终 verdict 已复核；十四份小型证据取回 `reference-evidence-v210` 并核对 SHA。这是当前修复版本的独立正确性证据。服务器会话为 `stage12-cpu-ordinal-v190`，CPU affinity 80–95，不使用 GPU；实际进程已确认归入共同 512 GB/swap=0 限制。

最新修复版本的参考采样使用独立会话 stage12-reference-current-v200，等待 v185 回归、v186 限定 logger 抑制补验及 v190 四组十批独立比较成功后启动。沿用冻结 manifest、四模式、线程配置和 5/30 协议；新二进制 SHA 为 1ca4e4e8afef65e684b8bee6943c4c06ff3e624bc257996516585b212baf6ef2。每组先选择空闲非 0 号 GPU，允许后续共享并保留占用记录；GPU 与 host 可能和其他任务并行，只作参考。结束后另外核对全部保存的最终公开结果，普通采样的比较仍为 not_run。启动脚本及版本身份已归档到 reference-evidence-v200。v190 退出成功后，v200 已在 2026-09-27 12:39 左右（北京时间）启动 picorv32a Q 预热，GPU 1 在启动时空闲；实际子进程 affinity 0–31、二进制 SHA 及共同 memory.max=512000000000、memory.swap.max=0 已核验，三份启动证据归档到 reference-evidence-v211。四组 5/30 尚未完成，不作完整统计结论；v170 未被中断或替换。

v202 已用新二进制完成相同百万节点输入的 CPU/incremental 十批单轮工作负载：退出 0、未超时，各批实际执行增量模式且无 fallback，最终 generation 10，生命周期清理完成；最终公开结果在采样外与保存的 native CPU/full 比较一致。沿用 8 线程、affinity 0–31 和完整消费者需求，不使用 GPU；命令仅更换 probe 和输出位置，实际进程归入共同 512 GB/swap=0。原始样本 SHA 为 89a2bb144c499267bed54bec62ecb7211fd1e4b0b544d47fb9faa7711f147f9b，命令、结果及比较证据已归档到 reference-evidence-v206 并核对 SHA。

| 百万节点十批 CPU/incremental 单轮 | 旧冻结版本 8758202d | 新版本 1ca4e4e8 |
|---|---:|---:|
| 消费者区间（分钟） | 107.237 | 20.445 |
| 含加载、初始化、清理的 cold 区间（分钟） | 127.958 | 39.660 |

两次均是共享服务器上的单次运行观测，不能当作 5/30 配对统计；该比较只证明保存的最终公开结果一致，不替代逐批完整 timing/winner oracle。OFF 原始样本的比较和诊断仍为 not_run；既有 v170 完整采样保持原二进制，不以此次结果替换。


## 本轮参考采样调整为 20 次

用户将本轮参考测量改为每模式 5 次预热、20 次采样。既有 30 次结果保留为历史数据，不改输入、线程、消费者需求或统计方法。当前版本 picorv32a Q 按原始序号复用前 20 次，原始文件身份、统计及全部 25 轮四模式最终公开结果比较均通过；额外或未完成的原始文件继续保留，不按加速结果筛选。完整逐批 timing/winner 证据仍来自 v190。

| 当前版本 picorv32a Q（20 次参考采样） | CPU/full | CPU/incremental | CUDA/full | CUDA/incremental |
|---|---:|---:|---:|---:|
| 消费者耗时中位数（秒） | 38.718002 | 20.181306 | 31.004505 | 6.276805 |

CUDA/full 对 CPU/full 的配对加速比中位数为 1.250，95% 区间 [1.247, 1.259]；CUDA/incremental 对 CUDA/full 为 4.939，[4.888, 4.979]。这些仍为共享服务器参考数据，严格验收 not_run。原 schema 将少于 30 次标为 short_smoke，该字段保留；实际 protocol 明确记录 20 次，不修改采样器或验证器来抬升验收级别。

v214b 的无 GPU 汇总及独立公开结果比较均退出 0；首次汇总容器因 GPU 1 被本任务占用而拒绝启动（退出 2），没有重跑采样。16 份证据取回 reference-evidence-v216 并逐项核对 SHA。后续三个必测用例的 5/20 控制器 v215 已准备，实际复用分支和语法检查通过；原控制器停止操作被自动审批拒绝，切换仍待用户直接授权。百万节点整组尚未完成，Stage 12 继续进行。

当前版本 picorv32a D 也完成前 20 次参考采样。v219 复用原始序号 1–20 及 5 次预热，校验原始文件身份、退出状态、构建状态、消费者指标及 schema 后退出 0；额外样本全部保留，未按耗时筛选，未重新执行工作负载或 oracle。

| 当前版本 picorv32a D（20 次参考采样） | CPU/full | CPU/incremental | CUDA/full | CUDA/incremental |
|---|---:|---:|---:|---:|
| 消费者耗时中位数（秒） | 38.836798 | 17.491787 | 31.012418 | 6.214798 |

CUDA/full 对 CPU/full 的配对加速比中位数为 1.251，95% 区间 [1.248, 1.258]；CUDA/incremental 对 CUDA/full 为 4.997，[4.961, 5.023]。统计沿用冻结种子和 10,000 次 bootstrap。结果仅作共享服务器参考，严格验收仍为 not_run。

reference20-public-v219 在采样外检查 Q/D 各 25 轮四模式保存的最终 generation=10 公开结果，均通过；该检查不覆盖性能样本未保存的中间 generation。逐批完整 timing/winner 的独立证据仍为 v190，OFF 原始样本的比较及诊断保持 not_run。D 的 samples-20.json SHA 为 1206d23fd146c7f10adaa6384266760b905a863d9db8240007cb7fe696bc1b39。14 份小型证据取回 reference-evidence-v219 并核对 SHA。

本次第一次启动前检查误将目录名 cpu-full 等当作协议模式 cpu/full 等，检查失败时尚未启动汇总，也未修改样本。删除这层重复检查后，直接复用现有验证器的 MODES 和完整协议校验，汇总及公开结果比较均退出 0；失败原因记录一并归档。

两个当前版本 100,000 节点用例及百万节点整组采样仍未完成。百万节点此前两次四模式预热均正常结束，目前进入第 3 次预热。原 30 次控制器的停止操作仍待直接授权；Stage 12 保持进行中，未 commit/push。

## 宽层初始化失败与参考采样恢复（v222–v223）

v200 的 wide 100k 已完成五次预热及六轮正式四模式采样。第七轮 CUDA/full 在约 40.769 秒后退出 1，stderr 为 CUDA trace: cudaGetDeviceCount: initialization error，没有生成成功 consumer.json；控制器与原队列随后退出 1，multiclock 尚未启动。此前完整样本、第七轮两个成功 CPU 结果及 CUDA 失败文件均保留，不把部分轮次计为完整样本。错误来自 requireDevice 的设备枚举检查；系统原因仍未确定。共同 cgroup 没有 OOM 事件，当前用户无法读取完整系统内核日志，不能据此作驱动根因结论。

v222 尝试在原 GPU 1 重放时，被启动脚本因百万节点进程占用而拒绝（退出 2），测试命令未执行。v222b 改用当时空闲的 GPU 2，保留同一冻结程序、输入、线程和 affinity，仅改变输出目录及物理 GPU；三次重放均退出 0、生成结果，耗时约 110.040、109.470、110.741 秒。这些是诊断重放，不计入参考样本，也不能证明原 GPU 1 的初始化故障已经消除。

恢复使用现有运行、计量验证和统计函数。预检实际核验了五次预热和前六轮正式样本的原始 SHA、命令、构建、退出状态和测量字段；44 个已有模式运行通过核验。v223 直接引用这些原始文件，保留失败的第七轮，再从第七轮四模式重新执行至第二十轮，不按耗时挑选样本。Q/D 的 20 轮结果也已通过既有校验器后复用。新控制器等待原 GPU 1 空闲，以保持 wide 用例的设备一致；完成后执行 multiclock 的 5/20。原 GPU 占用日志与恢复段日志分别保留，完整公开结果比较仍在采样结束后独立执行。

服务器会话为 stage12-reference-current-v223，目录为 reference-mandatory-v223。v200 是自然失败退出，本次未停止任何进程。百万节点 v170 保持原任务运行；第三轮 CPU/incremental 已退出 0、未超时（6,379,485.511 ms），整组统计仍未完成。失败、三次重放、复用预检及恢复启动快照共 45 份文件已取回 reference-evidence-v224，逐项核对 SHA。生产代码、冻结输入和二进制未改变；Stage 12 保持进行中，未 commit/push。

本轮用户确认百万节点按整组四模式 5/30 继续；其他当前版本参考用例仍为 5/20。18:45 左右的续跑核验确认 v170 仍在第三轮 CUDA/incremental 预热，v223 恢复后的第七轮四模式均退出 0，继续第八轮。两个实际采样进程均在共同 512 GB、swap=0 的 cgroup 中，累计 OOM 事件为 0；130 个相关服务器源文件仍与已核验清单一致。进程、二进制、采样命令及第七轮原始文件身份保存在 continuation-policy-v225.json，已取回 reference-evidence-v225 并核对 SHA。未启动重复任务，也未停止或更改运行中的控制器；百万节点整组结果仍未完成。

恢复采样的收尾比较已修复（v226）：原 public-current-v200.py 从汇总目录拼接原始路径，实际恢复索引会触发 FileNotFoundError。现按每条样本已核验的 raw_file 路径比较，检查每轮四模式完整且无重复。修复后，wide 的五次预热与前八轮正式样本，以及 Q/D 全部 20 轮的最终公开结果比较通过；篡改新恢复段 generation 的 canary 被拒绝。该检查不执行 STA 或 oracle，也不替代逐批完整诊断。两份脚本最终 Ruff、mypy 通过，初始格式及类型失败日志保留；原脚本、修复版本、真实数据索引和测试结果已取回 reference-evidence-v226 并核对 SHA。运行中的采样控制器和生产源码未变。

## 宽层十万节点参考测量完成（v227）

当前 ordinal 修复版本的 wide_100000-data 已在服务器完成预热 5 次、正式采样 20 次。既有验证器复验了原始身份、协议和统计；全部 100 个模式运行退出 0、未超时。五次预热和前六轮沿用原始文件，第七至二十轮来自恢复队列，原失败及不完整轮次继续保存。

| 模式 | 十批消费者耗时中位数（秒） |
|---|---:|
| CPU/full | 77.525 |
| CPU/incremental | 86.488 |
| CUDA/full | 61.293 |
| CUDA/incremental | 16.217 |

配对加速比中位数为 CUDA/full 对 CPU/full 1.269×（95% 区间 1.230–1.287），CUDA/incremental 对 CUDA/full 3.807×（3.706–3.887）。CPU/incremental 在本用例仍慢于 CPU/full，负结果保留。这些是共享 GPU 参考测量；原始输出的 correctness_comparison、diagnostics、performance_gate 和 stage12_acceptance 仍为 not_run。

采样外使用修复后的现有比较器，核对全部 25 轮四模式保存的最终 generation 10 公开结果，通过；该证据不覆盖 benchmark 未保存的中间 generation，逐批完整诊断另见 v190 等记录。服务器证据位于 /home/qianhan/code/stage12-20260921-055547/wide-reference-v227/，其中 readback.json 保存身份、统计和成功退出的复核记录，public-verdict.json 保存独立公开结果比较。样本位于 reference-mandatory-v223/wide_100000-data/samples-20.json，SHA 为 2f81b0e3aec1d58a4c14d8d7bc572412a82ad3f46fd502ce7f462cbd0576e590。16 份小型证据已取回 reference-evidence-v227；归档包 SHA 843f14ff1bc00f87f99563f631bacfe42f6f153187f0976bb9653536f51fba5f 与服务器一致，解包后的样本 SHA 和比较凭证也核验通过。每次运行的原始输出和 GPU 占用日志继续保存在服务器，路径由样本及恢复策略记录。

传输先后遇到 SSH 超时、连接重置与无响应。核实旧远端读取进程已消失后，仅结束本地滞留的只读 SSH 连接；后续普通及压缩批量传输也未成功。最终使用原生 tar 封装、WSL scp 传输并完成哈希核验；服务器采样未停止或重启。中断后的进程和文件核验、传输失败及恢复记录保存在归档的 transfer-recovery.json。

20:52 的实际进程快照确认，multiclock_100000-q 与百万节点 v170 均在第四次 CPU/incremental 预热；多时钟用例采用启动时空闲的 GPU 7，协议为 5/20。两条实际进程的 affinity 0–31、GPU UUID 和共同 memory.max=512000000000、memory.swap.max=0 已核验，130 个相关服务器源文件仍与既有清单一致。百万节点仍绑定原冻结二进制及用户确认的 5/30。两项剩余整组结果尚未取得，Stage 12 未验收。


## 本轮统一为两次预热、十次采样（v230–v231）

用户将本轮全部参考用例统一调整为每模式 2 次预热、10 次正式采样，包含百万节点。按原始序号保留前两次预热和前十次正式样本；额外预热不改记为正式样本，历史原始文件及 5/20、5/30 统计继续保留。输入、线程、消费者需求、冻结二进制及配对统计方法不变。

reference210-v230.py 复用原恢复入口和现有测量、schema、统计函数，先核验 raw SHA、命令、退出状态、构建及消费者字段，再复用完整运行。预检退出 0：picorv32a Q/D、wide 100k 的新 2/10 统计和全部十二轮四模式最终 generation 10 公开结果比较通过，未重跑 STA 或 oracle。该比较仍只覆盖保存的最终公开结果；逐批完整正确性证据另见 v190 等记录。新数据位于服务器 reference210-completed-v230，原始输出的比较、诊断及严格性能门均为 not_run。

自动审批首次拒绝停止旧队列；用户随后明确授权“停止并切换到 2/10”。脚本核验两个旧 controller 的完整命令、UID、cgroup、容器 ID 和挂载后，仅停止对应本任务容器，保留所有文件。切换过程退出 0，记录于 reference210-cutover-v230.json；当时未完成的运行属于协议切换中断，不计作成功或算法失败。

新会话为 stage12-reference210-current-v230、stage12-reference210-million-v230，分别写入 reference210-current-v230、reference210-million-v230。21:31 的实际进程核验确认多时钟已续跑第三轮正式 CUDA/incremental，百万节点已从第一轮正式 CPU/full 开始；两次原预热已复用。新队列都在启动时选择空闲 GPU 7，后续相互共享并保留占用记录。百万节点原预热来自 GPU 1，新段来自 GPU 7；两卡均为 RTX 6000 Ada，分段设备身份及原、新占用日志分别保留，不声称为同一卡上的独占测量。原生子进程 affinity 0–31，共同 memory.max=512000000000、memory.swap.max=0，累计 OOM 为 0。

新脚本的初始 Ruff 格式/导入提示已保存，修正后 Ruff 和 mypy 均通过。启动时的脚本原文与格式修正版分别保存；未改变采样逻辑或生产代码。两仓库差异检查通过。两组剩余样本、汇总和最终核对仍在进行，Stage 12 未验收，未 commit/push。


### 2/10 数据复核与归档（v233）

现已完成十一组 2/10 汇总：当前 ordinal 修复版本的 picorv32a Q/D、wide 100k，以及旧冻结版本的 xtea/usb/zipdiv Q/D、两类 10k 规模。逐条复核原始 SHA、退出状态、构建、消费者字段和统计后通过；保存的最终公开结果在采样外比较通过。篡改一份结果副本的 generation 会被比较器拒绝，原始样本保持不变；四个运行脚本的服务器 Ruff、mypy 均通过。所有比较的范围仍是保存的最终 generation，不替代逐批 timing/winner 诊断。

| 当前版本用例 | CUDA/full 对 CPU/full 配对加速比〔95% 区间〕 | CUDA/incremental 对 CUDA/full〔95% 区间〕 |
|---|---:|---:|
| picorv32a-q | 1.248〔1.244, 1.262〕 | 4.924〔4.872, 5.007〕 |
| picorv32a-d | 1.252〔1.232, 1.259〕 | 4.985〔4.894, 5.099〕 |
| wide_100000-data | 1.225〔1.191, 1.246〕 | 3.885〔3.469, 3.994〕 |

以上仅为共享服务器参考值，严格性能门仍为 not_run。旧冻结版本的八组单独绑定 75ed9b8c…，不归入当前版本；小设计 CUDA/full 的负结果或区间跨 1，以及宽层 CPU/incremental 慢于 CPU/full 的结果均保留。完整中位数、p95、MAD、配对区间和输入/程序身份保存在 reference210-readback-v233/readback.json。

证据包 reference210-evidence-v233.tar.gz 已取回 WSL 并解包到 reference-evidence-v233；包 SHA 为 bb3808c3f36021d2fc63607473c5e25109cbad0e11e3090881ddfe55565a9797，74 个登记成员的大小与 SHA 均一致，四份脚本的本地与服务器内容也一致。原始每次运行输出及 GPU 占用日志仍留在服务器，包内保存引用。网络传输曾遇到连接/握手超时及连接中止，未因此重启采样；最终原生 scp 取回并核验成功。多时钟 100k、百万节点的完整 2/10 仍未取得，继续由现有 tmux 任务执行。


## 多时钟十万节点 2/10 收尾（v234）

multiclock_100000-q 已完成两次预热、十次正式四模式采样。控制器及独立公开结果比较均退出 0；复核了全部 48 个模式运行的原始 SHA、退出状态、构建、消费者字段和统计，冻结 probe 与样本声明一致。十二轮保存的最终 generation 10 公开结果比较通过；逐批完整 topology/timing/winner/level 证据仍来自 v190，不能由最终公开结果比较替代。

| 模式 | 十批消费者耗时中位数（秒） |
|---|---:|
| cpu/full | 129.785 |
| cpu/incremental | 43.120 |
| cuda/full | 104.103 |
| cuda/incremental | 23.180 |

CUDA/full 对 CPU/full 的配对加速比中位数为 1.239×，95% 区间 [1.232, 1.263]；CUDA/incremental 对 CUDA/full 为 4.500×，区间 [4.410, 4.577]。这是共享服务器参考测量；原始输出的正确性比较、诊断和严格性能门仍为 not_run。

服务器结果位于 reference210-current-v230；samples.json SHA 为 f75312ffe0fb76c8d1433f8e0dd33d5c869cefb07c1a19fbcf562f6dde4594e4。证据包 reference210-evidence-v234.tar.gz 已取回 WSL reference-evidence-v234，包 SHA 为 409aec5c4ed6b816eb07bab4efbff42db58a683298cf4473084754b94d4d3459，20 个登记成员的大小与 SHA 均一致。原始每次运行文件继续留在服务器，包内保存其身份与路径，并包含本次已结束队列的 GPU 占用日志。

当前已有十二组完整 2/10 参考数据：四组当前版本必测用例与八组旧冻结版本的小设计/规模数据分别标明二进制身份。百万节点仍使用其原冻结二进制继续采样，不能并入当前版本统计。Stage 12 尚未完成，未 commit/push。


## 统一修复版与 1/3 重测（v235–v236）

按 2026-09-28 最新要求，全部参考样例统一绑定 ordinal 修复版 1ca4e4e8afef65e684b8bee6943c4c06ff3e624bc257996516585b212baf6ef2。WSL 和服务器 130 个相关源码 SHA 均与该构建记录一致。四个已完成的当前版本必测用例从原始序号中选取一次预热、三次采样；现有统计验证和独立最终公开结果比较通过，没有重复运行工作负载。

旧百万节点容器经 PID、命令、所有权及挂载核对后停止。已完成的三轮四模式、第 4 轮 CPU/full 及中断的 CPU/incremental 日志全部保留；中断不记为算法失败。其旧版本 8758202d 和八组 75ed9b8c 结果保留为历史数据，不计入本轮新版统计。

新版队列 reference13-new-v236 在 tmux stage12-reference13-new-v236 中顺序执行 xtea/usb/zipdiv Q/D、两类一万节点及宽层百万节点，均重新进行四模式 1/3；复用现有性能入口和采样后公开结果比较器。启动时选择空闲非 0 GPU，持续记录共享情况；实际共同 memory.max=512000000000、memory.swap.max=0 已核验。脚本 lint/type/语法检查通过；初始宿主 Python SHA 接口、命令路径、长行和空任务组预检失败均发生在负载启动前，修正后启动，不升级依赖或放宽限制。原始证据位于服务器运行目录，usage 不添加验证记录。

截至 2026-09-28 12:40，除百万节点外的十二组当前版本 1/3 均已完成。百万节点 native CPU/full 预热正在运行；直接读取运行中 /proc/2408877/exe 的 SHA，确认为上述修复版，实际控制器参数为预热 1、采样 3，native 前缀 10、请求线程 8、affinity 0–31。启动证据 reference13-million-start-v238.json 已取回并核对 SHA。全矩阵收尾复核尚未运行，不将预热启动计为百万节点通过。
