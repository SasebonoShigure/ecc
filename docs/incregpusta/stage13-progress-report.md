# Stage 13 实施记录

日期：2026-10-01。物理四模式、共同事务、greedy、当前 generation 产物及服务器验证已落地；Stage 13 尚未标记完整完成，GPU CI 的运行方式待确定。Stage 12 已按用户要求提交：ECC d91e536、ecc-tools 42b64be72，未 push。Stage 13 于 2026-10-08 按用户授权本地提交，ecc-tools 为 5429fc3d9，未 push；提交不改变下述未完成项。Stage 12 正式性能门仍为 not_run。

## 当前验收结果

| 项目 | 实际结果 |
|---|---|
| xtea / usb / zipdiv，Q/D 各两批，四模式 OFF/ON | 48 个目标进程、12 个独立 fresh 进程成功；96 项公开结果比较、48 项完整诊断比较通过 |
| 物理连接/坐标、RC、timing/winner/CRPR/checks、levels、实际模式 | 完整比较通过，四类诊断 canary 均拒绝；真实 incremental 无 full fallback |
| 共同事务、回滚/放弃、恢复后继续提交、查询和产物失败重试 | 对应 native/parent 回归通过；成功提交不自动撤销 |
| 生产 greedy 与 routing | zipdiv 四模式实际提交后对 fresh 通过；CUDA/incremental 完整 routing 通过，最新 OFF/ON 公开结果相同。xtea/usb 的 no-positive-gain 不计增量通过 |
| 独立 Release 构建 | OFF 164 项、ON 194 项相关 CTest 通过；默认未指定 CUDA/debug 的无 CUDA 构建 148 项通过。最后查询改动后三构建各 4 项复验通过，真实 binding 路径/flags 一致 |
| Sanitizer | CPU ASan/UBSan、CUDA memcheck/initcheck/racecheck/synccheck 通过；沿用已记录的 Logger ODR 抑制，未关闭泄漏/UB 检查 |
| Parent | 1701 项非集成测试通过；默认 RTL→GDS 完整集成通过。RCX→signoff 因 PDK 缺失 SS Liberty 失败；独立 iRCX 接口测试的 SIGSEGV 仍保留 |
| 静态检查 | 修改源码 lint、工作流 YAML、两仓差异检查通过；新物理模块/查询定向类型检查通过。全仓 ty 为 2174 个诊断；同环境修改生产源码 Pyright 69 个，基线 71 个，无新增诊断 |
| 剖析 | 实际分配阳性对照、按阶段 CUDA trace 和查询延迟行为通过；初始模型分配、容量增长、必要全图传播与 levels 回传单列，不声称零分配或性能通过 |
| CI | CPU 工作流已修改，服务器手动 GPU correctness 已验证；无已注册 GPU runner，未新增 runner/SSH 凭据。托管运行 not_run，GPU CI 接入待用户选择 |

原始证据在 /home/qianhan/code/stage13-20260928-163421；主要日志和摘要已取回同名本地目录。下文为各轮历史记录，旧的“待完成/未运行”状态由后续记录和上表更新，不删除失败历史。


## 已完成的准备与数学改造

- Stage 12 源码与验收清单的 130 个文件一致后提交；CLAUDE、独立报告、overview 和 Stage 13 文件未纳入。
- 独立设计审阅第 1 轮 request-changes、第 2 轮 approve。共同完成点、worker 外恢复记录、driver 单写入者、propagated 语义、合法化几何及产物消费约束已写入详细计划。
- 新增 DB-free 树形 RC 的 Arnoldi basis、DMP pi/load 结构模型，以及 CPU/CUDA 固定阶数谱、residue、波形、Ceff 和 driver/load 求值。复用既有 NLDM 插值增加连续 raw-load 入口；无寄生 ceil 路径不变。原生 DelayCalculator 算法不变，头文件仅增加 ON 对照测试的受限访问。
- 独立审查指出 DMP 中间溢出会丢弃有效 Arnoldi，已修复并增加有限极端输入回归；CUDA 测试补充归一化、正交性、residue、五阶及不同 launch 的完整数值比较。
- 仅 ON 的独立 native DCTask、Arnoldi/DMP 直接对照已通过，覆盖连续 NLDM、单位缩放、输入 slew、阈值、rise/fall、min/max、退化 pi、分支和链。原生重建使用原始 RC 与 pin load，不复用目标计算答案。
- 原始 RC 树适配已通过：按电阻输入顺序 DFS，Ohm 转 kOhm，wire/pin 电容各计一次；相同负载 lane 共享模型，非法连接、环、歧义名称和负值在入口拒绝。
- 修复 DMP 非有限第二极点被当作合法 fallback 的问题；区分结构模型有效与求值成功，缺表和求值失败保留真实状态。
- 非负 residue 的长尾在普通原生步进 4096 次后使用单调性缩小原步宽区间，再调用既有求根过程；极点跨度大时不再做十亿次步进。独立原生可运行规模、解析长尾及不同 GPU launch 对照通过。

## 导出、局部更新与传播时钟

- 原生 Liberty cell arc ordinal 与负载端阈值已进入导出和身份编码。ordinal 来自真实所属 cell，拒绝不同 owner 下值相等的假绑定；不会把 table interning 当作 native child 身份。
- RC net 和 start seed 的 reference delta 使用局部旧值、变更槽位与追加记录。撤销保存实际旧状态，容量预留后 apply；不复制全部 seed 或历史前缀。稳态分配测试区分必要扩容和本批局部工作。
- 混合 RC/no-RC 校验按 net 判定。存在一个 RC net 不再关闭其他 net 的负载、零延迟和 transition 校验；新增反例验证错误的无 RC 数据仍被拒绝。
- CPU reference 与 CUDA 按 clock owner 选择 effective clock：propagated 使用本轮 physical arrival/slew/predecessor，ideal 保持既有零延迟语义。CUDA 删除重复的 effective arrival/slew 数组。
- SDC 原解析器此前静默忽略 set_propagated_clock；现按已有显式名字、列表和变量解析，先核对全部 clock 再设置。未知或空名单拒绝；不声称实现完整 Tcl、通配符或 all_clocks。
- flat、Dual-CSR 和 Python 的 effective clock、deferred launch 校验已同步。native scalar RAT 保持原 endpoint 计算口径；真实路径的 CRPR 仍由既有报告后处理负责，不在 scalar RAT 重复加校正。
- ON 独立 native/CUDA baseline 已覆盖非零 propagated clock 和 malformed SDC。Q/D 各两批逻辑编辑在 CPU mixed、CUDA/full、CUDA/incremental 对 fresh native 比较通过；独立审查要求额外断言每个实际 prefix 为 propagated 且 CK 延迟非零，已补入，带该修正的重跑进行中。
- 下一组已接入 full 导出的共享 RC owner：一个 net 一份结构模型、相同负载 lane 共用归约、图弧和 Q seed 持有同一不可变对象。所有权、电容一次计入和生命周期检查正在 OFF/ON 构建验证；尚未接通生产 RC 求值及 targeted 失效。

受影响诊断格式同步迁移：reference candidate/raw 为 v2/v3、exact receipt 为 v2、Stage 5 process/verdict 为 v5/v4、Stage 6 为 v6/v5、buffer replay probe 为 v4、CUDA full trace/verdict 为 v5、targeted/incremental 为 v6。OFF 性能汇总格式未改，不添加旧版本兼容壳；具体迁移清单在证据目录。

## 实际检查与失败

本地 g++ Release 严格构建及解析 RC、负载变化、退化、大扇出、非法输入、溢出、单极点波形和 Ceff 检查通过。服务器使用已有 GCC 14.3、CUDA 12.8、Release 优化和 fmad=false。

