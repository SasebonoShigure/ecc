# Stage 14.6 实施记录

日期：2026-10-16。基线为 ECC 8f427ef、ecc-tools 79e3106df。状态：实施中。首批已提交推送（ECC d6b7ee4、ecc-tools 1d13fe226）；第二批回传与等待计量已提交推送（ECC a163804、ecc-tools 8da1527fc）。第三批 native 基线绑定及对应文档已提交推送（ECC 4f409c3、ecc-tools b14f47ede）；本次 checkpoint 包含后续加载器、测量入口和生产模式迁移，不代表阶段完成。

## 首批改动

- timing-only CPU 基线调用 propagateRequired()，保留 RAT/slack，不提前生成完整报告分组；默认一次性完整产物流程不变。
- 完整报告测试和 native 事务测试在实际消费处显式调用 analyzePropagatedTiming()。验证基线未提前生成路径组、报告前后完整 timing 相等、报告包含实际路径，以及回滚恢复已准备的报告。
- 独立设计与代码审查完成。复核撤回了一个 prefix0 回归判断：公开 oracle CLI 原本拒绝零前缀，本次不扩展该协议。

## 首批最终验证

| 检查 | 结果 |
|---|---|
| 原版报告回归 | 通过 |
| Release / CUDA ON / debug OFF 构建 | 通过 |
| OFF 报告、native 事务、编辑与 lifecycle 回归 | 31/31 通过，无跳过 |
| Release / CUDA ON / debug ON | 配置、构建及相关回归通过 |
| Release / 无 CUDA | 配置、构建及相关回归通过 |
| 两仓库 diff 检查 | 通过 |
| 新性能测量、完整阶段回归及 sanitizer | 未执行，不作通过结论 |

运行目录：服务器 /home/qianhan/code/stage14.6-20261016-implementation，本地同名目录位于 /home/shigure/code。基线归档、源码哈希、batch01-source.json 和 checkpoint01-evidence 保存版本与结果；本地最终三个源码文件与服务器受测 source01 哈希一致。driver01.exit=0，batch01-verdict.json 确认全部命令成功；原始日志已取回 checkpoint01-evidence。所有构建共用 512 GB 硬上限、swap=0。

曾启动的 batch02 仅验证后来撤回的 prefix0 扩展，已取消且保存日志；不计作最终改动的验证通过。

## 第二批：回传与等待计量

ecc-tools 提交：8da1527fc。

- 分开记录分层决策、level 元数据、必要状态、候选及完整结果的实际 D2H 字节和既有同步点等待。原 d2h_ms 改名 delivery_d2h_ms，仅表示传播后状态及显式查询的设备事件区间。
- Runtime 等待归属于本代计算、查询及针对该代的撤销。close 的同步属于生命周期清理；构造失败前临时候选中的计算等待不保证保留，失败整段成本仍取外层 wall time。主机等待与 kernel/传输区间重叠，不可相加。
- 复用现有同步和事件，只增加常数计数及主机时钟读取；不宣称零开销。分组仅在相应等待成功后完成，错误路径可留未分类字节。
- trace process/verdict 升级 major；samples v2 添加可选 readback 扩展，历史样本不补造缺失计量。
- 独立审查发现撤销等待原会随 cleanup 对象丢弃，已改为归属存活 owner。新增实际放弃、部分 patch 失败、构造分配失败、输入拒绝和重复查询行为测试，后续 OFF/ON 行为回归均通过。
- 修改文件类型检查失败：默认导入配置 44 项；在相同显式导入路径下，基线与本轮均为 43 项，没有新增诊断。原始输出及比较在 batch03-type-comparison.json；不将基线同错记为通过。
- Python 8 项通过，包含错误计量拒绝及旧 samples 兼容。首次运行发现 samples schema 未迁移，修复后通过；修改文件 lint 曾报 3 处 E501，修复后通过。未将这些主机测试当作设备验收。
- 冻结源码 source03 与本地 15 个 native 文件哈希一致。Release/OFF 配置和构建通过，10 项 CUDA trace、事务、mixed、fallback、查询及性能编排回归全部通过。任务使用 GPU 1 和共同 512 GB 内存上限、swap=0。
- driver03.exit=1：随后启动 memcheck 时找不到 compute-sanitizer，脚本以 FileNotFoundError 中断；memcheck/initcheck、ON 和无 CUDA 检查均未执行，未生成总 verdict。原始失败及已完成结果已取回 checkpoint03-commit-evidence；本次提交不将部分验证写成完整通过。

