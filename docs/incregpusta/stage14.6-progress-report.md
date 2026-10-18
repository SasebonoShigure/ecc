# Stage 14.6 实施记录

日期：2026-10-18。基线为 ECC 8f427ef、ecc-tools 79e3106df。状态：实施中。首批已提交推送（ECC d6b7ee4、ecc-tools 1d13fe226）；第二批回传与等待计量已提交推送（ECC a163804、ecc-tools 8da1527fc）。第三批 native 基线绑定及对应文档已提交推送（ECC 4f409c3、ecc-tools b14f47ede）；本次 checkpoint 包含后续加载器、测量入口和生产模式迁移，不代表阶段完成。

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

## 第九批：旧 CPU 执行与诊断链退役（构建修复中）

- 在前批消费者迁移通过后，删除旧 CPU coordinator/replayer、Stage 5/6 receipt/controller 和 CPU pipeline；保留实际 CUDA patch/mixed/fallback/恢复及独立 fresh native oracle。随机图和失败分类测试直接覆盖 builder、Kahn、reconstruction，移除模拟提交的测试编排。两项独立静态审查无剩余阻断。
- 新功能校验 canary 直接覆盖共享 timing/level validator。功能校验、7 项性能编排、CLI 启动与父仓库 122 项相关回归通过。修改文件 lint 初次失败，修复后通过；差异检查通过。相同导入范围的类型检查从基线 4 文件 6 项错误变为当前 5 文件 2 项既有错误，仍为失败，不作通过结论。
- source12 独立 Release OFF/ON 的 mixed 组件分别 4/4、6/6 通过；主构建均因接口失去旧 transaction 库传递的 `AffectedCapturePlan.hpp` 包含路径失败，完整运行回归和 binding 尚未验收。无 CUDA 构建在 2026-10-17 04:31 UTC 检查时仍由同一任务继续执行。
- 本地已改为 CUDA 接口直接链接实际使用的 native CSR adapter，并将无 CUDA 不使用的 descriptor、pending 和 RC 投影留在 CUDA 分支；运行中的 source12 未改动。该修复及后续 Python 格式/注解修正尚需新冻结版本验证。原构建失败保留。
- 当前差异尚未提交推送。此前用户要求的 checkpoint 已交付为 ECC `f98e0a84`、ecc-tools `caa49293d`；本批不纳入该提交，Stage 14.6 仍未完成。

### 第九批构建修复进度

source12 已结束：无 CUDA 组件也为 4/4 通过，三个主构建均失败；原日志已取回并校验。修复经独立静态复核后冻结为 source13，三套独立构建及 binding 验证正在执行。2026-10-17 04:49 UTC，OFF 组件通过、主构建仍在运行，尚不能宣称修复通过。

## 第十批：CPU 分层状态与等待合并（运行验证前）

- mixed 保留 CPU 已计算的 offsets；旧节点复用稳定层组，新节点追加归属，每代只维护层组到当前层号的映射。full 初始化与 fallback 新建归属。OFF mixed 不再生成、回传整表 node_to_level，显式查询才展开；ON 保留独立 GPU inverse、完整排列和实际边序核对。
- 上传位置描述使用持久缓冲，offsets 由待提交对象持有；合并临时对象生存期造成的等待。设备状态仍在传播前与交付前读取，设备 patch 失败优先于 CPU mixed 冲突，不能错误进入 full fallback。
- 放弃、构造失败和关闭后的清理都缩回追加的归属；查询先完成所有分配再发布缓存，功能分层信息不会被查询移走。新增 group remap、组合失败、逐分配点查询重试测试，保留连续提交、扩容、rollback 与恢复后继续编辑。两份独立静态审查无阻塞。
- 普通归属更新为 O(L＋新增节点)，容量增长仍可能复制 O(N) membership；现有全图 topology 扫描和旧层序 D2D 尚在。没有已测得的耗时或加速收益。source14 已单独冻结，尚未运行；source13 的结果不能证明本批通过。

### 后续编译依赖发现

2026-10-17 05:00 UTC，source13 的 OFF 主构建失败，ON 主构建也出现相同错误：物理测试通过 `BenchmarkTimingConsumer` 包含 CUDA 会话头，但未直接声明 `ista_cuda` 依赖，因旧传递依赖移除而找不到 `MixedLevelizationTelemetry.hpp`。已在 CUDA 条件内为该测试补齐直接链接；独立静态复核通过，无 CUDA 注册和原有测试保留。原日志不覆盖。

