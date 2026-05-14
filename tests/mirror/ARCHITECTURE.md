# tests/mirror 局部契约

## 1. 角色

本目录承载 Neo4j mirror 显性 testcase 的唯一物理入口，以及该入口对应的保护夹具与保护基线。

## 2. 作用域

本契约覆盖：

- `conftest.py`
- `test_neo4j_sync_integrity.py`
- `test_bootstrap_window_acceptance.py`
- `test_live_incremental_acceptance.py`
- `test_projection_policy_acceptance.py`
- `test_reconcile_acceptance.py`
- `protected_fixtures/`
- `protected_baselines/`

参考根契约：`../../OVERALL_ARCHITECTURE.md`

## 3. 稳定元素

- `conftest.py`：镜像显性验收所需的自动夹具装配与 Neo4j 访问适配层；运行时事实上的一等 Neo4j 目标由主 compose 中与 OpenCTI 同网段的 `neo4j` service 提供。
- `_fixture_support.py`：镜像显性验收的支撑夹具模块，只负责记录测试启动锚点、通过真实 OpenCTI GraphQL 建立场景以及等待真实副本结果，不得直接调用 mirror-sync 内部实现。
- `test_neo4j_sync_integrity.py`：最小链路显性入口。
- `test_bootstrap_window_acceptance.py`：时间窗与 2 跳补齐显性入口。
- `test_live_incremental_acceptance.py`：增量与恢复显性入口。
- `test_projection_policy_acceptance.py`：属性投影显性入口。
- `test_reconcile_acceptance.py`：删除与修复显性入口。
- `protected_fixtures/manual_seed_steps.md`：受保护的场景夹具描述。
- `protected_baselines/cypher_assertions.md`：受保护的查询断言基线。
- `protected_fixtures/bootstrap_window_probe.md`：时间窗与 2 跳补齐显性入口的受保护场景夹具。
- `protected_fixtures/live_incremental_probe.md`：增量与恢复显性入口的受保护场景夹具。
- `protected_fixtures/projection_policy_probe.md`：属性投影显性入口的受保护场景夹具。
- `protected_fixtures/reconcile_probe.md`：删除与修复显性入口的受保护场景夹具。
- `protected_baselines/bootstrap_window_contract.md`：时间窗与 2 跳补齐显性入口的受保护断言基线。
- `protected_baselines/live_incremental_contract.md`：增量与恢复显性入口的受保护断言基线。
- `protected_baselines/projection_policy_contract.md`：属性投影显性入口的受保护断言基线。
- `protected_baselines/reconcile_contract.md`：删除与修复显性入口的受保护断言基线。
- `test_fixture_setup_support.py`：镜像自动建夹具支撑测试入口。

## 4. 接口边界

- 输入边界：`.env` 中的 OpenCTI 与 Neo4j mirror 配置、主 compose 默认网络中的 `neo4j` service，以及运行时覆盖变量 `MIRROR_EXPECTED_IPV4_VALUE`、`MIRROR_EXPECTED_MALWARE_NAME`、`MIRROR_ASSERT_TIMEOUT_SECONDS`。
- 输入边界同时允许真实环境验收通过显式 bootstrap 启动锚点变量缩小初始扫描范围，例如 `BOOTSTRAP_START_AT`；该锚点只用于测试覆盖，不改变产品默认近一年窗口。
- `BOOTSTRAP_START_AT` 在本目录中的含义是“测试启动锚点”，用于避免共享 OpenCTI 中近期大量真实数据拖慢验收；测试只能缩小扫描范围，不能借此改变产品默认窗口语义。
- `MIRROR_STREAM_ID` 在本目录中的含义是 mirror-sync 容器订阅的 live stream 标识；测试契约只要求它存在并可配置，不要求受保护入口直接解析该值。
- `MIRROR_BOOTSTRAP_LOOKBACK_DAYS` 与 `MIRROR_POLL_INTERVAL_SECONDS` 分别为默认 bootstrap 窗口与等待轮询频率提供配置边界；受保护入口只依赖它们的语义，不把具体数值冻结为测试断言。
- 输出边界：显性入口测试体只读验证 Neo4j HTTP 查询结果；场景数据必须由本目录支撑 fixture 在断言前通过真实 OpenCTI GraphQL 自动建立，不得直接 import 或调用 `mirror-sync/` 的内部同步函数。

## 5. 依赖方向

- 本目录可以只读依赖根契约、意图图谱、`.env` 和本目录内的保护文件。
- 本目录不得依赖未来 mirror 实现目录的内部细节；后续实现应反向满足本入口，而不是要求本入口迁移。
- 本目录允许通过真实 OpenCTI API 造数，但禁止通过 import `mirror-sync/` 内部实现来伪造同步结果。

## 6. implements 追溯

- `test_neo4j_sync_integrity.py` 直接 implements 图谱中的 `OpenCTI 情报数据镜像至 Neo4j 完整性验证`。
- `test_bootstrap_window_acceptance.py` 直接 implements `近一年窗口热子图初始化同步` 与 `二跳邻域补齐完整性`。
- `test_live_incremental_acceptance.py` 直接 implements `Live Stream 增量实时同步` 与 `Watermark 恢复后幂等补偿`。
- `test_projection_policy_acceptance.py` 直接 implements `属性名称与默认基线投影一致性`。
- `test_reconcile_acceptance.py` 直接 implements `删除与撤销状态对齐`。
- 保护夹具和保护基线通过实现链间接承载同一显性 testcase。

## 7. 显性 testcase 入口

- `test_neo4j_sync_integrity.py`
- `test_bootstrap_window_acceptance.py`
- `test_live_incremental_acceptance.py`
- `test_projection_policy_acceptance.py`
- `test_reconcile_acceptance.py`

## 8. 关键非显性测试

- 根级 `../test_acceptance_baselines.py` 冻结本目录入口路径与保护文件存在性。

## 9. 普通非显性测试

- `conftest.py`：通过本地 Neo4j HTTP 脚手架为显性入口提供最小执行环境，不上升为新的显性入口。
- `test_fixture_setup_support.py`：自动建夹具支撑测试，用于在显性验收前记录 bootstrap 启动锚点、通过 OpenCTI GraphQL 建立固定场景数据，并等待真实同步容器完成副本更新。
- 后续若需要补充更多 mirror 支撑测试，应放在本目录或未来 mirror 实现目录的 `tests/` 下，并在局部契约中回填归属。

## 10. 保护对象

- 入口文件路径与测试函数名。
- `protected_fixtures/manual_seed_steps.md`
- `protected_baselines/cypher_assertions.md`
- `protected_fixtures/bootstrap_window_probe.md`
- `protected_fixtures/live_incremental_probe.md`
- `protected_fixtures/projection_policy_probe.md`
- `protected_fixtures/reconcile_probe.md`
- `protected_baselines/bootstrap_window_contract.md`
- `protected_baselines/live_incremental_contract.md`
- `protected_baselines/projection_policy_contract.md`
- `protected_baselines/reconcile_contract.md`

## 11. 变更规则

- 后续编码阶段不得修改本入口的挂载位置、查询对象、断言边界与保护文件路径。
- 后续编码阶段必须把 `_fixture_support.py` 收敛到“记录锚点 + OpenCTI 造数 + 观察副本”的职责，不得保留直接调用 mirror-sync 实现的测试捷径。