# query-backend 局部契约

## 1. 角色

本目录承载面向远端 AI Agent 的查询后端稳定边界，负责受控 Cypher、schema 视图、预算、审计、调查会话和结构化拒绝。

## 2. 作用域

本契约覆盖 `query-backend/` 目录作为稳定实现元素的职责边界，以及后续在本目录下新增的实现与 `tests/` 挂载点。

参考根契约：`../OVERALL_ARCHITECTURE.md`

## 3. 稳定元素

- `query-backend/`：承载查询 API、schema 视图、预算控制、审计与调查会话的稳定目录边界。
- `tests/`：后续编码阶段用于挂载查询后端支撑护栏的默认位置，不是显性 testcase 主入口。

## 4. 接口边界

- 输入边界：Agent 图查询请求、受控 Cypher、调查会话上下文、`investigation_id`、副本 freshness 状态与裁剪后 schema 视图。
- 输出边界：机器可消费的图结果、人类可复核的证据视图、`rejection_reason`、`budget_policy`、`freshness_ts`、`staleness_seconds` 与 `sync_status`。
- 本目录不得直接依赖 OpenCTI，不得静默回退到 GraphQL 翻译路径；副本不可用时只能返回降级状态或结构化拒绝。

## 5. 依赖方向

- 允许依赖：副本读模型、freshness 状态、运行时平台契约、标准库与第三方库。
- 禁止依赖：OpenCTI 直连、GraphQL 翻译回退、`tests/`、`scripts/`、`mirror-sync/` 的内部实现。

## 6. implements 追溯

- 本目录直接 implements `ReplicaGraphQueryBackend`。
- 本目录直接 implements `AIAgentGraphInvestigation`。
- 显性入口中的正常成功路径规格、`受控 Cypher 拒绝与结构化反馈` 与 `副本降级不静默回退` 固定由 `../tests/query_backend/test_query_backend_acceptance.py` 直接承载，本目录后续实现必须满足该入口而不是改写入口。

## 7. 显性 testcase 入口

本目录无显性 testcase 主入口；与本目录相关的显性验收固定收口在 `../tests/query_backend/test_query_backend_acceptance.py`。

## 8. 关键非显性测试

- `../tests/test_architecture_contracts.py` 冻结本目录必须存在局部契约并沿用共享骨架。
- `../tests/test_dependency_boundaries.py` 冻结本目录不得直接依赖 OpenCTI 或静默回退到 GraphQL。
- `../tests/test_implementation_traceability.py` 冻结本目录与 `ReplicaGraphQueryBackend`、`AIAgentGraphInvestigation` 的直接实现关系。

## 9. 普通非显性测试

- 后续编码阶段默认在 `query-backend/tests/` 下补充 schema 视图、预算策略、响应元数据与调查会话支撑测试。

## 10. 保护对象

- 本局部契约对 `ReplicaGraphQueryBackend` 与 `AIAgentGraphInvestigation` 的直接 implements 声明。
- `../tests/query_backend/test_query_backend_acceptance.py` 作为只读显性入口的挂载关系。

## 11. 变更规则

- 不得把同步细节、脚本编排或测试内部实现吸入本目录，避免把查询后端退化成跨层耦合入口。
- 若后续需要拆分子目录，只允许围绕查询后端职责分解，且不得改变显性 testcase 的挂载位置。