尚未启动的 source14 被 source15 取代，后者包含 A–C 与上述一行依赖修复；已冻结上传，实际构建及运行仍未执行。后续先编译 CUDA 核心，再运行完整相关矩阵；不以静态复核替代运行证据。

### 2026-10-17 05:13 UTC：构建依赖修复与 A–C 运行验证启动

source13 已结束：OFF/ON 因物理测试目标缺少直接 CUDA 依赖而编译失败；无 CUDA 构建、相关回归与隔离 Python binding 的导入/契约测试通过。原始失败日志及成功结果保存在运行目录 `checkpoint13-evidence`，共 43 个文件、压缩后约 103 KB，已取回并逐项核对哈希。

修复后的 source15 同时包含 A–C 层状态和上传等待改造，已在独立 OFF/ON/无 CUDA 目录开始验证；启动时仅确认 OFF 配置成功、核心组件正在构建，尚无 A–C 运行验收结论。GPU 2 无计算进程，2 MiB 为观察到的空闲常驻占用；共同 512 GB 内存硬上限、swap=0 和锁定镜像已核验。后续实际 API 剖析脚本已准备，尚未执行。

### 2026-10-17：OFF 回归与实际 API 剖析

source15 的 OFF 主构建、相关回归、隔离 binding 导入/构建状态/无设备拒绝通过；mixed 的 memcheck、initcheck、racecheck、synccheck，以及实际 fallback 的 memcheck/initcheck 均正常结束。ON 与无 CUDA 后续矩阵仍在执行，尚不能将整组标为通过。

独立 GPU 1 的两批 API 剖析正常退出，实际 `cudaMalloc`、H2D/D2H 和等待调用与 telemetry 相符，最终公开结果与 native 相同。每批 stage 内 D2H 仅为 8 字节状态、2 次 stream 等待，level metadata 为 0；末轮完整查询的 telemetry 另记 44,656 字节和一次等待；该查询位于 stage 断点区间外，本次 API 捕获未独立核验它。首批/次批实际分配为 24/8 次，包含真实容量增长，没有宣称零分配。必要 H2D、D2D 与全图传播仍保留。证据为 `profile15-evidence`，12 文件约 22 KB；仅证明本实际小用例的调用路径，不是性能样本或百万规模收益。

### 独立 OpenSTA 接入预检

已用固定 OpenSTA `aa598a2f` 构建独立 executable；没有用 OpenROAD 内嵌版本代替。插件加载与十批各 100 次编辑成功，实际单元由 4,000 增为 5,000。自身 greedy 及固定 trace 的连接/pin 集合一致，但增量结果对 fresh 的严格 timing 比较均失败，最大差 `1.0658141036401503e-05 ns`；原容差与失败保留。

同一编辑 trace 在 1/8 线程下逐点相同；同进程失效重算与 fresh 完全相同，fixed trace 仅失效 arrivals 也恢复一致。证据指向增量路径状态更新，具体触发分支仍未定位；不能把补算当作 incremental 验收通过。未改外部 timing 算法，未采性能样本。构建及原始诊断已取回 `external-tools/precheck-evidence`（82 文件约 2.10 MB），详见运行目录 `external-tools/precheck-report.md`。全阶段仍未完成。

### A–C 矩阵收尾与独立 binding 修复

source15 已终止，driver exit=1：OFF/ON/无 CUDA 主构建与相关功能回归通过，OFF/ON 公开结果相同；OFF sanitizer 结果维持通过。ON Python binding 编译因缺少 AffectedCapturePlan.hpp 直接依赖失败，其导入和运行未执行。OFF/无 CUDA binding 通过。原始 83 项证据已取回 checkpoint15-evidence（压缩约 115 KB），失败不改写为通过。

最小修复仅在 CUDA＋ON 的 py_ista 目标链接实际使用的 native CSR adapter。独立 source16 冻结、审查后运行；2026-10-17 05:57 UTC 构建仍在进行，尚无运行结论。没有覆盖 source15 或使用后续 E 源码证明该修复。

### 第十一批：稳定路径行与局部撤销（实现及审查中）

路径元数据改为一份 canonical begin/end 行；普通批次只追加实际变化的有序 tag，使用真实 row 旧值和原逻辑长度撤销。废 payload 超过存活量时仅扫描非空 segments 压缩，保留旧 host/device tag owner 直到提交或撤销完成；结果 committed/work 两份仍隔离。设备只上传 tag 尾部与变更行，扩容保留有效旧前缀并重绑当前容量。全部消费者与旧测试接口已迁移。