| 检查 | 当前结果 |
|---|---|
| 服务器独立 CPU/CUDA 严格编译与解析数值检查 | 通过 |
| CPU ASan/UBSan 数学模块 | 通过 |
| CUDA memcheck、initcheck、racecheck、synccheck | 修复后通过；零错误/零 hazard |
| 独立 OFF/ON CMake、既有插值测试 | 通过 |
| 数学模块独立 native 寄生对照（ON） | 通过；尚非完整生产传播链 |
| 相关 OFF/ON 原生严格构建、输入/结果/局部更新、CPU/CUDA 与既有 frozen trace 回归 | v27 通过 |
| propagated Q/D 两批逻辑编辑 | v29 通过；审查补充的非零 clock 断言待重跑 |
| 修改 Python lint | v30 通过 |
| 相同 24 个 Python 文件相对 Stage 12 的 type check | baseline 195 错误；当前连同新增脚本共 25 文件 178 错误，仍未通过 |
| 生产四模式物理 trace、完整回归与 binding 隔离 | not_run |

原始失败保留：
- 第一次 CUDA initcheck 报告测试传输结构的填充字节未初始化。使用 0xff 哨兵初始化传输缓冲并验证所有数值/状态，修复后四项 CUDA 检查通过。
- 完整 CMake 首次未找到拆分安装的 CCCL。已复用 Stage 12 固定头文件目录重新配置，无依赖升级。
- 首次原生对照编译使用了不存在的枚举值，改为已有 kPositive 后通过；长尾补丁的严格编译发现缩进歧义，修复后通过。
- 两次 GPU 启动因占用检查拒绝，未执行测试；随后空闲 GPU 5 上完成数学与 sanitizer 检查。
- 首次远程同步指向服务器旧工作区，基线哈希检查拒绝且未写文件；改用新的隔离执行快照。模板展开错误均发生在工具执行前，未修改文件。

后续检查的实际失败与修复：
- v11 分配计数测试把断言字符串本身分配计入 apply；将计数范围限制为实际操作后通过。v20 的小 seed fixture 触发了真实容量增长，改为先预留稳态容量再对比，并保留扩容行为单测。
- v13 构建目标名、v14 serializer helper 和 v17 新字段 fixture 编译问题均已按现有接口修复。v18 raw KAT 的旧版本字面值导致失败，v19 同步后通过。
- v15、v16 暴露既有 frozen 输入的指纹/种子不匹配；两份 trace 从相同输入重新导出，仅迁移 library/timing 身份，保留原编辑。相对原文件的字段差异另有清单。
- v19 real trace 生成的相对输入路径受工作目录影响，显式使用原 test/timing_edit 目录后完成。v21 混合 RC fixture 的 node net_name 为空，改用真实有 net 绑定的 chain 后 v22/v23 通过。
- v24 CUDA 测试还引用已删除的 effective 数组、v25 漏迁一个内部函数签名，分别修复后 v26 OFF/ON 回归通过。
- v26 独立 native baseline 揭示 SDC 命令根本未生效；修复上述原生解析入口后 v27 baseline 和 frozen 回归通过，没有放宽比较。
- v28 新小 fixture 调用了要求至少十个位置的自动选点入口，准备失败。v29 改用已有显式 Q/D 位置参数后通过。审查又发现测试可因两端均 ideal 而伪通过，以及 targeted 字段读取路径不符；已补非零时钟断言并按实际 published_observations 读取，等待 v30。
- v27 同范围 Python type 对比发现三条本轮新增错误，修正永不返回的错误函数声明及局部字典类型；随类型收窄显露的固定 2×2 数组表达也已修正。既有错误仍保留，未宣称类型检查通过。

## 尚未关闭的限制

带正负混合 residue 的极端长尾仍受普通搜索上限约束，不能套用非负 residue 的单调性证明；超限返回数值失败且不发布结果。该边界仍须处理，未解除生产 unsupported。

DMP 数值模块与无 RC 的 propagated clock 逻辑路径已取得上述组件证据。生产 RC 求值及局部失效、非零 CRPR 报告验收、共同物理事务、物理 fixed trace/greedy、当前 generation 产物和 CI 尚未完成。新增 baseline、逻辑 trace 和数学检查均不替代 Stage 13 验收。

## 证据

本地：/home/shigure/code/stage13-20260928-163421，包含基线身份、补丁、备份、提交核对、源码清单和运行脚本。

服务器：/home/qianhan/code/stage13-20260928-163421。独立执行快照在 current/ecc，保留 Stage 12 目录和服务器旧工作区。rc-model-check-v6 至 v9.log/.exit 保存后续实际检查；v9 退出 0，包含 RC 树、完整数值模块、sanitizer 和 OFF/ON CMake 对照。早期失败日志保留。构建和实验使用既有 Docker 入口及共同 512 GB 硬上限、swap=0。

后续证据：rc-model/rc-native/rc-mixed/clock-native 的 v10–v27 日志及退出状态，clock-trace-v28/v29，Python lint/type 原始输出和同范围 baseline 比较。rc-source-vN.json 记录隔离快照的前后 SHA；后续结果见各版本记录，不将启动状态计为通过。

### RC 共享绑定验收（v30–v31）

v30 的新测试错误地将存在输入弧的 Q 当作 deferred start，OFF transfer contract 因 fixture 假设失败；改为真实删除 Q 入/出弧、保留仅 driver 的 RC net，验证 seed 独立保有模型生命周期。v31 Release OFF/ON 严格构建与相关组件、独立 native/CUDA baseline、传播时钟 Q/D trace、Stage 5/6 frozen 差分及 controller 检查均通过，退出码 0。传播时钟 trace 额外检查 launch/capture CK 的非零物理 arrival 及五类 effective/physical 字段一致，避免退回 ideal 仍被判通过。独立审查已关闭逐弧 RC 深比较和 driver pin 电容漏计两项 finding；binding 只比较 owner/terminal，独立值比较归属测试。

证据：/home/shigure/code/stage13-20260928-163421/clock-native-v31.log。这些结果不代表 RC production backend 或物理事务已接通；本阶段继续实施。

### RC live 求值接线（v32 起）

CPU reference 的图弧初始化、动态 cell 传播、Instance clock-to-Q 现调用共享 RC 数值 helper，按实际 driver/native child/analysis/transition/slew 缓存；CTQ 副本与 Liberty graph child 身份分离，hit 不重新发布 driver。v32 独立 native 数值对照、OFF/ON 相关回归和 propagated Q/D trace 通过，退出 0。CPU associative cache 只记录实际调用，不建立 clock/tag/fanout 笛卡尔积；CUDA 仍计划复用已实现的有界行缓存。

审阅补充两项修复：DMP 有限正常不可用继续普通 NLDM，非有限仍硬失败；普通 NLDM 使用 native DFS root load，保留 ceil 查表敏感的求和顺序。新测试覆盖 raw slew 外推负值但 ceil 查表有效、A miss/B miss/A hit、CTQ 独立身份和两种缓存的 signed zero 行为。v33 新测试误调用 native 私有方法，编译失败；移到已有诊断 friend 后 v34 修复通过。terminal 求值只读取完成的 driver 响应，不为每个 child 建立完整 fanout map；v34 独立 native 对照、CPU ASan/UBSan、CUDA 四项 sanitizer、OFF/ON 相关回归及 frozen 差分均通过，退出 0。

剩余接入包括输入端口全局库阈值、net 初始化与传播、RC 初始化时 native driver 内访问顺序、受影响 net/CTQ 的局部刷新及 undo、CUDA 打包与并行 owner。公开 RC unsupported 尚未解除，不能将上述子模块结果当作四模式 RC 或生产 Stage 13 通过。


### 输入端口阈值与 net 接线（v35 起）

