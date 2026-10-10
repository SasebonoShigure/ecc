# Stage 14 实施记录

状态：功能、路径剖析及用户调整后的 1/3 参考成本验收完成。更新：2026-10-10。未 push。

以下按实施顺序保留失败与修复记录；当前结论见“最终验收与保留限制”。

## 基线与证据

- ECC `d13c513`、ecc-tools `5429fc3d9`；保留已有 CLAUDE、总计划差异及用户报告。
- 本地证据：`/home/shigure/code/stage14-20261008-120752`；基线身份与差异存于 `baseline.json` 和两仓库 baseline patch。
- 三设计原 post-CTS、ICS55 文件及 Q/D 各两批物理 trace 已重新核验并冻结，六个用例共核验 36 个文件，身份见 inputs-frozen.json；保留既有分段剖析作为历史基线，不把它当成本轮正式采样。性能口径包含每轮必要候选数据与末轮全部产物，5/30 尚未运行。
- 已运行的 parent 基线：`test_physical_greedy.py`、`test_sta_session.py`，42 passed；命令和原始日志见 `parent-baseline.log`。
- 服务器曾返回 SSH Connection timed out，随后恢复连接。当前验证目录：`/home/qianhan/code/stage14-20261008-120752`。
- 首组构建使用 tmux `stage14-csr-full-v1`、GPU 1；运行中的共同限制已核对为 MemoryMax=512000000000、MemorySwapMax=0。原始源码归档、配置、构建及测试日志分别保留，未覆盖 Stage 13 证据。

## 第一组：直接 CSR full 重建

- 增加 CUDA 内部 DualCsrState packing，保留 stable arc slot/tombstone，完整重建 active Base 入出邻接；arc/model/seed/RC 打包共用已有实现，不经 native 导出或 dense-input validator。
- `stageFullCsr` 仅供受控会话和测试 reader 使用，检查 session、下一 generation 和高水位；复用完整上传、full levelization/propagation、工作图和实际恢复。
- 修正 RC 模型查找对名称排序的依赖。Dual-CSR 模型按批次追加，不能继续使用仅适用于有序数组的查找。
- 新测试覆盖 Aux/tombstone、独立 CPU 对照、放弃、malformed、stale generation、重复提交/容量复用；另补充模型扩容后的实际数值失败、ON 分配异常扫描，以及恢复设备图上的后续 targeted 计算。
- RC 直接入口测试覆盖 Arnoldi/DMP/fallback、propagated clock、CTQ/deferred seed、inactive RC owner 及追加 load cell；保留现有完整结果比较和容差。
- 独立局部代码复审 approve；新增异常恢复、RC 和分配失败用例已运行。v2 的 Release/OFF、Release/ON 严格构建及四项 CUDA CTest 分别全部通过（OFF 6.37 s、ON 12.75 s，driver exit 0）。原始日志为运行目录的 build-{OFF,ON}-v2.log、ctest-csr-full-{OFF,ON}-v2.log；本地保留副本。此结论仅覆盖直接 full-pack 入口和测试，不代表生产迁移完成。

## 第二组：直接 CSR 编辑准备（历史实施记录）

- 新增 buildDirect：从 committed CSR、稳定 resolver、不可变 Liberty 和准备后的 raw RC 生成局部 descriptor；复用现有 Base/Aux 构造、pin-load 编码与 RC 准备函数，未调用 native 图编辑。
- native capture audit 改为可缺省；直接路径不生成虚假审计。factory 不再把已由 native builder 检查过的捕获审计作为重复提交授权，仍检查 owner、generation、policy、baseline 与局部 descriptor。
- 新测试对 buffer、Base/Aux、未移动 fanout 的完整 descriptor 做独立 native 对照，并实际 apply/undo graph/index/resolver；生产批次尚未切换。
- v3 因 factory 仍接收非 optional 的旧 audit 字段编译失败；迁移后，v4 暴露新测试的换行字面量错误。修复后的 v5 严格 OFF/ON 构建通过，OFF 直接编辑测试通过、两个诊断测试禁用；ON 三项通过。
- 独立审查发现并修复三项边界：同端点 non-graph 弧不能代替唯一 graph arc，改用现有模型 ordinal；直接构造复用当前 operation authority/session，并限定 canonical Database 的模型 owner；完整名称冲突按 kind/full_name 检查，不解析最后一个冒号。对应错误模型、非图弧前缀和含冒号名称的运行用例已加入。
- 复用既有 RC transaction 测试执行两批直接 CSR descriptor 的 apply、commit 和真实撤销，对照 native 导出的 raw RC、各 lane、未移动 sink 和 deferred Q seed；覆盖 RC 数值溢出后状态不变。v6 因新测试漏包含声明头编译失败，已修复。
- v7 严格 Release OFF/ON 构建和定向回归通过：OFF 三项通过、两项诊断禁用（not_run），ON 五项通过，driver exit 0。此版 GPU 仍消费 native patch，因此只证明直接 host descriptor/事务组件。该组独立局部复审 approve，未替代生产验收。
- 新增的 CSR→CUDA 局部转换只搬运实际 descriptor，RC 旧/新终端从受影响树及 seed 取得，模型借用会话缓存；其入口同样校验 canonical owner。测试已改为 direct patch→mixed 和 applied direct graph→full，v8 严格 OFF/ON 构建和上述定向回归全部通过，driver exit 0；它证明直接 descriptor 驱动的 CUDA full/mixed 组件，不代表生产迁移完成。
- 输入冻结工具首次运行遇到宿主 Python 无 hashlib.file_digest，改为标准库分块哈希后完成；没有升级依赖。一次构建启动因空闲 slice 限制已卸载而被预检阻止，重新 link/start 并核对硬限制后才启动。原始构建失败、成功日志和源 SHA 分开保留。