新增稀疏空行长序列、同集合不变、最后路径删除、压缩撤销、逐分配点失败，以及设备增删/放弃/真实失败/重试/查询测试；ON 加独立 CPU 结果对照。正在独立审查，尚未冻结或执行 E 构建。必要 dirty reachability、容量增长、废槽重置和查询 D2H 仍计实际成本，尚无 E 性能或百万规模收益结论。

### 独立修复通过，E 进入运行验证

source16 ON binding 已正常结束：编译、隔离模块路径和 SHA、CUDA/debug 只读状态、绑定契约及无设备拒绝均通过。小型原始证据已取回 binding16-evidence（20 文件约 56 KB），source15 原失败仍保留。

E 的独立审查补充了压缩交换 tag owner 后继续扩容、逐个实际 host/CUDA 分配失败的验证；失败后重新计算旧状态，再重试提交，避免只检查旧缓存。两项静态复核无剩余阻塞。source17 已冻结并在独立 GPU 1 开始 OFF/ON/无 CUDA 回归；2026-10-17 06:04 UTC 仅配置成功，构建尚在进行，不能计为 E 运行通过。


### E 首次构建失败与复验

source17 已结束：OFF/ON 均因新测试缺少 `outputLoad` 的直接定义头文件而编译失败，CUDA 运行及剖析尚未执行；无 CUDA 构建、相关回归与隔离 binding 均通过。原日志已取回 `checkpoint17-evidence`（39 文件，压缩约 151 KB）并逐项核验。

修复只增加测试 fixture 的直接 include，未修改生产算法。静态复核通过后冻结为 source18，在新的 OFF/ON 目录复验；2026-10-17 06:29 UTC 配置成功、构建仍在执行。无 CUDA 复用 source17 未受影响的结果，不宣称重新运行。E 尚未取得运行通过结论；D 的增量入度/roots 设计审查已完成，生产改动等待 E 针对性验证。


### 2026-10-17：E 的 OFF 回归与实际传输剖析

source18 修复测试夹具缺少直接 include 后，OFF 的组件、相关 native/physical 回归、隔离 binding 及无设备拒绝通过；mixed 的 memcheck/initcheck/racecheck/synccheck 与 fallback 的 memcheck/initcheck 通过。ON 仍在构建，不能把 OFF 结果当作双模式验收。source17 原始 CUDA 编译失败记录保留。

独立 profile18 在 GPU 2 执行，两批各上传路径 tag 128 B、行变更 640 B，总 H2D 分别 4312/3632 B；每批实际状态 D2H 为 8 B、两次等待，无 level metadata D2H。设备分配仍为25/6次，D2D为10008/256 B，扩容并非零成本。末轮物化实际回读44656 B并等待一次，同 generation 重复读取未重复传输；与同输入 native 公开结果及 telemetry 核对通过。此为小夹具诊断，不是百万门性能样本。证据位于独立运行目录 profile18-evidence，未检查 cudaFree、memset 或 API 时间，未导出的 D2D telemetry 未作等价结论。

百万实际标准单元的1次预热/3次采样协议已固定两模式相同输入与末轮需求；同时报告循环、含 backend setup 的 workload 和 cold end-to-end 成本。最终源码、二进制及实际线程活动证据尚未冻结，采样未执行。

### 分段统计与 D 剖析准备

性能入口保留 consumer_loop_ms 主指标，并从同一份完整 trace 样本补算 edit_sta_loop_ms、workload_ms、cold_end_to_end_ms。方向均为 native CPU/full 除 CUDA/incremental；workload 包含 backend setup。新增字段沿用 v3 的历史读取能力，不改写旧样本。现有性能编排测试通过，修改文件 lint、scoped typecheck 通过；初次 import 排序和行长错误已修。独立审查无阻塞。百万门采样仍未运行。

D 旧版 source18 的真实 mixed builder 回调访问为两批 33/37 次；实际 API 与 public native 比较通过。首次剖析脚本因旧 GDB 无 Breakpoint.locations 失败，另存 v2 用真实函数地址断点后通过，原失败保留。紧凑证据 profile18-topology-evidence 共 25 文件、25,321 bytes，归档 SHA256 d5777ba12ff9750688e5a13dd7eb1c7002840f1abced417e893b564c4a28eaf8。新 D 版 source19 独立 OFF/ON 构建尚在运行，未取得跨版本访问下降证据；上述小 fixture 剖析不是百万门性能样本。

