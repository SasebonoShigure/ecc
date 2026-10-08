# IncreGPUSTA 使用

在项目 ecc.toml 中选择实验流程；它在 CTS、合法化之后运行物理时序优化，再交给 routing：

    [flow]
    preset = "incregpusta_experimental"

    [params.sta]
    backend = "cuda"
    update_strategy = "incremental"
    fallback_policy = "error"

    [params.incregpusta]
    top_k = 100
    max_rounds = 10
    max_buffers = 1000
    horizontal_rc_layer = "auto"
    vertical_rc_layer = "auto"

运行 ecc run。backend 可选 cpu/cuda，update_strategy 可选 full/incremental；省略 STA 配置时仍为 cpu/full/error。RC 层默认取 routing 范围内最低可用方向层，也可填写具体层名。需要 CUDA 编译的 native 库才能选择 cuda。

产物发布失败时，用 ecc run --workspace WORKSPACE --from "Timing optimization" 重试；该入口保留已提交物理编辑。修改上游输入或预算后使用独立 run，不复用旧恢复历史。当前产物由 Timing optimization_ecc/output/physical_session/artifacts/manifest.json 指定；routing 自动读取，不手动选择旧 DEF。

## 开发检查

native 构建显式使用 -DECC_INCREGPUSTA_DEBUG_CHECKS=ON 开启诊断；默认 OFF。OFF/ON 使用不同构建目录，并隔离各自的 ecc_tools_bin 包。

CPU 检查：

    ctest --test-dir BUILD_NO_CUDA -L 'ista_unit|ista_property|ista_smoke|physical' --output-on-failure
    ctest --test-dir BUILD_NO_CUDA -L ista_integration --output-on-failure

GPU correctness 在服务器已有 GPU 环境手动执行；选空闲非 0 GPU，经 docker/run-container.sh --gpu N 启动持久会话。OFF/ON 各运行：

    ctest --test-dir BUILD -L 'ista_cuda|physical' -E context-fault --output-on-failure

故意破坏 CUDA context 的测试单独执行：

    ctest --test-dir BUILD_ON -R context-fault --output-on-failure

## 物理 trace 与独立对照

在 ECC 仓库根目录运行；PYTHONPATH 指向所需隔离 binding 包的父目录以及仓库根目录。所有输出目录必须不存在。以下参数用实际路径替换：

    python test/tools/ecc/physical_sta_probe.py \
      --workspace POST_CTS_WORKSPACE --binding-dir BINDING/ecc_tools_bin \
      --def-file BASELINE.def --verilog-file BASELINE.v --sdc DESIGN.sdc \
      --mode ON --backend cuda --strategy incremental \
      --physical-trace physical-trace.json --output TARGET

首次从已有语义编辑 trace 冻结合法化坐标，将 --physical-trace 换成 --prepare-from replay.json，并使用 --backend cpu --strategy full。生成的 physical-trace.json 供全部模式复用。

每个已提交 prefix 使用新进程运行原生 CPU/full：

    python test/tools/ecc/physical_sta_probe.py \
      --workspace POST_CTS_WORKSPACE --binding-dir BINDING_ON/ecc_tools_bin \
      --def-file TARGET/generation-1.def --verilog-file TARGET/generation-1.v \
      --sdc DESIGN.sdc --mode ON --backend cpu --strategy full --fresh --output FRESH

    python chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/test/physical_sta/physical_sta_compare.py \
      --target TARGET/diagnostic-1.json --fresh FRESH/diagnostic.json --generation 1 --canaries

OFF 同样运行真实编辑，省略完整诊断；它不能作为 fresh oracle。普通性能入口保持 OFF。