## 第三组：生产批次与按需 native 视图（历史实施记录）

- CPU/incremental 已直接生成、应用 CSR descriptor，删除 physical 批次的 native targeted 编辑和再捕获；native Database 在查询前保持旧视图。查询时复用现有 IDB wrapper、GraphBuilder.buildStructure 和 CSR result scatter，不执行 CPU timing 传播。
- raw map 与原 FullDerivedUndo 共同保存实际旧值；仅在完整准备当前结果后发布。新提交失效 timing/report generation，失败保留原 native raw/derived 状态并允许重试。
- v9 严格 OFF/ON 构建通过；OFF 五项通过、两项诊断禁用，ON 七项通过，包含 CPU/CUDA physical 回归。此版 CUDA 生产批次尚沿用旧路径。
- 独立审查要求封闭 physical 会话绕过 generation 的旧 snapshot/reference/scatter 测试入口，并补冷查询失败恢复。已在 context 层拒绝旧入口；测试在 raw 与 derived 重建中分别触发实际分配失败，比较图、独立 native timing oracle、RC、pin/net、QOR/paths 和功耗值，随后重试及继续编辑。
- v10 因测试缺少 CsrSnapshotObservation 的完整类型头文件编译失败；补齐后的 v11 严格 OFF/ON 构建和同组回归通过（OFF 五项通过、两项禁用；ON 七项通过，exit 0）。
- CUDA 生产迁移保留设备 session 的 close/poison 生命周期，新增必要 host CSR/resolver/index 编辑状态；不再绑定 native targeted owner。直接 host 局部 undo 与设备事务共同发布；CUDA/full 调用完整 CSR 重建，incremental 使用 direct patch。查询复用同一当前 native 视图。v12 独立局部审查通过，严格 Release OFF/ON 构建通过：OFF 五项通过、两项诊断禁用，ON 七项通过。顺序构建并隔离两份 binding 后进入真实设计验证。

## 第四组：最小候选结果与末轮报告（历史实施记录）

- 增加 CPU/CUDA 紧凑候选读取，只取 setup slack、data/clock slew 和有限 MAX-path 有效性；CUDA 不回传完整 PathState，设备容量和同 generation 缓存复用。ON 覆盖首次设备分配失败后重试；设备错误仍 poison。
- native 与 CSR 共用原 gain 计算和稳定身份决胜，收集阶段分别读取各自权威状态。CSR 借用当前图、IDB 坐标、RC 与不可变模型，不先准备 native 报告。审查发现的负载求和顺序差异已按 native full_name 顺序修正。
- 新增真实三批编辑形成双 sink 的四模式用例，要求非空正 gain 并比较完整 edit、gain、坐标；另验证同 gain 时反转 sink 输入顺序不改变 stable ID 选择。首次读取前检查 native 图未被 CSR 编辑或候选查询物化。
- Python 默认循环删除起点及每批 QOR 查询和 before/after 日志，greedy schema 升为 2；结束后沿用当前 generation 产物发布。相关 parent 用例 51 passed，ruff/format 通过，见 parent-final-report-v1.log。
- native 物理 CPU/full 的 baseline 和批次仅执行必要传播，包括 RAT/slack；显式查询统一用 analyzePropagatedTiming。普通一次性 full 入口保留原行为。
- 独立审查发现 analyzer 的 report diversion 会暂改路径，CPU/full 首次报告失败不能靠 CSR 重散射恢复。现按实际修改的 path entry 保存局部旧值，并在成功或失败后恢复，报告不改变下一轮输入；没有整库复制或重新传播。新增首次报告在 arrival 已改后触发实际分配失败的测试，比较完整权威状态、原报告、独立成功结果及重试缓存。代码局部复审 approve，运行结果仍待核验。

## 本轮构建与真实设计证据