D 的 source19 独立 OFF/ON 构建、相关回归、隔离 binding、跨构建值比较和 OFF CUDA 检查通过；无 CUDA 复用 source17，未声称重跑。相同小型输入的实际 mixed 拓扑回调由 33/37 降为 6/6；五份输入文件内容哈希一致，仅不可变源码目录路径不同。该剖析不构成性能采样。F 已实现、测试复核中，尚无运行结论。

### F 编译修复与测量证据准备

source20 的 OFF/ON 核心构建因新增测试的三处命名空间错误失败，CUDA 运行验证未执行；无 CUDA 后续检查继续。修复只涉及测试类型限定名，独立复核未见新的静态阻塞；source21 在全新 OFF/ON/无 CUDA 目录验证，尚无运行通过结论，原失败日志保留。

百万门测量的只读监测脚本增加任务身份、每线程 CPU ticks、实际 affinity 和同时间资源占用记录，已有低内存自检及 lint 通过。尚未运行测量，不能从请求线程数推断实际并行度。

source20 最终 driver=1：CUDA 编译失败，无 CUDA 的相关构建、测试及隔离 binding 通过；35 份紧凑证据约 104 KB 已取回并校验。source21 于 08:12 UTC 仍在 OFF 核心编译，尚无 F 运行结论。资源监测经独立审查修正进程/线程身份读取竞争，自检和 lint 通过；实际测量仍为 `not_run`。


### 2026-10-18：F 验收与 H 模型验证复用

source21 的独立 Release OFF/ON/无 CUDA 构建、相关组件与 native/physical 回归、隔离 binding 及跨构建值比较通过；OFF mixed 的 memcheck/initcheck/racecheck/synccheck、fallback 的 memcheck/initcheck 通过。F 测试命名空间修复没有修改生产算法，source20 原始编译失败保留。86 份紧凑证据约 116 KB 已取回 checkpoint21-evidence，归档及文件哈希均核验。

同一 propagated-clock 小夹具的实际剖析确认：初始化上传时钟工作表，随后两批 mixed 不再从 propagate 上传该表，但实际 clock kernels 每批执行。每批 mixed 拓扑回调各 3 次；末轮物化回传 37,696 B、一次实际等待，三次读取复用缓存。独立 native CPU/full 公开结果与 API/telemetry 核对通过。新增加的模型校验断点实际命中 child/table 5/30 和 3/18 次，作为 H 改造前证据。

首次剖析验收脚本错误要求阶段外也必须命中 validator，因此 driver=1；实际阶段内正命中已证明断点有效。保留原 calls 和失败日志，修正这一无依据断言后仅离线重核原数据，verified-v2 通过，没有重采。阶段外零命中不代表整个初始化路径没有模型验证。profile21-evidence 共 17 文件约 27 KB，此小型诊断不属于百万门性能采样。

H 在现有 ModelStorage 中复用不可变 owner 的结构验证和 arc-index 唯一性；每次仍检查可变 fallback 标量及 patch 的负载、旧值、身份和边界。公开 validator 复用原规则，timing-check 不新增 transfer 的索引唯一性限制；新模型发布前完成分配。补充缓存命中非法标量、坏表、重复索引和值别名、实际分配点失败重试以及公共 patch 拒绝测试，并将低层 RC 夹具规范到已有 CSR 单位/表签名。两项独立静态审查通过，source22 已在新目录开始 OFF/ON/无 CUDA 验证，运行结论尚未取得。

百万门资源汇总自检与 lint 通过，记录 PID/TID 身份、累计 CPU 活动下界及有效观察间的 CPU equivalents；包含加载阶段，不能作为纯 STA 并行度。正式的 1/3 样本仍未执行。G 的候选与报告按需读取、完整阶段验收和外部工具对照仍待完成。


### H 运行验收通过，G 候选读取开始验证

source22 的独立 Release OFF/ON/无 CUDA 构建、相关组件及 native/physical 回归、隔离 binding、跨构建值比较通过；OFF mixed 的 memcheck/initcheck/racecheck/synccheck 和 fallback 的 memcheck/initcheck 通过。88 份证据约 119 KB 已取回 `checkpoint22-evidence` 并逐项校验。

