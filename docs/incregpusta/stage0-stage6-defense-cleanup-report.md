# 阶段 0–6 报告：过度防御与哈希冗余清理

> 状态：完成；功能回归、边界验证、hygiene及两轮独立终审均闭合
> 日期：2026-09-03
> 基线：parent `48c09f84f4abfa60c95c0e4b7809c96ee31f97e3`，ecc-tools `b8bfc3a79930b0be146ac26ca10dc0e99115f1fc`
> 完成提交：ecc-tools child `8eed90e86c934052f2eb10a8c114f7e41f6db7df`；parent由本报告和submodule pointer所在的后续本地提交承载；均不push
> 验收原则：功能正确性、语义一致、fresh replay和source unchanged是主证据；哈希只保留真实artifact或跨进程输入边界用途，不扩张为无上限“哈希攻防”

## 1. 结论

本轮没有改变Stage 0–6的功能范围，而是删除与功能结果脱节的静态实现门禁、重复摘要和blind echo链。ecc-tools共修改105个文件，净变化为690行新增、11569行删除。全部相关功能回归最终通过；功能终审与哈希边界终审均为`APPROVE`，blocker、major、minor均为0。

审查同时发现并修复一项真实正确性缺口：CSR session原先只比较同case内session/repeat的一致性，没有把session projection/FIFO与已验证legacy/default结果绑定，因此“每次都稳定地产生同一个错误结果”可能通过。新contract直接保存并比较完整原始字节，并分别加入projection与FIFO稳定漂移负例。

## 2. 删除内容

### 2.1 静态实现清单

- 删除目标`SOURCES`、`LINK_LIBRARIES`、`COMPILE_OPTIONS`自比较，以及对象文件、Ninja输出、CTest数量、AST/源码字符串、source SHA和递归link-closure门禁。
- 删除Stage 2内部步骤和Stage 3–6的source inventory、target/workflow镜像、ownership字符串计数及无消费者CMake变量。
- 保留真实target、strict compile flags，以及功能、属性、故障注入、事务、恢复和fresh-process测试。

### 2.2 重复或无边界哈希

- Stage 0：删除topology/config/full-snapshot诊断哈希和manifest固定输入哈希；完整snapshot与artifact逐字段/容差比较成为权威。
- projection：删除只在同一父进程中自证的文件SHA和输入复合指纹。
- reference-input：删除父端提供、子端不重算而原样回显的`input_case_sha256`绑定字段、CLI、wire、schema与负例。
- session/real-differential：删除完整projection、FIFO、raw、snapshot、replay、clock、descriptor及payload旁边的重复SHA，改用完整字节或typed object直接比较。
- Stage 4：删除`IntegrityReceipt`、`frozen_artifact_digest`及其canonical encoder、schema和validator链。
- Stage 5/6：删除无消费者的hash-as-acceptance布尔字段和静态ownership门禁。

## 3. 明确保留的边界

- `CsrSnapshotIdentity`和`ComponentFingerprints`继续承担generation/session stale-state与invalidation身份判定。
- real-differential父端读取五个实际输入文件生成绑定值；oracle/reference两个C++子进程分别再次读取文件、独立重算并比较。该哈希是实际跨进程输入边界，不是功能结果替身。
- timing-edit source `content_sha256`绑定未嵌入trace的源文件内容；baseline `binary_sha256`只覆盖无法结构化解码比较的`instance_power.bin`。
- SHA实现KAT保留为算法实现测试；它不参与Stage功能PASS判定。

## 4. 验证

- Nix/GCC 14 Release/Ninja最终重新configure成功；仅有既有pybind11 `CMP0148`开发警告。
- Stage 0–4 focused功能集55/55通过；projection/real-differential边界集5/5通过，其中real-differential fresh双进程约94秒。
- Stage 5/6联合功能标签25/25通过；单独Stage 5为4/4，Stage 6为14/14。
- 联合标签首次运行有18项因对应测试target尚未构建而`Not Run`；明确构建18个目标全部成功后，以相同标签原样复跑25/25。没有把缺少二进制、skip或静态门禁绿灯计作功能通过。
- reference-input四个关键target构建通过，针对性6/6；session controller与真实fresh-process 2/2；graph encoding、timing-edit oracle和real-differential针对性回归均通过。
- 12个现存变更JSON全部解析通过；全部变更Python通过忽略存量纯风格规则后的实质lint；`git diff --check`通过；无`__pycache__`、`.pyc`或意外未跟踪生成物。
- 两名独立审查者分别从功能契约与哈希边界复核最终diff，结论均为`APPROVE`，blocker/major/minor为0/0/0。

## 5. 边界

本轮不新增CUDA、GPU、affected-cone、物理提交或性能结论，也不改变Stage 7及以后范围。Stage 0–6仍以既有功能收据和回归为准；后续阶段继续遵守总体plan的功能优先验收条款，不得重新引入与真实边界无关的哈希、对象清单或源码扫描攻防。