- v13 严格构建通过，OFF 七项通过、两项禁用；ON 两项 allocation 扫描失败。v14 新 collector 的 IDB coordinate const 类型错误、v15 split CUDA Toolkit 下测试头文件路径错误均已修复。
- v16 因 GPU 1 已被其他任务占用而在启动预检退出，未执行构建。v16b 改用空闲 GPU 2：OFF 七项通过、两项禁用，ON 两项扫描仍失败；驱动退出文件因 shell 状态捕获错误写为 0，CTest 日志明确失败，不能按该退出文件判通过。后续使用独立 driver 脚本保存实际退出码。
- ON 失败定位为 ordinal 34 未抛异常，owner 未 poison、generation 未变；full packing 使用的 stable_sort 可在 nothrow 临时分配失败后继续。测试现确认注入真实发生；若正常返回，必须完整比较 staged 结果、close 撤销，再运行实际后续提交。该修订不把未触发注入视为通过。
- v17、v18 因新增候选测试误用文件私有 helper / 错误函数名编译失败；已改用导出的 stable key 和既有 defaultTokenMaterialization。v19 OFF 严格构建通过，但正 gain 物理测试为空候选；驱动在 OFF 测试失败后退出，ON 未执行。v20 严格 OFF/ON 构建通过，除相同候选失败外，ON 新增 RC 对照暴露数值差异。v21 因 GPU 已占用在预检退出；v22 改用空闲 GPU 7，复现上述失败。
- 首次 physical-trace-v12 因 Python 导入了旧安装 binding 而全部在 STA 前失败，记录为未执行。修正隔离包路径后，physical-trace-v12b 的 48 个组合（三设计 × Q/D × OFF/ON × 四模式）均退出 0；十二个独立 fresh native CPU/full 进程也均退出 0。独立比较已退出 0：96 项公开结果比较、48 项完整诊断比较通过，level/winner/CRPR/timing 四类 canary 均检出；原始结果见 compare-public-v12b.log、compare-diagnostic-v12b.log。这组使用 v12 binding，不能证明后续候选/报告改造。
- v22 的 RC 差异为 data_slews：CUDA 0.25817815851098996、CPU reference 0.24644278766958133。根因是 CPU reference 对按批次追加的模型数组执行 lower_bound，漏掉新增 load cell；现使用借用名称和模型地址的索引，不复制模型。v23 严格 OFF/ON 构建通过，RC 对照及分配失败恢复回归通过；ON 7 项通过、2 项物理候选失败，OFF 5 项通过、2 项诊断禁用、2 项物理候选失败。候选失败仍在定位，未放宽 gain 门槛。
- 空候选定位为物理测试夹具缺失 LEF port，IDB 因而跳过 pin 坐标更新，新增 buffer 间 RC 为零；补齐真实 port 几何后，四模式三批正 gain 候选、完整评分/位置比较及不物化检查通过。v24 诊断代码缺少模型定义头、v26 坐标 getter 的 const 用法编译失败均已修复；v25 保存了定位所用实际 RC/driver 输出，临时日志已删除。v27 OFF 7 项通过、2 项禁用，ON 8 项通过、首次报告失败注入 1 项未触发。
- 首次报告测试起初只改 input_output_delay_map，reporter 实际优先读取 graph_delay_map，因而没有更优 diversion；v28 仍未触发。同步修改两份真实消费缓存后，v29 ON 物理回归通过，实际覆盖 arrival 改写后的分配失败、权威 timing/原报告恢复、与独立成功会话相等的重试及缓存复用。模型借用、物理候选与报告测试均获得独立局部 approve；不替代完整生产验收。
- v30 严格 Release OFF/ON 回归通过：OFF 7 项通过、2 项诊断禁用；ON 10 项通过，包含 native RC 差分、候选与首次报告恢复。binding 分别核对实际路径、CUDA=true、debug=false/true 后隔离保存至 binding-{OFF,ON}-v30；新版三设计矩阵已启动，完整比较待核验。
- 服务器 /home 剩余空间降至约 1.3 GB 后，仅暂挂本任务容器，保留进程。旧版 physical-trace-v12b 的 3,274,767,451 字节证据已取回本地 archived-physical-trace-v12b，经 rsync 逐文件 checksum 无差异，并对本地压缩包完成内容比较、gzip 校验；162 MB 压缩包回传后 SHA/gzip 再次核验。服务器未压缩副本已由该无损归档替代，目录余量恢复至约 3.9 GB，原容器 5d3ab3570413 已恢复且没有重采。原始数据、归档及 archive-record-v12b.json 均保留在本地运行目录，服务器归档为同级 physical-trace-v12b.tar.gz。直接在低余量服务器压缩的尝试被自动审批拒绝且未执行；改为本地完成、校验后再释放服务器副本。
- 本轮服务器任务共用 MemoryMax=512000000000、MemorySwapMax=0；构建使用空闲非 0 GPU 和 tmux。所有源码 SHA、构建、失败、fresh 命令及原始输出保留在同一独立运行目录，各版本不覆盖。

## 末轮消费性能入口及补充验收（2026-10-09）