后续补验使用镜像中已有 compute-sanitizer 的绝对路径，未改变源码或覆盖原失败记录。driver03b.exit=0：复用已核验身份的 OFF 成功结果，补跑 memcheck/initcheck 均为零错误；独立 Release/ON 构建与 10 项相关回归、Release/无 CUDA 构建与 4 项相关回归均通过。紧凑原始记录及哈希已取回 checkpoint03-resume-evidence。此结果仅覆盖本批计量与相邻路径，不代表完整阶段、旧严格编译或类型检查通过。

## 第三批：native 基线绑定（相关回归通过）

ecc-tools 提交：b14f47ede。

- NativeFullEditPreparer 直接借用 canonical Database 与会话 authority 建立语义节点、net 及实际 clock-point 保护；不再要求完整 CSR 输入。外部 frozen trace 身份检查仍留在实际接受该输入的测试入口。
- 物理 CPU/full 在 native 传播后直接绑定会话，不为恢复目录及编辑绑定导出整份 CSR。CUDA 的实际 CSR 输入保持原路径。旧 benchmark loader 仍会导出 CSR，I 尚未全部完成。
- 恢复身份改为原生连接、约束、唯一已用 cell 的实际模型、全局输入端 slew 阈值，以及原有文件、几何、RC 参数、模式和构建身份。独立审查发现初版遗漏实际加载模型，已复用现有 cell 编码修复；不把用户传入的文件清单当作实际模型的替代。
- physical-sta-baseline 升至 2.0.0；旧 journal 明确拒绝，不做兼容重放。模型覆盖仍为 baseline 已用 cell，未扩大为未来尚未使用的全部 buffer 模型身份。
- 新增实际传播时钟 net 拒绝，以及连接顺序、约束、已用模型、全局阈值变化后的恢复拒绝测试；模型不变的恢复须成功。源码冻结在 batch04-source.json。driver04.exit=0，独立 Release OFF/ON 构建及各 6 项相关回归、无 CUDA 构建及 4 项回归通过，无跳过；实际构建开关已核对。小型原始日志与哈希在 checkpoint04-evidence。本批尚未做专项 sanitizer 和调用剖析，不代表完整 I 或阶段验收。

## 第四批：native-only 加载边界（原构建失败，后续修复见第五批）

- 加载器提供直接借用 native/session/authority 的回调；原 CSR 回调继续显式导出并校验其支持范围。实际加载、operation guard 和清理共用同一实现，无运行期开关。
- native 事务测试改用 native-only 回调；完整 CSR 导出留在测试中用于 frozen identity 和回滚等价证明。补充回调失败后的清理及同进程重开测试。
- native 事务测试迁出 CUDA-only probe，独立 target 在 OFF、ON 和无 CUDA 构建均可运行；删除旧 native-transactions CLI，公共 timing 文件检查移动到共享测试 helper。
- source05/batch05-source.json 已冻结，driver05.exit=1：OFF/ON/无 CUDA 配置通过，三种构建失败，运行测试未执行。OFF/ON 的 native 测试间接包含 CUDA helper，缺少 MixedLevelizationTelemetry.hpp；无 CUDA 构建另报 NativeExecutionAuthority／NativeCandidateExecutor 类型不完整及 NativeExecutionFailpoint 未声明。后续修复已移走 CUDA 报告 helper 依赖并直接包含 native 执行定义，原失败仍保留；新源码尚待运行复验；原始失败保存于 checkpoint05-build-failure-evidence。
- source05 不包含后续紧凑输入及末轮 benchmark 迁移，不能将后续结果归给这个失败版本。

## 第五批：紧凑输入与末轮测量