同输入 profile22 实际批内 child/table validator 调用由两批 5/30、3/18 降为 0/0、0/0；阶段外准备/查询等仍记录 11/66 次，全程入口总数为 8/48 → 11/66；这里只证明批内重复扫描消失，不能宣称完整生命周期校验总量或总耗时降低。公开结果对 native 及实际 API/telemetry 比较通过，末轮完整物化仍为 37,696 B。17 份剖析证据约 28 KB 已取回；它是小用例调用证明，不是百万门采样。

G 候选查询改为准备合法 net 及实际驱动输入的 IDs，按所需 ID 收集标量；resolver 直接返回原 map entry 的身份与绑定，删除全图名称/反向身份中间表。成功前分配完整、同代缓存复用；空请求保留缓存，已有完整结果可直接提取。新增稀疏/重复/空请求、实际分配点失败重试、输入 slew 与固定输出 slew 评分反例、clock-slew 消费正负对照和真实时钟 gather 检查。两项静态审查通过；source23 已在独立目录启动 OFF/ON/无 CUDA 验证，运行结果尚未取得。clock 组件检查不等于完整物理 CTQ 闭环验收。G summary/paths 按需读取及百万门 1/3 验收仍待完成。


### G 候选夹具失败与修复

source23 的 OFF 相关回归有两项物理测试失败：新增夹具错误要求不同输入 slew 下，经 RC 计算后的输出 slew 严格相等。固定 Liberty slew 表不能保证这一点。诊断版原测试仍 exit=1；诊断驱动 exit=0 只表示完成取证。六位小数相同不代表数值相等，也不能据此确定实际 RC 求解分支。首次诊断脚本的编译失败一并保留；15 份小型证据已取回并校验。

修复仅改测试：在真实准备结果的副本上只改变独立输入槽的 data slew，要求评分改变，恢复后要求完整结果相等；保留两种真实输入、三批提交、native/CUDA 完整候选比较、clock 正负对照和查询/物化一致性。没有修改生产计算或容差。两份独立静态审查通过；使用原生产对象、原编译参数的独立 OFF 预检已启动，运行结论尚未取得。ON 原相关回归也返回非零，具体失败记录待收尾核对；无 CUDA 后续检查仍在运行。

报告按需读取的设计已审查，生产实现及百万门 1/3 测量仍未完成。本批后续改动未提交推送。


### G 候选修复通过，报告按需读取进入构建验证

source23 终态 driver=1：OFF/ON 各有 native 与 CUDA physical 两项失败，无 CUDA 有 native physical 一项失败，均为同一新增夹具错误要求两种输入下输出 slew 完全相等。其余相关构建、回归、隔离 binding、跨构建结果及 OFF mixed/fallback CUDA 检查通过；失败未改写为通过。

candidate24 只重编修复测试并链接原 source23 生产对象，OFF、ON、无 CUDA 的对应运行均通过。实际 GDB/libcudart 剖析中，首次 3/4 个候选请求分别 H2D 24/32 B、D2H 96/128 B、一次 gather 和一次等待；已有缓存/完整结果的请求无被跟踪 CUDA API 调用。此为小型功能夹具的调用证据，不是性能样本，也不证明整个物理闭环已经完成。合并证据 123 文件、压缩159175 B已取回并逐项校验。

报告低层新增当前 generation 稀疏 node/path 缓存、批量投影读取及 partial→full 补缺项。测试覆盖重复和空请求、完整结果复用、真实编辑/pending/放弃，以及 ON 实际 host/CUDA 分配点失败后重试。独立静态审查通过，source25 全新 Release OFF/ON/无 CUDA 构建已启动，运行尚未验收。部分缓存升级仍需暂存和装配；生产 summary/paths 调用者、clock/path 闭包及全 N scalar 读取尚待迁移，不能宣称 G 完成。字段解码公共 helper 在该冻结之后提取，尚未构建。

Stage 14.6 整体验收和百万门 1次预热/3次采样仍未完成；后续差异未自动 commit/push。


### 2026-10-18 提交检查点

按用户要求提交并推送当前阶段性改动。提交前两仓库 `git diff --check`、修改 Python 文件 lint 和语法检查通过；功能 timing 与性能入口的 8 项 Python 行为测试通过。04:56 UTC 核对 source25 仍在独立构建中，本次提交不声称其运行验收通过；冻结后提取的公共字段解码 helper 尚未构建。保留前述失败记录、G 生产报告调用者迁移及百万门测量等未完成事项，Stage 14.6 不标记完成。


### G 报告前驱链检查点