- v30 矩阵中 ON/zipdiv/Q/CPU-full 的 600 秒超时覆盖了磁盘紧张期间的容器暂停；保留原失败，单独重试退出 0。最终 48 个目标组合与 12 个 fresh 进程退出 0，96 项公开结果比较和 48 项诊断比较通过；level、winner、CRPR、timing canary 均检出。最终 driver-resume-v31.exit 为 0，日志及 effective-status.json 保留。这不包含真实 closed-loop 或完整产物验收。
- 新性能入口复用 physical_sta_probe 与现有配对统计，raw/aggregate 为 physical-sta-sample(s)/2.0.0。固定 trace 每批读取实际 PDK buffer 池的候选输入，最后才完整查询并发布产物；连续总计时包含最终工作，加载、初始化和清理另记。默认 5/30、四模式轮转、fresh process，ON 在输入加载前拒绝；Stage 15 验收始终为 not_run。
- v32 首次运行完成了实际查询、产物及清理，但复制完整公开结果中的合法无限 sentinel 导致严格 JSON 序列化失败；性能样本已改为只保留结果 generation 和真实产物 manifest，不重复搬运完整功能对象。v33 四模式各一份短 smoke 退出 0；不把它当作新协议或 5/30 验收。
- 独立审查要求输入与 binding 身份绑定、统计/协议篡改 canary 和 timeout 状态；已修复并局部 approve。checkpoint 身份在加载前记录；trace 同一份 bytes 用于解析和摘要；结束复核最初身份。性能子进程 PYTHONPATH 使用隔离包父目录，并由真实 Python 子进程测试实际导入路径。v37 隔离目录遗漏已有 json_schema_contract helper，在采样前失败，补齐后以新 v38 目录重试，旧日志保留。
- parent-performance-v36.log 的相关 73 项通过；parent-ecc-v36.log 为 405 passed；完整非 integration/pdk/slow 回归 parent-regression-v36.log 为 1725 passed、8 skipped、4 deselected、13 xfailed。重叠合法化负例的原生日志保留，不将 skip/xfail 算通过。改动性能文件 lint/type 通过。
- 全仓 ty check 实际失败，2174 diagnostics，见 parent-type-all-v36.log。两个修改过的生产 Python 文件在提交基线与当前代码均为 18 条相同诊断，见 parent-type-{baseline,current}-v37.log；未声称全仓类型通过，也未扩展修复无关模块。
- 2026-10-08 连接曾超时，2026-10-09 恢复；未据超时重启旧任务。新验收 tmux 为 stage14-validation-v38（GPU 7）与 stage14-no-cuda-v38（CPU），共同 MemoryMax=512000000000、MemorySwapMax=0。前者执行新协议 smoke、真实 ON 拒绝及 CUDA 检查；后者使用独立源码和构建目录，省略 CUDA/debug 选项核验默认 OFF。结果待核验。

## 运行复核与语义路径迁移（2026-10-09）

- v38 新协议四模式短 smoke 通过，实际 ON binding 在采样和输入加载前被拒绝，未产生样本；不是 5/30 成本验收。默认无 CUDA 独立构建 driver-no-cuda-v38.exit=0，相关 CTest 七项通过、两项诊断禁用；隔离 binding 实际报告 CUDA=false、debug=false。
- v40 CUDA memcheck/racecheck/synccheck 在 OFF/ON 均通过，initcheck 两次退出 99。紧凑候选记录的三个 double 与 bool 组成的结构体尾部存在未初始化填充，D2H 每 32 字节触发检查。已将标记改为定宽 uint64_t 并约束无填充布局，记录仍为 32 字节，不增加清零 kernel 或传输。独立局部审查 approve；v41 严格 OFF/ON 构建、受影响回归及八项 CUDA sanitizer 均退出 0。原失败完整保留在 validation-v40，修复结果在 validation-v41。
- v41 构建发现早期运行目录中的 CCCL 头文件路径已不存在，改为复制服务器现有 CUDA 12.8 的同版头文件到本轮证据目录；保存 toolkit-version.json、文件身份和新的 cache 文件，不升级 Toolkit 或依赖。
- v40 CPU ASan/UBSan 在进入三个测试前均因既有 Logger.cpp 的 _log_instance 同时链接到 libidb/libtcl 报 ODR violation。相关生产源码和链接文件相对基线未改。保留原配置失败；v43 仅对该符号增加运行时 ODR suppression，其余地址、UB、泄漏检查保持开启，三个测试通过。此为有明确排除项的补充证据，不将原配置记为通过。
- v39 闭环驱动虽然 24 个进程退出 0，但复核 journal 和执行记录发现 probe 将模式写入错误的嵌套参数键，实际均为 CPU/full；该组不能证明四模式。已改用生产参数键，并增加命令行到实际 request parser 的四模式测试。首次测试夹具遗漏 flow/db 路径导致四项失败，补齐后相关 38 项通过，lint/format 通过；type 检查需加入脚本目录作为 import 搜索路径，原缺失路径诊断保留。
- v42 使用修正 probe 和隔离 v41 binding，24 个闭环进程退出 0；驱动逐一核对 baseline request 和实际 batch mode/fallback，不再按目录名推断。xtea、usb 均无正 gain，只有基线产物；zipdiv 四模式均真实提交一个 buffer 后停止，两个 incremental 模式实际执行 incremental、无 fallback。最终产物的独立比较仍待完成，不把基线退出当作增量通过。
- 最终独立 Standards 审查 approve；Spec 审查发现仍在执行的 semantic subject replayer 沿用 native 编辑→捕获→CSR，要求迁移，未批准整阶段完成。已完成迁移设计复核：复用 buildDirect、CPU coordinator 和现有 CUDA patch/full-pack；source IDB 保持不变，native 视图仅在显式消费或最终输出时一次性补齐，独立 fresh native oracle 保持原路径。
- 迁移第一步提取现有稳定键结果映射，并加入原子 semantic native view；整个未物化 trace 后缀在同一 raw/derived undo 中构图及 scatter，失败不留下部分视图。新增两批不查询、最终 scatter 失败整段撤销、重试、重复查询、查询后再提交的行为测试。v44 严格构建因新测试缺少 transaction target 的头文件依赖失败，已补齐，以 v45 独立日志验证；三个实际 replayer 和对应 schema 尚未接入。