现有 ParasiticModel 保存一份全局 TimingLibrary 的 derate/lower/upper（共五个值），内部 view 借用该记录；不复制到每个 net，不引入运行期开关。空 RC 域仍归一为默认值；非空域保留有限退化阈值，由 native 等价求值选择 fallback。导出、独立 raw 投影、指纹、测试 wire 和诊断 JSON 同步迁移。

v35 严格构建和 OFF 其余检查通过，controller selftest 因一份 deep 字面输入仍缺少新增阈值失败，ON 未启动；迁移字面输入与身份后本地自检通过。原始失败日志保留。26 个修改 Python 文件 lint 和两仓库差异格式检查通过；一次 lint 调用因文件列表为空误扫证据目录，结果单独保留，随后以显式非空文件列表重跑。

CPU net 初始化及动态求值已接入缓存、输入端口、原始 RC 树 fallback。独立审查发现无效 fallback 可能被解释成零延迟，已改为数值失败，并增加真实有限 RC 树产生 impulse 溢出的用例。v36 的数学 sanitizer 与 OFF/ON 组件通过，propagated trace 因新 JSON 阈值使用裸数字而非既有 semantic number 格式失败。修复 serializer，并让 canary 先接受完整合法对象后只破坏目标字段；v37、v38 同库/跨库 sink、真实 native 初始化和完整所选回归通过。上述进展不解除公开 RC unsupported，也不代表完整生产 RC/物理阶段验收通过。

### 初始化顺序及 frozen 身份迁移（v38）

CPU RC 初始化只为 RC 非空 cell 收集 (driver, native cell ordinal, ArcId)，按 driver 内原生顺序求值；物理 Arc 槽位、传播候选和无 RC 路径不变。新增碰撞用例验证反序槽位、disabled/loop-disabled 初始化、相同 slew 下最后真实 miss 以及 A hit 不覆盖 B；独立审查无剩余 blocker/major。该用例属于组件层，不替代完整生产验证。

全局 RC 阈值加入身份后，两份 frozen trace 仅迁移八个 parasitic/timing_input 指纹字符串，原输入、编辑、执行参数均未改。修改前后逐字段清单及备份保存在证据目录；初次宽泛替换被自动审核拒绝，补充只读差异证明和限定字段断言后完成精确迁移。v38 独立 Release OFF/ON 严格构建、native RC、CPU/CUDA baseline、propagated Q/D、Stage 5/6 frozen 差分和 controller 均通过，退出 0。

26 个修改 Python 文件 lint 通过；type check 仍有 178 个错误，相对 v30 归一化诊断未新增，不能称为全仓 type check 通过。原始结果见 clock-native-v38.log、ruff-v37.log、pyright-v37.log 和 python-type-comparison-v37.json。

### CUDA RC 结构与 table 接入（v39 起）

新增按 net 打包的紧凑归约/terminal 数据，相同 owner 的四个 lane 共用 payload，重复打包复用容量。Liberty 子表继续值复用，但原生 driver 缓存身份不使用 table 索引。设备 Child 增加真实阈值及库身份，raw-load 插值不做普通 NLDM 的 ceil；设备 driver/load/port/raw fallback 调用既有数值模块，不上传 native timing 答案。

独立调用链审阅确认：graph child 每 analysis/output 的不同 input-slew 上界为初始化一次、clock 两次、data 两次，共五条；CTQ 独立域一条。arrival/RAT 仅读取已完成弧延迟，不按 tag 或 fanout 扩大缓存。RC 初始化必须按 driver 单写入，slew 选定后按最后真实 miss 发布只读 driver 索引；v43 已完成 full 并行 owner 接线，targeted 局部更新仍待完成。

v39 严格编译发现新测试缺少 ista namespace 引用；修正后 v40 独立 OFF/ON 严格构建、相关组件、native RC、baseline、propagated trace 和 frozen 差分通过。公开 RC unsupported 保留，模型组件不计作完整 CUDA/物理事务验收。
### CUDA full RC 接线与检查器修复（v41–v43）

full 路径按 driver 并行初始化 RC，driver 内保留 native cell ordinal 顺序；clock、CTQ、data slew 完成后选择最后真实 miss，net load 只读已完成响应。记录按 graph child 五条、CTQ 一条预留，缺容量/数值失败不发布；无 per-tag/fanout 缓存展开。full/work 图各自持有仍使用的 RC owner，成功上传后才确认可复用；失败先排空 stream，再恢复原图。

v41 initcheck 报 6150 次未初始化读取，来自测试复制整份 driver record（含填充）；删除这份无消费者副本后，v42 剩余 2050 次来自输出结构的主机传输填充。v43 对测试输出区使用 0xff 初始化，并继续断言全部状态和数值；memcheck/initcheck/racecheck/synccheck 均零错误。未初始化读没有通过关闭检查或放宽容差掩盖。

v43 退出 0：Release OFF/ON 相关严格构建、完整 combinational RC 组件 CPU/CUDA 对照、两种 launch 一致、native RC 数值、非零 propagated Q/D、既有 Stage 5/6 frozen 差分全部通过。独立审查未发现确定的 full 并发/回滚/异步生命周期 blocker，但发现未变 RC 在 H2D 之前仍被重复打包，已将打包移至 owner mismatch 分支，后续验证单列。

这些检查仍不代表生产 RC 通过。新增 propagated-clock/CTQ RC 及 full 放弃、数值失败、连续提交和按需查询测试正在运行；targeted RC 显式拒绝仍保留。完整物理 trace、共同事务、greedy、产物与 CI 仍未完成。证据：cuda-rc-v40 至 v43.log/.exit、rc-source-vN.json。


### CUDA full 生命周期及局部 RC 事务（v44 起）

v44 新测试调用私有 full 入口，编译失败；移至已有 test friend 后，v45 Release OFF/ON full/mixed 回归通过，ON memcheck/initcheck/racecheck/synccheck 均零错误。覆盖 propagated-clock/CTQ RC、两种 launch、无查询连续提交、放弃、数值失败和继续提交；未变 owner 不再重复打包。

native 事务增加显式 prepared pre-route tree 输入，要求 placed edits、完整 post-edit terminal 和一棵连通树。raw apply/undo 移动 map node handle，保存实际旧对象；不克隆 Database/Liberty，也不把 descriptor expected 当撤销数据。targeted 每个受影响 net 只准备一份模型，更新 driver 和全部 terminal（含未移动 sink），撤销恢复旧共享 owner。full 使用同一 raw RC 撤销。

v46 编译发现旧测试仍调用已删 models.transfer，迁移至实际 arcOrdinal/cell 消费；v47 新 RC fixture 沿用 no-RC corner，导出正确拒绝，改为显式 pre-route context。v48 两套 Release 的五项 host 事务/输入回归通过，退出 0。raw 测试覆盖连通性、非法数值及 apply/undo 零分配；full/targeted host 覆盖两代提交与放弃。这些不是物理共同事务或设备 RC 增量验收。

独立审查补充 Q driver 和模型准备溢出的真实撤销测试。v49 fixture 头文件相对路径错误导致编译失败；修复后 v50 暴露 Q fixture 的 Database 赋值复制 Liberty 后保留旧 Arc 指针，正在用显式 fixture 重绑定修复并复验。

CUDA targeted RC 初版按受影响 net 准备模型/cache rows，复用已有 full_work 的逐 net 设备容量。buffer 与 descriptor 配对交换；Arc/独立 Q seed 的 binding 索引稳定，所有新增 node→net 槽定义为 absent。描述符和 binding 批量散写；撤销读取实际 committed 数据，仅保存一份供 host/device 共用。两项独立审查 finding（full packing 的 host binding 初始化顺序、重复 undo 副本）已修复，设备回归进行中。