- 测量入口仅接受 native CPU/full 与 CUDA/incremental；原 Stage12Benchmark 和旧 probe 分发已删除。其他生产入口的模式收敛尚未完成。
- 紧凑输入 v2 校验有序实际源文件身份、输入规模及既有批次规则。native 直接加载并编辑，不构造 CSR baseline identity；CUDA 使用计算本来需要的真实 CSR 身份。
- 每轮只执行编辑和计算，末轮读取完整 timing/QOR/paths。samples v3 使用连续 consumer_loop_ms，拆分加载、准备、提交、最终物化/报告和清理；未执行的中间报告为 null，正确性比较及诊断为 not_run。历史 samples v2 与 physical 格式仍可读。
- 主机 Python 8 项及历史 schema 自检通过；首次 lint 失败已修复并通过。显式修改文件类型检查为 43 项错误，基线同口径为 39 项；新增 4 项来自测试可空返回值，修复后显式检查为 39 项，与基线既有错误相同，新增文件不再报错；lint 通过。旧错误仍为失败。
- driver06.exit=1：三种配置均成功，构建均失败，运行回归未执行。OFF/ON 报 6 处 JSON/nullptr 条件表达式类型歧义；无 CUDA 报 build-info helper 间接包含旧 DualCsrReplayTypes.hpp。原始日志及哈希已取回 checkpoint06-build-failure-evidence。
- 改为显式 JSON null，并把既有 build-info 函数移到只依赖配置和 JSON 的测试头；新增 cuda_enabled 读取真实生成配置。旧 serializer 复用同一函数，不新增兼容包装。修复与 Python 类型收窄冻结为 batch07/source07，使用独立 Release OFF/ON/无 CUDA 目录重新构建；07:16 UTC 已确认 OFF 配置成功且构建运行。旧 source06 保留。运行验收尚未完成，不作速度或全阶段结论。

## 剩余范围

I 的加载器和测量进程已通过针对性验证，百万单元初始化剖析见下文；模式退役剩余测试链及 A–H 优化仍未完成；测量 controller 的实际小用例验证见第六批补验。未取得新加速结果；Stage 13 遗留项、Stage 12/15 正式性能门及既有严格构建、类型和 sanitizer 失败保持原记录。README、用户 CLAUDE 和独立报告不纳入本次提交。


### 第五批后续复验

- source07 三套 Release OFF/ON/无 CUDA 配置、构建和实际 build-info 均通过；ON 11 项相关测试通过。OFF/无 CUDA 原运行各有一项新测试失败，原夹具将四个编辑复制为八个，超过 engineering_smoke 的总限额 4。现保留原四个互不冲突的编辑，拆成两批各两个，更新第二批 token 序号，未放宽边界校验。
- 修正测试使用身份相同的 source07 二进制。无 CUDA 和 ON 复验通过；首次 OFF 复验因启动脚本覆盖容器库搜索路径而报 CUDA 驱动加载错误，恢复原环境后通过。原两次失败保留；最终实际进程覆盖连续两批、重复 native 运行、native/CUDA 完整公开 QOR/paths 对照及 malformed 输入拒绝。原构建及测试证据在 checkpoint07-evidence，修正记录在 checkpoint07-corrected-contract。
- 独立 GDB 剖析先停于 main、确认共享库符号解析，再观测入口及完整返回。该两批用例的 native CSR graph/reference 导出均为 0 次，analyze 为 0 次，analyzePropagatedTiming 为 1 次；native 完整构图和传播为基线加两批共 3 次。CUDA 只调用一次结构构图、CSR reference 导出和设备初始化，GPU propagation 为 3 次；native timing 传播为 0 次。两模式正常退出，公开结果与未插桩运行一致，证据在 checkpoint07-profile。
- 上述调用证据只证明该实际用例的路径，不代表全部输入或性能收益。GDB 时间包含插桩和嵌套，不相加、不作为采样。百万单元初始化分解、完整阶段回归和新性能对比仍未执行。
- 已按原哈希迁移 wide/multiclock 的小规模及百万单元紧凑输入，保留原网表、工艺文件、十批各 100 次编辑和真实规模；只补有序源文件身份，未复制大型网表。compact-inputs07/identity.json 保存来源与哈希，输入迁移不代替运行验收。
- 夹具与剖析证据范围经独立复审，无静态阻断；修改文件 lint 通过。类型检查既有 39 项错误仍记失败。当前后续改动未提交，整个 Stage 14.6 尚未完成。