## 语义入口直接编辑与闭环产物核验（续）

- CPU semantic subject 已迁移为 buildDirect → CPU coordinator；删除 native targeted 编辑和再捕获。默认末轮物化，显式 consume_results 保留 Stage 12 原逐批消费口径。未消费的物化/报告字段为 not_run/null，capture audit 及其专用证明删除；受影响 receipt、process、verdict 与 smoke schema 已升级。
- v45 的测试 creation token 使用错误批次序号，v47 缺少完整 authority 声明头，均已修复。v46 直接编辑/physical 定向测试 OFF/ON 各三项通过；v49 严格 OFF/ON 构建通过，OFF 五项通过、两项诊断禁用，ON 九项通过；Stage 5/6 独立 fresh controller、OFF 短 smoke 及 ON 性能拒绝已运行。修改 Python 的类型诊断在基线与当前均为 85 条，归一化内容一致，不宣称全仓类型通过。
- 提取 CUDA 功能 host graph/index/resolver 的局部 Patch owner，physical 路径复用该 owner。v50 因 GPU 已占用在预检退出；v50b 使用空闲 GPU 6，严格 OFF/ON 构建与三项定向回归分别通过，exit 0。
- CUDA full/targeted semantic subject 已接入同一直接 CSR 准备与局部 Patch；CUDA/full 仍完整重建计算 CSR。删除旧 CudaFullExecution native 构图/export 包装；默认末轮消费，ON 才构造诊断映射和完整设备观察。新 schema 区分 active arc 与 slot 高水位、未执行的逐轮报告；协议测试八项及 20 个子用例通过，修改 Python lint 通过。
- v52 遗漏一次性 CUDA baseline 的旧调用签名，v53 缺少直接 CSR 所属 target 的头文件依赖，均编译失败并保留日志；v54 严格 OFF/ON 构建通过，各十项实际定向测试通过，ON 另三项因遗漏构建硬件测试程序而 Not Run，driver exit 8。
- Spec 发现设备故障未立即 poison 外层 session，已补异常收束，并新增 ON-only 真实 context 故障的 full/targeted/mixed 三个独立进程用例；在任何查询前检查外层 poison、host/device generation 和未提交历史，保留真实撤销与 cleanup 失败语义。
- CUDA subject baseline 复用现有 private lifecycle 的窄输出参数，将唯一一次导出 move 给 loader 局部对象；仅在 baseline 成功后借用，不增加持久快照。普通生产入口传 nullptr，独立 fresh native oracle 保留自身导出。Spec 与 Standards 均 approve 本组静态复审。
- v55 因新参数缺少前向声明编译失败，修复后的 v56 严格 Release OFF/ON 构建通过、定向回归各 11 项通过；单独硬件日志中的八项测试全部通过，包含上述三个 semantic fault 用例，driver exit 0。旧失败不删除。
- v57 新版 binding 顺序构建/隔离完成，native 回归 OFF 28 项通过、2 项诊断禁用，ON 35 项通过。物理路径 OFF/ON 的 memcheck/initcheck/racecheck/synccheck 共八项及 semantic full 的 memcheck/initcheck 共四项通过；另八项因驱动误将完整 artifact 传给要求裸 replay 的入口而在计算前退出 1，原 driver 失败保留。v62 仅提取既有 replay 字段重跑这八项，全部通过；full/mixed 的完整 OFF/ON 输出相等，输入转换与原始输出保存在 validation-v62。
- 优化前 native 源码另从冻结提交 5429fc3d9 导出归档，并在独立 v58 目录重建；成本协议沿用冻结的三设计 Q/D 六组输入，四模式、优化前后交错、8 个固定逻辑 CPU、预热 5 次及采样 30 次，消费者需求包含每轮候选数据与末轮全部产物。协议及归档身份见 cost-protocol-v58.json，采样尚未执行。
- closed-loop-fresh-v51 的 24 个独立 ON native/full 进程均退出 0。最终 manifest、generation 和文件身份经生产 reader 验证；与 v42 目标产物比较，DEF/netlist、QOR、paths 及文本报告完全一致，SDF 仅 DATE 不同，功耗二进制逐条身份一致、最大绝对数值差 1.0587911840678754e-22，既有 1e-10 容差未放宽，数值 canary 检出。首次比较脚本日期正则转义错误，修复后 v51b 24 项通过，原失败保留。
- 上述闭环证据绑定 v41 native binding；xtea/usb 共 16 个组合为无正 gain 的基线退出，zipdiv 八个组合真实提交一批。该结果不替代新版 semantic runtime 回归或固定 trace 多批次验收。

## 最终版本补充验收（2026-10-09）

