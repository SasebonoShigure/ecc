# IncreGPUSTA 开发检查规范

适用范围：Stage 0 起的 IncreGPUSTA 实现与后续开发。此文件由总实施计划要求在改动前阅读，不修改仓库通用 README。

## 构建与运行

`ECC_INCREGPUSTA_DEBUG_CHECKS` 默认 OFF，独立于 CMake Debug/Release。使用 `-DECC_INCREGPUSTA_DEBUG_CHECKS=ON` 开启开发诊断；Release + ON 仍执行诊断，不依赖 NDEBUG 或 assert。

native 库、binding、probe 共用生成的构建配置。Python 只读取 native 的 `incregpusta_debug_checks_enabled`，不提供运行期开关或环境变量。

## 必须区分的检查

始终保留外部输入解析与范围、session/generation/owner、算法必需的容量/数值/cycle、unsupported/fallback、事务原子提交、真实回滚与恢复。状态更新、必要快照/索引和恢复所需编辑记录不能放入诊断分支。

仅 ON 执行重复全图/索引校验、独立 oracle、验证性第二次传播/重建、完整对象比较、诊断快照/摘要、详细访问计数与恒等式、故障注入。关闭时必须同时消除仅为诊断准备的数据与序列化。未运行的验证记录为 not_run，禁止伪造 PASS 或完整验证凭证。

不能按函数名批量关闭：逐个沿调用链区分外部输入、内部已受控状态以及纯诊断消费者。混合函数必须拆开必要检查与诊断工作。编译开关使用作用域清楚的常量条件或预处理块，不设计通用策略框架。

## 测试与性能

OFF 保留正常功能与必要失败回归；ON 运行完整 oracle/fresh replay/逐字段比较和故障注入。在独立开发验收中比较两套构建相同输入的功能结果。

正式性能入口只接受 OFF；不启动 oracle、不生成完整 receipt、不比较 source isolation。保留预热、原始样本、实际结果、构建状态、requested/executed mode 和 fallback。初始加载与正常清理是功能生命周期，不能省略。ON 下性能入口必须在采样前拒绝。性能记录明确 correctness comparison=not_run，不把性能成功写成正确性证明。

每次变更更新检查分类和实现报告，记录实际命令、失败及修复。使用功能测试和代表性调用剖析验证诊断路径，不建立源码字符串、对象清单、固定测试数量门禁。不升级依赖或修改其他项目算法。