证据为 cuda-rc-v44 至后续版本的 .log/.exit 和 rc-source-vN.json。公开 RC unsupported 仍保留；FLUTE/物理事务、固定物理 trace、greedy、当前 generation 产物与 CI 尚未完成，Stage 13 继续实施。


v51 OFF 严格构建通过，CUDA full/mixed 的新 targeted fixture 因 transfer/table 签名与阈值不符合公开输入规范而拒绝；修正 fixture，没有放宽 validator。host Q fixture 的旧 Arc 指针修复后，v52 又检出它并非 deferred Q，已仅移除 Q 入弧、重建邻接并保留其 RC 出网、顺序实例及 clock/check 元数据。v52 CUDA 容量增长 fixture 新增起点却没有 seed，现改为无新增 start 的孤立节点。v53 OFF 八项回归通过；ON 严格编译发现分配扫查忽略 nodiscard 返回值，已显式处理，正在复验。

新增 native→CUDA RC 联调复用 host 事务 fixture、真实 patch 及既有稳定 ID 结果投影，覆盖两批 Q/端口编辑、放弃后设备重传播和 full/mixed。ON 使用独立 fresh CPU reference 比较完整 timing，levels 单独检验合法性。该联调尚不包含 IDB 物理事务，也不是三设计 fresh native/full 验收。

### 2026-09-30：RC 局部事务联调与物理 RC 构建

- v54–v56 的失败分别定位为组件 reference 未明确处理现有 RC gate，以及 Q 测试夹具带有额外 clock-divider/case-analysis 和错误 cell graph flags。修正夹具后，v57 OFF/ON 的 host 事务及 native→CUDA 事务检查通过：port/Q 两批、full/mixed、放弃后实际设备重传播、继续提交。未降低数值容差，未解除生产 unsupported。
- v58 sanitizer 第二个进程在 CUDA stream 初始化时报错，未完成整组检查。v59 独立复跑中 memcheck、racecheck、synccheck 通过；initcheck 报告 12 次 RC binding 扩容时的未初始化 D2D 源字节。设备结构原为四个 uint64 加 bool，kernel 字段赋值未初始化尾 padding。改用同体积的第五个 Index 消除空洞；修复后的 sanitizer 结果待记录。
- 新增 pre-route RC builder，复用 FLUTE 和 IDB routing 层参数，按原坐标构树，重合 terminal 用零电阻边保留身份，不重复加入 Liberty pin cap。独立审查发现真实 pin 名与 FLUTE 内部 steiner 名可能冲突，已改为局部映射并加入测试。LEF edge-capacitance 缺失值显式初始化为 -1，缺失参数继续拒绝。
- v60 首次严格构建被既有 IDB 头文件告警阻断；新模块保持严格告警，IDB 依赖头以 SYSTEM 引入，等待复跑。物理 RC 测试涵盖层选择、DBU、解析 R/C、对角线、重合与单 terminal、load 顺序、保留名及坐标溢出。

原始命令、退出状态与日志在 stage13-20260928-163421/cuda-rc-v54 至 cuda-rc-v60 对应文件；源身份见 rc-source-v60.json。上述为组件证据，尚不能替代三设计 post-CTS 物理 trace、共同提交、生产 preset、产物及最终回归验收。

### 2026-09-30：物理 RC 与 prepared IDB 批次

v61 退出 0：独立 Release OFF/ON 的 pre-route RC 构建和 native→CUDA RC 事务用例通过；同一 ON 二进制的 memcheck/initcheck/racecheck/synccheck 均无错误。v59 的 binding padding 问题已由实际 initcheck 复跑确认修复。

新增 PreparedPhysicalBatch，限于生产 owner 单操作 guard 内的已解析物理编辑。准备阶段只复制受影响 net 的连接引用，构造新 buffer/net，并预留全局容器容量；apply 迁移预建名称 map 节点，交换连接引用和真实 pin net/name。撤销保留原顺序、ID 和 net 平均坐标缓存。共同 owner 尚未接入，该组件尚不能宣称跨层原子提交完成。

v62 缺少测试直接调用的 geometry_db 链接，已修复。v63 测试崩溃源于新夹具创建 IO pin 后遗漏 term；v64 因镜像没有 gdb 未取得堆栈，随后通过源码调用链定位并修复夹具。v65 OFF/ON 全部通过：准备不改变逻辑状态，apply/rollback/commit 实际分配计数为 0，双 net 高扇出、move、放弃、连续提交、重复 sink 拒绝、ON 逐分配失败后原状态及连接索引一致。计数仅存在于测试可执行文件。

为保证准备失败和放弃能释放新对象，修复直接依赖的 IDB 构造、pin 引用索引、pin/shape/obs/via 临时所有权及 instance pin-list 释放。独立审查另发现 via clone 内部长名称复制失败泄漏，已改为函数内 RAII；测试补充长名称 via、obs、IO sink、镜像方向下非对称 pin 坐标。v66 正在复跑，并加入独立无 CUDA ASan/UBSan 与泄漏检查，结果尚待记录。生产 gate、preset 和共同提交尚未启用。

物理事务 v67 ASan/UBSan 首跑发现 477360 字节泄漏，根对象均为测试 fixture 的 cell master；旧 IdbCellMasterList 析构不释放 master。测试改用显式所有者，保持生产 IDB 所有权契约不变，复验待运行。v66 扩展 via/障碍/IO sink 的 OFF/ON 测试已通过，其失败仅为 Debug O0 与 Nix FORTIFY 的严格构建冲突；v67 使用 RelWithDebInfo 保留 sanitizer 和严格告警。

v68 进一步定位到 fixture 的 IdbObs 非拥有障碍层；显式所有者修复后，v69 无 CUDA RelWithDebInfo ASan/UBSan（含 leak detection）两项通过。v70 现有 IDB die、DEF/Verilog escaped names、geometry builder 回归四项全部通过。未修改旧 master/obstruction 列表的生产所有权约定。

v71：物理 RC 按真实 IDB pin 身份和朝向后的坐标生成，apply 前预备树与 apply 后重建逐字段一致；OFF/ON 及 ASan/UBSan 均通过。共享 baseline pin 名称编码，未修改 RC 支持 gate。共同操作守卫迁移的独立审查发现 global→API 锁反转，已在共享 API guard 的加锁前检查 global sentinel，并新增确定性交错测试；审查复核通过，修复运行验证待完成。桥接物理与语义编辑的代码置于 STA interface，物理 RC 模块不反向依赖 native timing edit，避免扩大旧 toolkit/interface 依赖环。

### 2026-09-30：生产物理基线、守卫与恢复日志

v72–v74 独立 OFF/ON 严格构建及守卫/native 事务回归通过。global→API 锁反转修复已运行验证；CPU coordinator 提交资格与发布分离，实际分配 hook 确认成功资格检查及 publish 不分配。CPU baseline 准备从 benchmark 移到现有 transaction 模块，生产与 trace 复用同一实现。

v75、v76 分别因新 production baseline 和物理测试缺少直接头文件/target 依赖而构建失败，补齐实际依赖后解决。v77 OFF 编译通过，CUDA session 测试在未传 GPU 的容器失败，ON 尚未执行；v78 使用空闲物理 GPU 1 后，OFF/ON 的物理基线、native 事务、coordinator、session 和 native→CUDA RC 事务回归全部通过（退出 0）。没有调整算法或容差掩盖设备环境错误。

生产物理 baseline 复用 EngineDB 唯一 IDB：先准备完整 pre-route RC，再执行所选 backend；CPU/full 只运行一次 native full。native/IDB terminal 必须构成一一绑定，错误输入先拒绝。CPU incremental 的 baseline helper 已迁出 probe；完整四模式生产支持尚未启用。现有物理 fixture 的 close 使用测试 SessionOperations，只验证 context 释放，不视为真实 closeOwned/closeStaResources 验收。