- v59 默认无 CUDA 独立构建与九项回归通过，两项 ON 诊断禁用；隔离 binding 报告 CUDA=false、debug=false。CPU ASan/UBSan 三项通过，仍仅排除既有 Logger _log_instance ODR 冲突，原配置失败不改写。
- 精确基线 5429fc3d9 的独立 Release/OFF/CUDA 构建 v58 完成。v63 优化前后四模式各一份短 smoke 成功；这些不是 5/30 验收。审查发现其 complete_report=not_run 会误述旧库隐式报告，现改为 explicit_complete_report_request=not_run，旧库隐式工作仍计入对应阶段；生成器、validator 与测试同步，26 项测试及改动文件 lint/type 通过。保留 v63 原始样本，不将其当作修正后的最终证据。
- 成本驱动 v66 追加实际 journal 的输入、完整 RC、trace 和构建一致性检查。冻结清单的 ss/125 是显式加载 Liberty 的角标；既有 direct 入口 journal 记录 __direct__/pre_route/__unspecified_temperature__，两份事实分别保存，实际 Liberty 文件与 RC 仍须精确匹配冻结清单，不改生产分析参数。
- 保留 v61 剖析构建因容器缺少 /bin/true 退出 127、v64 因 CMake 缓存类型预检退出 1 的记录；v65 修复后成功，保留符号的 binding 与 v57 Release/OFF 的 .text 摘要完全相同。调用剖析增加 QOR/path serializer 正控制，malloc 统计排除 marker 内部调用，仅表示 libc malloc 请求量。
- 修正成本短 smoke v66 的优化前后四模式八个进程与协议校验均通过；实际 journal 的输入/RC/analysis/trace 四类篡改 canary 均检出，独立局部复审 approve。最新 binding v57 的三设计物理回归 v60 已完成：48 个目标与 12 个 fresh 进程成功，96 项公开比较、48 项诊断比较通过；v68 闭环及独立 fresh 最终产物比较 24 项通过，其中 xtea/usb 的 16 项为无正 gain 基线退出，zipdiv 的八项实际提交一批。最大功耗数值差 1.0587911840678754e-22，沿用 1e-10 容差。正式 5/30 尚未启动。

- 分配剖析 v67 保留运行；地址补录 v69 因系统 GDB 没有 Breakpoint.locations 属性退出 1，未生成有效验收证据。v70 使用该 GDB 支持的 maintenance/info address 命令重试，单独记录函数入口与地址，不把 v70 未采集的 malloc 计数当成零分配。

- v70 四模式函数入口剖析已正常退出，所有目标断点均解析且地址记录有效。三个 CSR 模式的两批 apply 均直接进入 buildDirect；观测到的 native 编辑、executeFullTiming、native export 和报告入口在这些批次均未命中，最终查询才进入 native view 构造及 analyzePropagatedTiming。CPU/full 为 native 编辑/传播正控制，四模式最终查询均命中 QOR/path serializer。原始 calls.json 保存完整符号与分相计数；此为调用证据，不替代 malloc、传输及性能验收。

- v67 逐 malloc 断点剖析在首个 CPU/full 进程达到预设 3600 秒上限，子进程退出 124、driver 退出 1；没有据此作分配结论。保留原始失败，复用 Stage 13 已使用的 heaptrack 采集四模式实际分配栈，结果待核验。
- v70 四份 Nsight 原始记录和 SQLite 导出均成功。zipdiv/Q 两批中，CUDA 候选读取的 D2H 从每次约 6.98 MB 降到 161,984/162,048 字节；最终查询仍回传约 6.98 MB，最终文件发布没有再次 D2H。apply 仍回传约 41 KB 的必要状态/levels；RC 和传播均观察到每 block 256 线程，不能据 launch 形状推断实际 SM 利用率。
- 同组记录中 CUDA/full 第二批 H2D 从 5,805,872 降到 2,779,616 字节，cudaMalloc 从 1,148 次降到 30 次；首批仍有 8,517 次分配。CUDA/incremental 两批的必要传输和设备分配未下降，候选容量首次建立及增长各有一次分配。上述为实际剖析分解，保留剩余成本，不宣称零分配或正式加速。硬件性能计数器仍因既有权限限制未执行。

- 最终独立代码审查 approve；验收复核要求补跑最新版本的真实末轮发布失败重试。v73 直接复用 Stage 13 的 v133 测试：zipdiv CUDA/incremental 在 OFF/ON 均真实提交一个 buffer，再以 manifest 目录冲突触发 rename 失败。恢复重试后 journal、完成记录和 greedy 日志字节不变，generation 仍为 1，routing handoff 与引擎结果检查通过；实际加载 v57 binding，CUDA/debug 状态一致。没有新增生产故障开关。