## 百万单元初始化剖析

profile08 的四个诊断进程均正常退出；wide_2500002（1,000,000 个单元）及 multiclock_2666692（1,000,008 个单元）分别执行 native CPU/full 和 CUDA/incremental。每个进程仅使用派生的首批 100 个编辑，不是冻结十批协议的性能样本。原始十批输入未改动。

两设计的完整公开结果均与对应 native 结果一致。native 不导出 CSR，完整传播为基线加一批，报告后处理仅末轮一次；CUDA 只构造一次 native 结构和 CSR 输入，GPU 传播为基线加一批，没有 native timing 重算。所有观察断点均解析并核对入口、返回和正常退出。

CUDA 结构构图约 27 秒，CSR reference 导出约 62/72 秒，提示初始化仍有显著主机成本；这些是带 GDB 插桩的嵌套区间，不相加、不作为加速样本。完整内部 oracle、实际工作线程剖析仍为 not_run。紧凑证据 checkpoint08-profile 共 39 文件约 93 KB，已取回并逐文件核验哈希。

## 第六批：生产模式及调用方迁移

- Python/native 公共入口只接受 CPU/full 和 CUDA/incremental，在加载或设备访问前明确拒绝退役组合。历史 execution record 仍可解码。CPU/full 的显式 snapshot/reference/scatter 诊断仅 ON 可用，OFF 不生成观察对象。
- 删除物理会话 CPU incremental owner、计算和发布分支，以及独立 CUDA/full replayer、probe、controller；保留 native full、CUDA incremental、必要 full 初始化/恢复/fallback 和物理共同事务。
- retained CUDA controller 逐 prefix 使用独立 fresh native CPU/full 进程，核验实际模式、prefix、构建诊断状态和无 fallback。新增公开结果 stream/file 对照；不以同源 CUDA/full 比较替代 native oracle。
- 物理 benchmark 同步为两模式和 physical samples v3；历史 v2 四模式仅保留验证读取。独立审查发现的旧统计 import 与四模式循环已修复，审查复验无静态阻断。Stage 5/6 旧诊断 orchestration 及测试专用 full API 尚未全部收敛，不能宣布完整模式退役结束。
- 父仓库 test/tools/ecc：415 项通过；测量调度 8 项通过；修改文件 lint、两仓库 diff 检查通过。扩展到全部本轮 Python 文件后，类型检查仍失败：配置实际项目与虚拟环境的当前 20 文件和基线 18 文件均为 154 项相同诊断，没有新增消息。旧六文件的 39 项记录保留，不混用检查范围。
- source09 冻结当前 native 源码。首次构建脚本误改缓存路径，三配置在编译前失败；第二次误改清单名称，在加载清单前失败。原日志保留。修正后的 batch09c 使用同一源码、独立 Release OFF/ON/无 CUDA 构建目录；三套构建及真实 build-info 均通过。原 profile08 使用 source07，不冒充 source09 验收。


### 第六批补验与提交边界

ON 的 19 项相关回归全部通过；OFF 的 13 项、无 CUDA 的 9 项各有一项事务测试失败：测试替身仍要求 OFF 已关闭的诊断 snapshot context。修复只让该替身在 OFF 返回基线完成，ON 仍捕获快照。独立复核确认实际 native 事务、撤销、放弃和所有权断言保留；以原编译、链接参数和同一生产库重新编译该测试对象，三配置均通过。原失败二进制与日志未覆盖，当前源码比 source09 多这项测试修复及统计模块末尾空行清理。

真实两模式 controller 完成每模式 1 次预热、1 次样本，四个子进程均成功，完整公开结果一致；这是小夹具 contract smoke，性能门仍为 not_run。native/CUDA baseline 对照通过；传播时钟测试最初因脚本漏建已有 independent oracle target 未执行，补建后通过。

证据已取回并逐文件核验：checkpoint09-build-evidence（约 102 KB）和 checkpoint09-supplement-evidence（约 289 KB）；checkpoint09-targeted-acceptance.json 汇总最终局部验收并保留所有原失败。本次不宣称完整 Stage 14.6、全部 sanitizer、真实设计全矩阵或正式性能门通过。