恢复日志用 flock 限制单 owner，用同目录 no-replace rename 发布每代记录，未提交 pending 在重启时删除。独立审查发现普通 open 失败会错误永久损坏 owner，以及 FIFO baseline 会阻塞：已修复，并用真实 RLIMIT_NOFILE 与 mkfifo/alarm 复验。轻量 WSL 严格编译测试通过，覆盖无分配发布、放弃、worker 在 marker 前后退出、重启、冲突不覆盖、代洞和清理失败。v79 正在执行 OFF/ON 与无 CUDA ASan/UBSan，结果待记录。未宣称断电持久性。

后续共同批次正在接线：本批恢复记录复用稳定编辑编码，保存坐标、实际模式和 generation，不保存 canonical 快照。marker 前完成计算及资格检查；marker 后复用无抛出发布。异常分支先在仍有效的 guard 中完成撤销，再根据日志/设备健康状态 poison，避免提前 poison 使 native 撤销失去资格。当前 CPU/full 生产批次代码及新测试尚待运行验证；其余模式、显式恢复、合法化、preset/greedy、产物与三设计四模式验收仍未完成。

证据位于 stage13-20260928-163421 的 cuda-rc-v72 至 cuda-rc-v79、对应源 SHA manifest，以及 physical-journal-local.log/.exit。Stage 13 保持进行中，不将组件通过计为整阶段完成。

v79 OFF/ON 相关测试通过，无 CUDA sanitizer 二进制构建完成；启动脚本末尾引号错误使 sanitizer CTest 未执行，退出 2。已改为完整写入脚本并先执行 bash -n，v80 使用物理 GPU 1 和共同内存 slice 复跑，结果待记录。

新增生产 CPU/full 共同批次及显式恢复入口，复用既有物理/native 事务。恢复一直持有初始化操作 guard，全部逐批重放成功后才发布可用状态。测试新增 marker 输出失败后、重试前完整消费者结果不变，以及损坏第二条记录、拒绝查询中间前缀、重新加载原 fixture 后恢复、记录字节不变和恢复后继续提交。测试输入仍是组件 fixture，不替代真实 post-CTS checkpoint 验收。

修改文件的 Python Ruff 首次通过；新增类型检查修复中出现行宽与布尔参数告警，已修复并待最终复验。Mypy 首次报告 233 项，已提交 Stage 12 对应源码检查报告 387 项；修复本轮新增诊断后为 214 项、与基线相比无新增错误内容。该对照不是全仓类型通过。既有 Dual-CSR controller 自测与 reference-input controller 自测通过；日志独立保存于本次运行目录。

### 2026-09-30：共同事务与按需结果复验

v80 的 Release 构建先后暴露测试 reporter 缺少直接链接，以及第三方 LEF/DEF archive 写入源码目录，令 ASan 产物混入 Release 链接。前者补齐直接依赖；后者在独立验收运行目录用 CMake project include 改写四个 parser target 的输出目录，没有修改第三方依赖。v81 的几何身份 canary 因 IDB 非 const 坐标 getter 未编译，已修正。

v82 两套 Release 严格构建及相关 CTest 分别 8/8、9/9 通过，涵盖生产 CPU/full 物理共同提交、marker 冲突撤销、两批日志重放、几何变更拒绝、恢复后继续提交和已有事务回归。无 CUDA ASan/UBSan 首次在已有 Logger 多库全局符号重复定义处于测试启动阶段退出；v83 仅关闭 ODR 重复定义检查后，物理事务和日志测试 2/2 通过，内存、UBSan 和泄漏检查仍开启。原始失败及复验输出分别见 cuda-rc-v80 至 v83 的 .log/.exit；源码身份见 rc-source-v82.json。

生产 session 增加在单操作守卫内读取当前 generation 的 timing values、公开 QOR 和 paths，底层复用原有 TimingReporter 与按需 materialize/prepareReport。重复读取及与测试现有消费者的一致性检查已写入；v84 源文件经 SHA 核验同步服务器；WSL SSH 启动前一度连接 10.19.20.9:22 超时，随后改从 Windows SSH 连接，在空闲 GPU 2 和共同 512 GB/no-swap slice 运行。OFF、ON、无 CUDA ASan/UBSan 各 1/1 通过，真实退出码为 0。PowerShell 上传的宿主脚本末尾带 CR，使退出文件初次带 CR 文件名；已读取原文件内容确认 0 并复制为规范 .exit，原文件保留作为证据。

当前通过的是组件与 CPU/full 小 fixture。CPU/incremental、CUDA/full/incremental 的生产共同事务、真实加载/关闭、合法化、实验 preset、greedy、同代产物和三设计 post-CTS 对照仍未完成。Stage 13 继续进行，不据此宣称整体正确性验收通过。

v85–v86 尝试把 CPU/incremental 物理批次直接复用 Stage 5/6 的 narrow capture；v85 首先因新源缺少 authority 直接头文件编译失败，修复后 v86 严格编译通过，但真实物理多批次用例在 capture 阶段被拒绝。定位到既有 narrow capture 明确要求 NoParasitic，且其数据准备仍按无 RC 负载投影；只去掉 unsupported 原因会让公共输入误报支持，不能作为修复。该接线及测试已逐文件与 v84 SHA 比对后撤回，服务器工作副本同步恢复为 v87；v85/v86 失败日志保留。CPU/incremental 生产 RC 继续标为未实现，先扩展受影响 RC payload 捕获或复用已验证的局部 patch，再解除对应拒绝。


## 2026-09-30：物理基线失败恢复

runSessionPhysicalBaseline 在 RC 树安装与 propagated clock 状态切换之后，若 backend、导出或恢复绑定拒绝，之前会留下已改变的 native 输入。现已在安装前保存原寄生库所有权和各 clock 标量状态，成功后解除撤销；失败时按作用域恢复。该路径不克隆整库。扩展了既有物理基线拒绝测试，在拒绝场景中实际设置一个 clock，检查拒绝后 RC 为空且 propagated 标志恢复。

服务器隔离目录 stage13-20260928-163421 中，baseline-rollback-v89.log/.exit 记录 Release OFF、Release ON、no-CUDA ASan/UBSan izh_native_physical_rc_test 各 1/1 通过，最终退出状态 0。共同 ecc-workloads.slice 实测 MemoryMax=512000000000、MemorySwapMax=0。ASan 因已有 Logger 跨共享库 ODR 重复而关闭 ODR 检测；内存、泄漏和 UB 检测仍开启。

生产物理批次目前仍仅 CPU/full。CPU/incremental 的 narrow capture 同时有 NoParasitic 策略门、无寄生负载投影和缺失弧 RC 绑定；未解除支持门，避免将错误计算标为支持。四模式、真实 post-CTS 设计、合法化、greedy、产物和 CI 均未验收。

### 2026-10-01：三设计 post-CTS 输入与物理 CPU/full 基线