- v72 heaptrack 四模式与已有 ELF 栈分析均退出 0。zipdiv/Q 两批的 apply 分配事件分别为 CPU/full 13,508,159、CPU/incremental 710,177、CUDA/full 390,277、CUDA/incremental 208,486；这些为包含子调用的分配请求数，不是峰值内存或函数调用次数。三个 CSR 模式的可解析批次栈未出现 native 构图、传播、targeted prepare、再导出或报告；CPU/full 的 native 传播分配提供正控制。Database/Liberty copy 栈未观察到分配。分析不重建内联帧或跨线程父调用链，结合 v70 调用记录和代码审查解释，不能把缺失栈当成独立的绝对证明。 独立验收复核确认这组联合证据满足代表性路径剖析要求；不扩展为所有输入或内联行为的绝对证明。
- v68 派生比较文件的旧 binding-v41 标题已在 closed-loop-artifact-comparison-v74.json 更正为实际 OFF/ON v57，并记录原文件摘要；比较内容及原始文件保留。1326 个用户保留文件的摘要仍与基线一致。
- 冻结的六组 Q/D、四模式、优化前后 5/30 成本采样已在 GPU 5 的 tmux stage14-cost-engineering-v66 启动。运行目录为 cost-engineering-v66，日志为 driver-cost-engineering-v66.log；启动前确认旧剖析进程已退出、GPU 空闲，所有任务共用 512 GB 硬上限及 swap=0。结果待核验，尚不作成本结论。

- 最终范围核对发现，v60 固定 Q/D 两批只保存逐批公开/诊断结果及 DEF/netlist；v68 closed-loop 的产物比较不能替代固定多批次完整产物。现仅在既有 trace probe 循环结束增加一次发布，生产代码和冻结 parent-v66 不变。v75 补验准备在成本采样结束后执行 OFF/ON 三设计 Q/D 四模式，复用 v60 同为 nworst=1 的最终 prefix fresh 产物；不将 nworst=20 的性能样本混入比较。相关 26 项 parent 测试、修改入口 lint/format/type 及独立静态复核通过；真实补验尚未执行。

- 成本采样首组 xtea/Q 已完成优化前后各四模式 5/30，共 280 个 fresh 进程样本。本地协议复验及相同输入/需求的 30 对样本统计重算通过。配对 before/after 加速比中位数及 95% CI：CPU/full 1.035 [0.990, 1.077]，CPU/incremental 1.039 [1.022, 1.067]，CUDA/full 1.153 [1.128, 1.178]，CUDA/incremental 1.007 [0.990, 1.026]。CPU/full 与 CUDA/incremental 在该组未取得显著收益；优化后 CUDA/full 对 native CPU/full 的区间为 [0.527, 0.567]，仍更慢。原始聚合样本和本地核验位于 cost-engineering-v66/xtea/q；其余五组尚未完成，不据首组作阶段结论。

- 2026-10-09 用户将本轮采样改为 1 次预热、3 次采样。仅停止本任务 v66 容器，driver 137 记为协议变更导致的主动中止；xtea/Q 完整 5/30、xtea/D 已完成数据和未完成进程日志全部保留。v76 协议保留相同六组输入、四模式、线程、消费需求和统计方法，按原始序号复用两组 xtea 的首个预热及前三个样本，其他四组新采 1/3。复用组实际已有五轮预热，单独记录，不伪称只运行一轮；原 5/30 输出保留作补充。新输出沿用 short_smoke 分类，仅作为用户调整后的参考成本证据，不替代 Stage 15 正式性能门。

## 用户调整后的参考成本结果（已核验）

v76 退出 0，六组冻结输入的优化前后四模式全部完成。v77 从原始聚合样本重算统计并核对完整用例、序号、输入、binding、线程配置及实际模式；192 条选定记录中，64 条复用 xtea 原序号，128 条为 usb/zipdiv 新采。每模式保留 1 个预热、3 个正式样本；xtea 实际经历过 5 轮预热，原始额外数据与这项差异均保留。

下表为优化前/优化后完整循环耗时的配对比值中位数，大于 1 表示本次改造后更快。计时包含每轮候选读取、两批提交、最终完整查询与所有产物；固定 trace 的位置在采样前冻结，不把该结果描述为包含在线合法化的 closed-loop 性能。

| 用例 | CPU/full | CPU/incremental | CUDA/full | CUDA/incremental |
|---|---:|---:|---:|---:|
| xtea/q | 1.017 | 1.048 | 1.171 | 1.018 |
| xtea/d | 1.041 | 1.035 | 1.168 | 0.988 |
| usb/q | 1.038 | 1.078 | 1.250 | 1.038 |
| usb/d | 1.033 | 1.085 | 1.275 | 1.056 |
| zipdiv/q | 0.996 | 1.038 | 1.302 | 1.019 |
| zipdiv/d | 1.024 | 1.044 | 1.284 | 1.015 |

短样本保留全部负结果：xtea/D 的 CUDA/incremental 和 zipdiv/Q 的 CPU/full 中位数略退化；xtea 的 CPU/full、CUDA/incremental 等区间跨过 1，不能据点估计宣称稳定收益。优化后 CUDA/full 相对 native CPU/full，在 xtea/Q、D 仅为 0.527、0.572；xtea/D 的 CUDA/incremental 相对 CUDA/full 为 0.978，仍有小规模负收益。usb/zipdiv 的对应 CUDA/full 比值为 1.284–1.359，也只作本轮参考。