本批 ecc-tools 提交：9f843e36a；按用户要求提交、推送当前 checkpoint，后续阶段工作继续保留独立验收边界。

## 第七批：删除独立 CUDA/full 的整图 staging（验证中）

- 删除仅剩测试调用的 `stageFull`、`stageFullNativeExport`、`stageFullCsr`，以及完整 Dual-CSR 重打包和第二份设备图的提交／撤销分支；不再通过旧测试维持退役模式。CUDA 初始化和 patch 的完整分层 fallback 继续保留。
- RC 仍需要旧／新 net buffer 隔离。将实际使用的备用 RC buffer、descriptor 放回持久 `RcPatchStorage`，保留成对交换、失败恢复、容量复用及清理等待；没有将真实撤销移入 debug。
- RC 容量增长、并行 launch、查询后编辑和 native RC 编辑改测实际 patch；新增模型增长后数值失败的 patch 撤销证明。旧完整重建专属测试删除，同一实例模型不同负载、部分 patch、cycle、owner/generation 及 ON 分配异常仍保留。
- 两项独立静态审查均未发现阻塞项，差异检查通过。新源码冻结为 source10，Release OFF（省略诊断选项）、ON 和无 CUDA 在独立目录构建；2026-10-16 09:19 UTC 确认 OFF 配置成功、构建仍在运行，尚无本批运行验收结果。不将先前 source09 或旧完整重建测试作为本批通过证据。

本批 ecc-tools 提交：54fd11223；按用户要求提交并推送验证中的 checkpoint，Stage 14.6 仍未完成。


### 第七批复验：RC 测试断言修正

source10 的独立 Release OFF/ON/无 CUDA 构建及 build-info 均通过。原回归 OFF 为 16/18、ON 为 19/21、无 CUDA 为 7/7；前两者均在 targeted/mixed session 的 RC 复制断言失败，原结果仍记失败，保存于 checkpoint10-build-evidence。

诊断实测该用例稳态分配为 0，四个节点的 D2D 为 32 字节，来自 mixed 分层必需的旧层序复制。原测试迁移后仍要求 D2D 为零，现改为只允许这份层序复制；未改生产计算或放宽数值比较。以原构建参数和同一生产对象重新编译修正测试，OFF/ON targeted、mixed 均通过；OFF mixed 的 CUDA memcheck/initcheck 均为零错误。

## 第八批：旧执行链的消费者迁移

- 语义 native-view 测试直接组合现有 graph/index/resolver patch，以独立 CPU reference 产生 scatter 输入，移除旧 coordinator 链接依赖。保留连续不查询、失败原子性及重试、查询后继续编辑、parallel arc 身份，并迁入 inactive peer 不影响活动身份及后续编辑的检查。
- 从旧 controller 移出已有的子进程/JSON 比较与功能 timing/level 校验函数；CUDA、物理比较和性能消费者直接引用窄测试 helper。计算过程及容差不变，旧 CLI 暂保留，整条旧执行链删除尚未完成。
- OFF/ON/无 CUDA 均按原严格参数重编译语义视图测试，并移除 coordinator 静态库后链接、运行通过。证据复用 source10 生产对象，不宣称已完成后续删除后的全量构建。checkpoint11-migration-evidence 共 58 文件、约 36 KB，已取回并逐文件校验。
- 独立审查发现两个导入遗漏，已修复；Stage 5/6 控制器自检、8 项性能编排测试、物理/CUDA/workload CLI 启动检查、修改文件 lint 和差异检查通过。修改文件类型检查仍失败：基线 6 文件与当前 8 文件均为 57 项相同诊断，无新增消息；此范围与前述 154 项检查不同。
- 本批仅为已验证的迁移 checkpoint；完整 Stage 14.6、其余存储优化、旧链删除、全面 sanitizer 和正式性能门仍未完成。README、用户 CLAUDE 与独立报告保持原样。

本批 ecc-tools 提交：caa49293d；按用户要求提交并推送当前 checkpoint。