新增端点及固定 tag 路径、有效时钟前驱链的批量准备，复用当前 generation 的稀疏缓存；提取共用 CRPR 根节点解析。组件测试覆盖重叠链、跨 block、缺失 tag、有效槽无路径、ideal/propagated clock、缓存复用及实际分配失败重试。两项独立静态审查无剩余阻塞；生产 summary/paths 调用者和全 N 标量消费者尚未迁移，不能据此宣称报告路径优化完成。

source25 已结束，driver=1：OFF/ON 各两项 CUDA session 测试失败，原因是重复查询断言把首次物化新增的合法投影 kernel 也计入了重复查询区间。修复改为比较首次查询后的计数，并同时核对传输、分配和等待；不修改算法或容差。OFF/ON 后续完整回归未执行；无 CUDA 构建、相关回归和隔离 binding 通过，原失败保留。

包含上述修复、链准备及字段解码提取的 source26 已冻结，归档 SHA256 为 55e8000f5d06c3e705127f877e305abe838780a21e5a0000dcc39386230525a2。05:13 UTC 在 GPU 2 的 stage146-batch26 会话核验容器及共用 512 GB、swap=0 限制；独立 OFF/ON/无 CUDA 回归正在运行，本检查点不宣称其通过。源码身份与本次提交前工作区一致。

本次按用户要求提交推送开发检查点。Stage 14.6 整体验收、生产报告接入及百万门 1 次预热/3 次采样仍未完成。


### G 生产报告接线与 source27 验证

生产 CUDA 报告入口已接入端点、CRPR 时钟及选中路径的批量准备；reader 只解码已准备值，沿用原报告排序与选择。在 source27 冻结时，公开全 N AT/RAT/slack 消费者仍触发完整物化；后续标量迁移记录见下节，G 尚未验收。

独立审查修复了三处问题：parallel ordinal 跨 child 编号导致 native rank 错配；完整结果缓存中的 missing-tag 默认对象污染后续查询；reader 对 native resolver 的循环构建依赖。分别改为受影响邻接内按实际 child 配对、每个准备边界清除解码缓存、把原只读 resolver View 移到现有 contract 目标。补充完整/稀疏并行弧与重复查询行为测试，两份静态复核通过，运行待验。

source26 最终 driver=1：OFF/ON 编译成功，各两项 session 测试失败于报告链夹具没有 tagged path seed，却要求完整路径闭包；仅该组件夹具补充实际路径种子，保留独立 CPU view 计算对照，不改变生产输入校验。CUDA 后续主回归与 sanitizer 未执行；无 CUDA 的既定构建、相关回归和隔离 binding 通过。27 份小型证据已取回 checkpoint26-evidence，压缩 6560 B，归档和成员哈希核验通过。

source27 冻结 156 个变更文件、72 个删除，归档 SHA256 为 0cc745b3dd00814f2d07bb8a3681e62d1b2d52dafaffac8322a07a6ae8884861。首个启动脚本误改日期路径，未启动构建；失败脚本保留，v2 使用同一源码快照。05:46 UTC 已确认 GPU 1、tmux stage146-batch27-v2、固定镜像及实际共同 512 GB/swap=0 限制，OFF 配置成功并开始构建。独立 OFF/ON/无 CUDA 矩阵追加报告与 scatter 回归，尚无通过结论。此后差异未提交或推送，百万门 1/3 测量仍未执行。


### G 全节点标量读取提交检查点

全 N AT/RAT/slack 改为独立标量读取，物理查询、benchmark consumer 及 trace replayer 均已迁移；报告继续按实际需求准备节点细节和路径。查询复用同 generation 已有字段，完整查询只补缺项，保留 pending/poison 拒绝和提交失效。共用一份设备投影 scratch，不增加独立设备容量池。

新增回归覆盖不同查询顺序的真实回传字节、空图、重复读取、事务放弃和提交失效，并在 ON 枚举实际 host/CUDA 分配失败及重试。独立静态审查发现部分报告缓存后读取标量应复用设备容量、零 cudaMalloc，已修复测试的错误正计数断言；两份审查无剩余静态阻塞。部分缓存补缺仍有暂存及 host 复制，完整结果后再请求标量会增加约 24N bytes host 缓存，不宣称零复制。

05:59 UTC 只读核对 source27 仍在运行，OFF 配置成功、构建未结束；该快照不含本组标量改动，不能作为其验证证据。本次两仓库差异检查通过，新增标量代码及测试尚未编译运行。按用户要求提交并推送开发检查点，保留已有失败记录；完整 Stage 14.6、剖析及百万门 1 次预热/3 次采样尚未完成。
