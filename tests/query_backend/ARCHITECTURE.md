# tests/query_backend 局部契约

## 1. 角色

本目录承载查询后端显性 testcase 的物理入口集合，以及这些入口对应的保护夹具与保护基线。

## 2. 作用域

本契约覆盖：

- `conftest.py`
- `test_query_backend_acceptance.py`
- `test_query_backend_docker_acceptance.py`
- `protected_fixtures/`
- `protected_baselines/`

参考根契约：`../../OVERALL_ARCHITECTURE.md`

## 3. 稳定元素

- `conftest.py`：查询后端显性验收的局部 pytest 装配点；优先连接已运行的容器化健康实例，必要时只为测试期补位隔离实例，但不得新增第二个显性入口。
- `test_query_backend_acceptance.py`：查询后端 API 契约只读显性入口。
- `test_query_backend_docker_acceptance.py`：查询后端 Docker 统一代理只读显性入口。
- `protected_fixtures/rejected_cypher_and_degraded_probe.md`：受保护的成功、拒绝与降级场景夹具描述。
- `protected_fixtures/docker_proxy_probe.md`：受保护的 Docker 统一代理入口场景夹具描述。
- `protected_baselines/response_contract.md`：受保护的成功、拒绝与降级响应断言基线。
- `protected_baselines/docker_proxy_contract.md`：受保护的 Docker 统一代理入口断言基线。

## 4. 接口边界

- 输入边界：`QUERY_BACKEND_BASE_URL`、`QUERY_BACKEND_DEGRADED_BASE_URL`、`QUERY_BACKEND_AUTH_TOKEN`、`QUERY_BACKEND_INVESTIGATION_ID`、`QUERY_BACKEND_SUCCESS_CYPHER`。
- 当 `QUERY_BACKEND_BASE_URL` 指向已运行的 compose 容器时，本目录必须直接复用该健康实例；降级实例可以通过单独 base URL 注入，未注入时才允许测试期补位本地实例。
- Docker 统一代理显性入口使用 `QUERY_BACKEND_DOCKER_BASE_URL`，默认目标是 `https://localhost`，并通过 `POST /graph/query` 验证 Caddy 到 query-backend 容器的真实转发路径。
- 输出边界：只读验证查询后端的正常成功、结构化拒绝与降级响应，不负责创建业务数据。
- 本目录冻结四类显性场景：正常成功、受控拒绝、副本降级与 Docker 统一代理入口。

## 5. 依赖方向

- 本目录可以只读依赖根契约、意图图谱、本目录内的保护文件与运行时覆盖变量。
- 本目录不得依赖 `query-backend/` 的内部实现；后续实现应反向满足本入口，而不是要求本入口迁移。

## 6. implements 追溯

- `test_query_backend_acceptance.py::test_successful_query_returns_graph_payload_and_freshness_metadata` 直接看护 `ReplicaGraphQueryBackend` 与 `AIAgentGraphInvestigation` 的正常成功路径规格。
- `test_query_backend_acceptance.py::test_controlled_cypher_rejection_returns_structured_feedback` 直接 implements `受控 Cypher 拒绝与结构化反馈`。
- `test_query_backend_acceptance.py::test_replica_degradation_does_not_fall_back_silently` 直接 implements `副本降级不静默回退`。
- `test_query_backend_docker_acceptance.py::test_docker_proxy_entry_preserves_structured_rejection_contract` 直接 implements `Docker统一代理查询入口可用性验证`。
- 保护夹具和保护基线通过实现链间接承载同一组显性 testcase。

## 7. 显性 testcase 入口

- API 契约入口：`test_query_backend_acceptance.py`
- Docker 统一代理入口：`test_query_backend_docker_acceptance.py`

## 8. 关键非显性测试

- 根级 `../test_acceptance_baselines.py` 冻结本目录入口路径与保护文件存在性。
- 根级 `../test_implementation_traceability.py` 冻结本目录与意图 testcase 的实现链。

## 9. 普通非显性测试

- `conftest.py`：保留为局部 pytest 装配点，但不得再通过本地 HTTP stub 伪造查询后端可用性，也不得改写显性入口函数名与路径。
- 后续若需要补充更多查询后端支撑测试，应继续放在 `../../query-backend/tests/` 下，并在相关局部契约中回填归属。

## 10. 保护对象

- 入口文件路径与测试函数名。
- `protected_fixtures/rejected_cypher_and_degraded_probe.md`
- `protected_fixtures/docker_proxy_probe.md`
- `protected_baselines/response_contract.md`
- `protected_baselines/docker_proxy_contract.md`

## 11. 变更规则

- 后续编码阶段不得修改这些入口的挂载位置、成功/拒绝/降级/代理断言边界以及保护文件路径。