各模式绝对中位数、p95、MAD、配对 bootstrap 95% 区间和原始样本见 cost-reference-v76；local-validation-v77.json 保存重算及身份核验。三次采样的区间不能替代正式重复性验收。Stage 12 严格性能门、Stage 15 正式实验均保持 not_run；已完成的 xtea/Q 5/30 单独作为补充，不依据结果选择报告协议。

固定两批完整最终产物补验 v75 在 GPU 5、tmux stage14-physical-artifacts-v75 完成，driver 退出 0；与成本采样隔离，共用 512 GB 硬上限和 swap=0。三设计 Q/D、四模式、OFF/ON 均与独立 fresh native/full 的最终 prefix 比较通过，全部实际提交两批、最终 generation=2、无 fallback。SDF 仅排除 DATE，报告和 DEF/netlist 按完整内容比较；power 沿用 1e-10 容差，最大差 1.0587911840678754e-22，数值 canary 检出。

## 最终验收与保留限制

- v77 按冻结用例集合核验全部提交、输入/RC、真实 binding、只读 CUDA/debug 状态、最终 generation 和产物比较，不以固定数量替代覆盖。完整最终产物已取回本地，生产读取器验证大小、SHA 与 generation；初次筛选归档遗漏的原始 owner.lock 已补齐，再验证通过。服务器原始日志、诊断、产物、剖析和旧采样均保留。
- 源码组合 native v56、parent v66、probe v75 共 129 份身份一致，全部 native 工作区变更由这些清单覆盖；1326 个用户保留文件与基线一致。最初仅用 v56 清单检查时遇到已有 v66 Python 验证器差异，合并真实版本清单后通过；没有改动生产代码或重跑已完成采样。
- 独立最终代码审查通过；独立验收复核确认 v73 真实发布失败重试、v75 固定多批次完整产物、v70/v72 调用及分配证据、v76 参考成本均已补齐，Stage 14 可关闭。该结论不替代 Stage 13 尚未完成的托管 GPU CI，也不替代 Stage 12/15 正式性能验收。

| 验收范围 | 最终证据与结论 |
|---|---|
| Release OFF/ON 严格构建及 native 回归 | v57；OFF 28 项通过、两项诊断禁用，ON 35 项通过；v56 硬件错误用例单独通过 |
| 三设计固定 Q/D 两批与独立 fresh | v60 公开/完整诊断比较通过，v75 最终完整产物比较通过；ON/OFF 实际模式与 generation 已核验 |
| closed-loop 与末轮输出恢复 | v68/v74：xtea/usb 为无正 gain 基线退出，zipdiv 真正提交一批；v73 OFF/ON 真实发布失败后恢复重试通过，不重复编辑 |
| 默认无 CUDA 及内存/并发检查 | v59 默认 CUDA=false/debug=false，相关九项通过、两项禁用；CUDA memcheck/initcheck/racecheck/synccheck 及 v62 修正 replay 检查通过 |
| parent 与修改文件检查 | 相关 73 项、ECC 405 项及非 integration/pdk/slow 的 1725 项回归通过；8 skipped、4 deselected、13 xfailed 保留；最终 probe 的 26 项测试及 lint/type 通过，两仓库 diff 检查通过 |
| 运行路径与实际成本 | v70 调用/Nsight、v72 heaptrack 及六组 v76 参考成本核验通过；必要 full 重建、传播、回传及末轮工作均保留计量 |

CPU ASan/UBSan 原配置因既有 Logger ODR 冲突失败；仅排除 _log_instance 后的三项通过，不能记为无排除通过。全仓 ty 仍失败（2174 diagnostics），修改生产文件与基线相同的既有问题已单列，未宣称全仓类型通过。性能计数器仍因权限限制 not_run，未修改驱动安全配置；托管 GPU CI 没有实际运行。

本阶段完成的是直接 CSR 编辑、共同事务、最小候选消费、末轮产物、正确性与路径/参考成本验收。1/3 短样本、固定合法位置及小规模负收益限制完整保留；Stage 12 严格性能门和 Stage 15 正式实验保持 not_run。

## picorv32a 性能回退修复（2026-10-10）

直接 CSR 路径重复导出基线、重复完整证明、复制 ArcGroup key，并逐项移动 index 尾部。现复用受控导出，OFF 省去内部重复证明，公共入口及 ON 完整验证保留；批量 index apply/undo 改为一次压缩和展开，capture 统计只做一次，比较借用 key。保留实际旧值、预分配和失败撤销。

Release/OFF，Q/D 各十批×100 buffer、1 次预热与 3 次采样：CUDA/incremental 中位数由 18.626/15.665 秒降至 5.941/6.979 秒；相对 Stage 12 为 1.29×/1.09×，包含逐批报告改为末轮报告的差异。D incremental 仍比同版 CUDA/full 慢约 3%；共享服务器及短采样限制保留，不作为正式性能验收。

相关 OFF/ON、默认无 CUDA、index ASan/UBSan、CUDA memcheck/initcheck、跨构建、恢复和公开结果比较通过。调用剖析确认 OFF 不再执行完整 reference 重验，必要 index/state 校验仍执行。证据与分项耗时在 /home/shigure/code/picorv32a-stage14-opt-20261010-r2；原始负结果保留，临时大输入与构建已清理。
