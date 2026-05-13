# tests/query_backend 局部契约

## 1. 角色

本目录承载查询后端显性 testcase 的唯一物理入口，以及该入口对应的保护夹具与保护基线。

## 2. 作用域

本契约覆盖：

- `test_query_backend_acceptance.py`
- `protected_fixtures/`
- `protected_baselines/`

参考根契约：`../../OVERALL_ARCHITECTURE.md`

## 3. 稳定元素

- `test_query_backend_acceptance.py`：查询后端只读显性入口。
- `protected_fixtures/rejected_cypher_and_degraded_probe.md`：受保护的成功、拒绝与降级场景夹具描述。
- `protected_baselines/response_contract.md`：受保护的成功、拒绝与降级响应断言基线。

## 4. 接口边界

- 输入边界：`QUERY_BACKEND_BASE_URL`、`QUERY_BACKEND_DEGRADED_BASE_URL`、`QUERY_BACKEND_AUTH_TOKEN`、`QUERY_BACKEND_INVESTIGATION_ID`、`QUERY_BACKEND_SUCCESS_CYPHER`。
- 输出边界：只读验证查询后端的正常成功、结构化拒绝与降级响应，不负责创建业务数据。
- 本目录冻结三类显性场景：正常成功、受控拒绝与副本降级。

## 5. 依赖方向

- 本目录可以只读依赖根契约、意图图谱、本目录内的保护文件与运行时覆盖变量。
- 本目录不得依赖 `query-backend/` 的内部实现；后续实现应反向满足本入口，而不是要求本入口迁移。

## 6. implements 追溯

- `test_query_backend_acceptance.py::test_successful_query_returns_graph_payload_and_freshness_metadata` 直接看护 `ReplicaGraphQueryBackend` 与 `AIAgentGraphInvestigation` 的正常成功路径规格。
- `test_query_backend_acceptance.py::test_controlled_cypher_rejection_returns_structured_feedback` 直接 implements `受控 Cypher 拒绝与结构化反馈`。
- `test_query_backend_acceptance.py::test_replica_degradation_does_not_fall_back_silently` 直接 implements `副本降级不静默回退`。
- 保护夹具和保护基线通过实现链间接承载同一组显性 testcase。

## 7. 显性 testcase 入口

- 唯一入口：`test_query_backend_acceptance.py`

## 8. 关键非显性测试

- 根级 `../test_acceptance_baselines.py` 冻结本目录入口路径与保护文件存在性。
- 根级 `../test_implementation_traceability.py` 冻结本目录与意图 testcase 的实现链。

## 9. 普通非显性测试

- 后续若需要补充更多查询后端支撑测试，应继续放在 `../../query-backend/tests/` 下，并在相关局部契约中回填归属。

## 10. 保护对象

- 入口文件路径与测试函数名。
- `protected_fixtures/rejected_cypher_and_degraded_probe.md`
- `protected_baselines/response_contract.md`

## 11. 变更规则

- 后续编码阶段不得修改本入口的挂载位置、成功/拒绝/降级断言边界以及保护文件路径。