- v89：生产物理 baseline 在导出或绑定失败时恢复原寄生库和 clock propagated 标志；Release OFF/ON 与无 CUDA ASan/UBSan 各 1/1 通过。v90 的 Python binding 构建因缺少 timing_csr 私有 include 失败，修正 target include 后 v91、物理入口 v92 与空网修复后 v96 的 OFF/ON binding 均构建成功；实际加载路径和只读诊断值已核对。
- 在独立运行目录复制 xtea、usb、zipdiv 原 ICS55 项目并逐文件记录 SHA-256，均完成 synthesis、floorplan、fixFanout、CPU placement、CTS、legalization（退出 0）。原始设计和 PDK 未修改。服务器 Docker 缺少 X11 runtime 库及 USER 环境变量，仅在隔离运行目录补充现有宿主 runtime 库并设置运行环境；失败的 xtea v1–v4 仍保留。最终 checkpoint 为各设计 legalization_dreamplace/output 下同代 DEF 与网表，源身份见 post-cts/*-input.json。
- xtea 首次真实物理 baseline 失败：合法化 DEF 保留零端点空网 data_out1_10_，端口实际属于 zh_fanout_net_20。native 与 IDB 均为零端点时不建无意义 RC；有端点却零驱动的网仍拒绝，错误含网名和驱动数。新增空网回归后 v94 Release OFF/ON、无 CUDA ASan/UBSan 各 1/1 通过。
- v3/v96：三设计的生产 CPU/full pre-route baseline 和当前 generation 结果读取在 OFF/ON 均退出 0。xtea、usb、zipdiv 分别返回 574、3486、5062 个 timing points；完整 timing/QOR/paths 及执行记录的 OFF/ON JSON 完全一致，SHA-256 见 physical-baseline-off-on-v97.json。baseline generation 均为 0，不计物理增量通过。
- Python 父工程 session 直接包装现有 native 物理 baseline/结果入口；test_sta_session.py 与 snapshot 回归 60/60、修改文件 Ruff 与两仓 git diff --check 通过。v4 的 xtea 真实调用退出 0，输出与直接 native v3 SHA-256 一致。
- 原始命令、日志和退出状态均在 /home/qianhan/code/stage13-20260928-163421。这批证据不包含真实物理 Q/D 多批次、CPU/incremental 或 CUDA 生产执行、DREAMPlace 局部合法化、greedy、最终产物与 CI；Stage 13 仍未完成，Stage 12 正式性能门仍为 not_run。

### 2026-10-01：当前 CUDA RC 组件复验

v98 首跑仅在未指定 Docker --gpu 的容器中执行，CUDA session 创建报 driver version insufficient；pre-route RC CPU 测试通过。按 docker/USAGE.md 修正为宿主 --gpu 2 后，v99 OFF/ON 各两项 native→CUDA RC 与 pre-route RC CTest 全通过，ON memcheck/initcheck/synccheck 各 0 errors、racecheck 0 hazards（退出 0）。GPU 2 启动前无其他进程，容器位于共同 512 GB/swap=0 限制中。该结果仍是组件级验证，物理 CUDA 生产批次尚未接通。

定向 Pyright 未通过：sta_session.py 原有 snapshot_observation_from_mapping 调用的 object→Mapping 类型错误两处（当前第 285、421 行），本轮新增物理方法无新增诊断；Ruff 与 60 项 pytest 仍通过。未升级 Pyright 或放宽检查。
随后将 native snapshot protocol 的返回类型标为实际的 mapping/None，定向 Pyright 复跑为 0 errors、0 warnings；Ruff 和 60 项 pytest 复跑仍通过。未升级依赖。

### 2026-10-01：受限 RC 输入边界与四模式物理基线

v100 的模式参数未传入 session，三次实际均为 CPU/full，保留原文件但判为无效模式证据。v101 修正驱动后，xtea 的 CPU/incremental、CUDA/full、CUDA/incremental 均以 typed unsupported/parasitic_net 退出 1，无成功文件和 CPU fallback。

新增公共 RC 绑定校验：从 raw tree 和 pin 电容核验 driver、terminal 及不可变模型；每个 owner 比较一次。受控 OFF 导出不做第二次 reduction。只有 pre_route 且所有树完整准备成功才解除寄生拒绝；一般 SPEF、断连/网状输入仍拒绝。Python 独立诊断同步检查 raw 连通性及 pin 覆盖，沿用原始数值比较。新增损坏 owner、terminal、lane 和错误 seed 绑定测试。

v102 OFF/ON 各 8 项相关回归通过。v103 OFF 原生边界/物理回归 9 项通过，但 CPU/incremental 实际基线失败；定位到 canonical validation projection 漏带弧 RC owner。ON 实际基线另发现校验把 deferred clock sink 当作 Q driver，误要求其持有 RC。已修复投影及 terminal NodeId 重映射，immutable numeric lanes 继续共享；只让真正驱动的 deferred seed 持有 RC。对应反例纳入原有测试。

v104 OFF/ON 严格构建及各 9 项回归通过；三设计四请求模式共 24 个独立进程均退出 0。CPU/incremental 的公开 timing 与 native CPU/full 完全一致；CUDA 的最大 timing 绝对差为 3.552713678800501e-15，公开 QOR/paths 一致。结果位于 physical-baseline-v8。所有这些运行均为 generation 0 baseline，不计物理增量通过；逐弧/winner/CRPR 与物理编辑完整 oracle 仍待验收。

CUDA physical full/incremental 共同事务和日志恢复已接线，targeted mixed/fallback 编排由 benchmark 移入生产 interface，仓内消费者直接迁移；详细 rejected-attempt 仅 ON 保存，实际 fallback 执行记录始终保留。新增真实 journal 冲突撤销、连续两批、重复查询、重载恢复与第三批提交测试，v105 运行中，尚不作为通过证据。CPU/incremental 物理编辑仍受 narrow capture 的 RC 支持边界限制，后续继续接入。

### 物理多批次共同提交（v106–v109，继续实施）

- v105 严格构建因测试引入不必要的 benchmark header 而失败；已移除，测试直接使用生产 targeted staging。
- v106：OFF/ON 各 5 项通过；CUDA/full、CUDA/incremental 与独立 native CPU/full 执行物理连续批次、提交标记失败后的真实回滚、恢复及恢复后第 3 批。无 CUDA CPU ASan/UBSan 通过。
- v104 三设计四模式基线结果由独立比较脚本 v106 核验：OFF/ON 完整输出一致，QOR/paths 一致，CUDA 最大有限 timing 差 3.552713678800501e-15。比较器显式处理一致的非有限未约束哨兵，有限数值容差维持 1e-10；仍仅是 generation 0 baseline。
- CPU incremental 复用已准备的局部 RC owner；只替换受影响 raw-net/launch-seed binding。v107 首轮因 raw-net 字段名及内部测试参数迁移遗漏而构建失败，v108 修正后 OFF/ON 物理四模式及原 narrow/structured 回归通过。v108 无 CUDA sanitizer 链接未纳入新增 RC capture 源文件，需重新生成构建清单后复跑；不记为通过。
- 新增 Python 物理批次与恢复入口；复用语义编辑 JSON 解析和共同事务，无测试 failpoint。父仓库 session/snapshot 61 项通过，修改文件 Ruff 与 session 定向 Pyright 通过。native binding 与新请求边界测试待 v109 验证。
- 查询设备/清理错误需将 poison 传递至整个会话；普通分配失败保持可重试。真实设计物理 Q/D 编辑、合法化、greedy/preset、最终产物及完整阶段验收仍待完成。

## 2026-10-01：物理多批次公开结果与低层合法化

- v110–v112：将 CUDA/full 准备收敛到生产与 trace 共用的 stageCudaFullBatch；修复报告清理失败时的 poison 传播、输出流分配失败处理和 RC 名称核对的重复扫描。独立 Spec/Standards 复审通过此组变更；ON 对基线和连续批次做真实分配失败扫查，失败后重试完整查询一致。
- v113–v115：原生会话维护局部 row 占用索引；父仓库复用 DREAMPlace 的 greedy legalization 与 legality check，仅本批新 buffer movable。旧实例、已提交 buffer、row 洞、blockage/fence 为障碍。复审修复 SITE 身份、行容量线性增长和传入 C++ 前目标坐标的整数范围检查；不重建 placement engine。
- v115 严格构建及回归：OFF 8 项执行通过、2 项诊断测试禁用，ON 10 项通过；无 CUDA ASan/UBSan 物理事务测试通过。服务器 Python 40 项通过，包含真实低层合法化算子。泄漏/UB 检查开启；沿用已记录的跨 DSO Logger ODR 抑制。
- 三设计 xtea/usb/zipdiv 的原 post-CTS checkpoint：冻结 Q/D 各两批真实物理编辑；OFF/ON 四模式 48 个进程均成功，另有 12 个逐 prefix 独立 fresh native CPU/full 进程成功。96 个批次公开 timing、QOR、paths 比较通过，OFF/ON 结果一致，实际 incremental 无 full fallback。该结果尚不代表完整 winner/CRPR/RC 验收。
- 新增仅 ON 编译链接、显式请求的物理诊断读回，复用既有 NeutralWire/native reader。完整诊断运行 v116 因缺少事务头的私有构建依赖停止，v117 修复后重跑；最终结果待核验。独立复审发现旧 reader 的丢弃 JSON 重复序列化及条件弧模糊绑定，已删除重复工作，并直接复用原始 rank 对应的完整语义 key。物理反向连接诊断 canary 正在补齐。
- 证据：/home/qianhan/code/stage13-20260928-163421/physical-trace-v2、physical-public-comparison-v115.json、physical-api-v110 至 v117 日志及源文件身份。原始失败均保留。本地修改文件 pyright 报 torch/dreamplace 缺失导入，未宣称通过；服务器完整类型检查待执行。

完整诊断、closed-loop greedy、实验 preset、当前 generation 产物、最终 CI/剖析及完整阶段回归尚未完成；Stage 13 保持实施中。

### 2026-10-01：完整 RC 对照与生产接入（v118–v131）

- v118/v119 严格构建、局部事务和 sanitizer 回归通过，36 个 ON/fresh 物理进程成功。v119 的最终比较器因导入路径错误未执行；修复后 v120 的完整比较检出了真实数值问题，不能用 v115 的公开 top-20 结果替代完整检查。mixed 的 active-edge 数组先按语义排序，仍分别检查实际 level 合法性。
- usb/zipdiv 的分歧来自 Arnoldi ramp 的解析边界：数学上相等的 R*C*log 与 transition 因末位舍入走入不同分支。用捕获输入建立最小反例，修复前退出 1；native 独立实现与 CSR/CUDA 实现分别在有限值边界处理 8 个机器 epsilon 的相对舍入，未放宽结果比较容差或改变迭代规则。v128 的四项 native/CUDA 组件测试、41 项 parent 测试通过；usb/zipdiv Q 各两批四模式共 16 项完整物理/RC/timing/winner/CRPR/checks 比较通过，level/winner/CRPR/timing 四项 canary 均拒绝。完整三设计 Q/D 矩阵仍需刷新。
- v121 的 OFF/ON native 回归、无 CUDA ASan/UBSan 和 41 项 parent 测试通过；xtea Q 的两构建四模式共 8 个进程，覆盖 baseline 与两次提交的同代 power/timing/SDF/DEF/netlist、旧 manifest 拒绝、真实 manifest rename 失败后重试。产物读回逐文件校验长度和哈希。缺失头文件、GCC 14 字节排序 Werror、CUDA constexpr 告警分别在 v126/v127 暴露并修复；v123 的 Python 缺 libstdc++ 是脚本覆盖 LD_LIBRARY_PATH，v124 保留容器原路径后解决。原始失败保留。
- 生产增加显式实验 preset、当前 RC/Liberty 的 greedy 选择和同代 routing handoff。独立审查修复了缺失几何产物、sizer 同名阶段误识别、DEF 读取失败未拒绝，以及输出失败不能恢复的问题。TIMING_OPT 自身重试保留 journal/累计预算，greedy 已结束时仅重试产物；从上游重跑则清除绑定旧 checkpoint 的后继历史。完整重开全流程仍沿用原 reset。父仓库相关 CLI/GUI、报告失败恢复、负实际 gain 提交及模式隔离测试通过；最终审查仍未完成。
- v129 的生产入口、几何结果门和实际 routing IDB 加载成功；xtea/usb 无正 gain，zipdiv 提交一批后无正 gain。验证脚本使用错误的 Workspace 模式键，实际全是 CPU/full，不算 CPU/incremental 证据。v130 加入 native request 断言并检出同类配置错误；v131 改用已有 STA backend/STA update strategy 参数名，正在运行真实四模式。无候选与 baseline 不计增量通过。
- 现有仓库 GitHub API 返回 0 个注册 runner；GPU CI 的接入方式待确定。服务器 GPU 验证继续，未把未运行的托管 workflow 记作通过。

本组证据仍在 /home/qianhan/code/stage13-20260928-163421；Stage 13 保持实施中，Stage 12 原正式性能门仍为 not_run。剩余包括完整矩阵刷新、真实输出重试、生产 greedy 差分、最终 native/parent 回归、剖析和 CI 收尾。

### 2026-10-01：全量回归与生产恢复（v133–v137，验收进行中）

- v131 已核对 native 实际请求及每批实际模式：三设计四模式共 12 个 ON 生产进程通过；xtea/usb 无正 gain，zipdiv 四模式均提交一批后无正 gain。前两者只记 baseline/停止原因。当前 generation DEF 已由真实 routing IDB 接收；完整 routing 尚待 v136。
- v133 OFF/ON 全目标严格构建通过。全部 CTest 分别出现 4/5 个失败：混合 RC 夹具遗漏 prepared binding、scatter 仍把 propagated clock 当作不支持、ON RC 组件测试仍手动清除旧 unsupported 标记；三处测试输入/预期已迁移，生产验证未削弱。另有范围外 ircx_interface_test 段错误，保留失败，尚未归因为本轮或既有问题。v132 缺失 snapshot contract 构建依赖已修复。
- v133 zipdiv 的两构建四模式共 8 个真实输出失败重试通过：发布时遇到 manifest 路径冲突，移除故障后重新进入生产入口恢复并发布，committed 编辑、greedy 日志及停止记录均未追加或改写。
- v134 OFF/ON 所有相关 CTest 退出 0；三设计 Q/D 四模式共 48 个进程、12 个 fresh 进程均已执行完毕，公开 timing/QOR/paths、实际模式及 OFF/ON 的 96 项比较通过。完整物理/RC/winner/CRPR/checks 的最终比较仍在运行，不提前计为通过。
- v135 省略 CUDA/debug 选项的新 Release 构建及相关 CTest 通过。独立无 CUDA ASan/UBSan 的 RC、物理准备、共同事务、journal 四项通过，泄漏/UB 检查开启；仅沿用已记录的 Logger 跨 DSO ODR 抑制。
- v136 物理 CUDA 共同事务的 memcheck/initcheck/racecheck/synccheck 全部退出 0，无 error/hazard。仓内 physical_sta_probe 已用真实 zipdiv 两批 CUDA/incremental 和独立 fresh CPU/full 运行，完整比较及 level/winner/CRPR/timing canary 通过。独立审查补齐空 trace/空 edits 拒绝、当前 generation 核对和流式摘要，未增加生产检查。
- 本地相关 parent/CLI 测试 139 项通过；类型边界修复后 31 项相关回归通过。两仓本轮修改 Python 源码 Ruff 通过。相同 Python 环境下，修改生产源码的 Pyright 从 Stage 12 基线 71 个错误变为 69 个，无新增诊断；新物理模块（除本地缺 torch/DREAMPlace 导入）及复现入口定向检查通过。全仓 ty 实际失败，2174 条诊断，原始输出保留；未宣称全仓类型检查通过。用户已有 overview 内脚本的 lint 失败单独保留，不修改用户报告。
- 托管工作流只做静态/YAML/脚本检查，尚未实际执行。现有仓库无 GPU runner，按当前接入方案保留服务器手动 GPU correctness 命令，不注册 runner；CPU-fast、native source-build 和手动 CPU integration 复用现有工作流。
- v136 的 closed-loop 独立对照、完整 routing、Nsight Systems 和 parent 完整回归，以及 v137 的真实 CPU 分配调用栈仍在收尾。硬件性能计数器权限限制保持，不改驱动或容器安全配置。数值边界最小复现的修复后独立日志为 arnoldi-ramp-boundary-fixed-v136.log，退出 0，原失败文件不覆盖。

### 2026-10-01：最终差分、审查和剖析（v134–v139）

- v134 三设计 Q/D 两批、OFF/ON 四模式与逐 prefix fresh native CPU/full 全部运行成功。96 项公开 timing/QOR/paths/实际模式比较通过，OFF/ON 相等；48 项 ON 完整物理连接、坐标、RC、拓扑、timing、winner、CRPR/checks 比较通过，level 独立合法，四类 canary 均被拒绝。未放宽容差。v136 仓内 portable probe 的 zipdiv Q 两批及独立 fresh/完整比较也通过。
- v136 当前 native RC/物理测试的 memcheck、initcheck、racecheck、synccheck 均通过，零错误。v135 默认未指定 CUDA/debug 选项的完整 Release 构建、相关 CTest 与四项 CPU ASan/UBSan 通过。v139 因最后的查询精简重新构建 OFF/ON/无 CUDA 并核对实际导入路径。
- 独立最终审查发现 greedy 每轮完整结果仅用于 QOR 日志；现有查询增加 summary_only，保留 prepareReport/物化，跳过完整 timing vector、paths 序列化及 binding 转换。默认完整查询不变。Python 42 项、定向类型零错误及 lint 通过，Spec/Standards 无剩余高置信代码问题；native 测试新增摘要/full 同代等价和实际分配对照。
- v136 全 parent 回归为 1702 passed、3 failed、6 skipped、13 xfailed、1 deselected。空 PDK 测试受到本轮显式 PDK 环境变量影响；两项完整 flow 测试因执行副本漏同步已有 GCD fixture 符号链接而未取得 RTL。v139 隔离环境并恢复 tracked 链接后复跑，原日志保留。
- v136 zipdiv greedy 的 CPU/full、CPU/incremental、CUDA/full 均完成实际正 gain 提交并通过独立 fresh 完整比较。CUDA/incremental 已提交并产出同代产物，但额外完整 routing 因测试脚本漏调用原有配置生成入口而失败；v139 补齐测试准备后复跑。此前所有四模式的路由 IDB 导入证据仍保留，不能用它代替完整 routing 执行。
- v137 原始 heaptrack 采样成功，但首次分析没有 binding 符号，全部零计数无效。v138 用相同 Release 对象重链接保留符号，确认 .text SHA-256 与实际加载 binding 完全一致，再按真实动态装载地址解析。xtea Q 两批 CPU/full 有 211726 次分配的栈包含原生 propagate；CPU/incremental 批次没有此路径、全图 GraphBuilder、完整 export、Database/TimingLibrary 拷贝或诊断栈，且明确观察到真实 apply/targeted 栈。计数是分配事件而非函数调用次数，不涵盖无分配的内联拷贝；与局部事务分配失败/原位 owner 测试及独立审查共同使用。
- v136 Nsight 原始 trace 成功保存；容器缺少 importer，v138 使用已有宿主 importer 在同一内存 slice 中转换成功。实际 initializeRcDrivers 为 6 blocks×256 threads，传播为 1–20 blocks×256 threads；不以 launch 数代替 SM 利用率。完整 trace 包含初始模型分配、提交和查询，下一份带阶段标记的记录将区分连续无查询批次与首次/重复查询。性能计数器权限限制仍保留。
- GitHub API 核实该仓库无已注册 runner。已修改现有 CPU 工作流，并提供服务器手动 GPU correctness 入口；没有注册 runner、配置 SSH 凭据或声称托管 GPU CI 已接通。待用户对该 CI 边界的选择；托管工作流执行均为 not_run。

### 2026-10-01：最终消费路径及未关闭项（v139–v145）

- 最后的 summary_only 查询变更在 OFF/ON/默认无 CUDA 三份完整 Release 构建中验证，三份实际导入路径与只读 flags 正确；各 4 项物理回归和 ASan/UBSan 查询失败重试通过。ON 真实分配对照观察到摘要 3 次、完整 5 或 9 次，不以这些数值建立固定门禁。139 项本地关联 parent 测试通过，独立 Spec/Standards 再次 approve。
- v139 zipdiv CUDA/incremental 的生产入口提交 generation 1、1 个 buffer，无静默 fallback；随后按无正 gain 正常停止。manifest 产物被 routing 实际读入并完成布线、数据/几何产物及 EngineFlow 检查。独立 fresh native CPU/full 的完整比较与 canary 通过。v145 默认 OFF 同一流程成功，公开 timing/QOR/paths 与 ON 完全相同，OFF 未生成诊断或启动 oracle；OFF 再验证同代产物可被 routing IDB 加载。
- v140 首次分段剖析因既有 PyTorch 是 CPU 版、不提供 NVTX 而失败。v141 使用已安装 Nsight 头文件编译测试专用两函数标记库，没有加入生产代码或依赖。Nsight trace 及 v144 关联分析成功：连续两批不查询，apply-1/2 分别 D2H 40876/40908 字节；最终查询 D2H 6981304 字节，重复查询没有 CUDA API 分配/同步、传输或 kernel。最终公开结果与相同输入逐批查询的结果完全相同。
- 同份 trace 的初始化有 8525 次 cudaMalloc、5674 次 H2D；两批分别有 45/21 次 cudaMalloc、30/27 次 H2D。第一批 2515000 字节 D2D 与后续第二批 40512 字节 D2D 分开保留，包含首次容量增长和工作缓冲成本，不当作零复制。RC 初始化实际为 6×256 launch，传播为多线程；硬件计数器权限仍阻塞 SM 利用率证据。该记录只用于行为核验，不是正式性能采样。
- 两个空输入负例均实际退出 1，明确拒绝无批次/无编辑 trace，没有生成批次成功结果。未将 baseline 成功算作增量验收。
- v139 的 1701 项非集成 parent 测试通过；集成复跑先被 v136 失败留下的已有工作区挡住。v142 将两个生成目录移到证据目录保留，再执行完整流程：普通 RTL→GDS 通过；RCX 已执行，但后续 signoff 拒绝不存在的 ics55_LLSC_H7CR_ss_cworst_1p08_m40_nldm.lib。未改约束、corner 或用别的 Liberty 代替。该 PDK 文件当前不可用，不能宣称该集成通过。
- v133 额外全仓 native 运行的 ircx_interface_test SIGSEGV 没有改成 skip 或成功；它使用未加载 IDB 的独立占位输入。v144 请求回溯时容器没有 gdb，debugger.exit=127，外层脚本 0 不表示测试通过。没有为此升级环境或扩展修改 iRCX。
- CI 静态解析完成，未运行托管工作流。仓库没有已注册 GPU runner；按不注册 runner 的边界保留服务器手动 GPU correctness 命令，未擅自配置 SSH 凭据。此接入选择尚未获得用户答复，Stage 13 总体保持未关闭；Stage 14 未启动。

### 2026-10-08：按用户授权提交

提交前核对当前源码与上一轮已验证版本一致；暂存检查发现两个新增 C++ 文件的行尾空白/文件末空行，修正后以忽略空白差异核对确认无逻辑变化，两仓暂存差异检查通过。本轮未重跑构建和服务器回归。用户已有 CLAUDE.md、独立报告及 overview 未纳入；GPU CI、类型检查、RCX 回归和 Stage 12 正式性能门保持原状态，不因提交计为完成。
