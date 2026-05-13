# Query Backend Docker 统一代理保护基线

本文件冻结 Docker 统一代理显性 testcase 的 THEN 断言边界，不允许在后续编码阶段缩减。

## THEN

1. 统一代理入口 `https://localhost/graph/query` 必须可达，并能把请求转发到查询后端容器。
2. 通过统一代理入口提交包含写操作的 Cypher 时，响应必须返回 `backend=neo4j-replica`、`investigation_id`、结构化 `rejection_reason` 和 `budget_policy`。
3. 响应不得把统一代理入口伪装为 OpenCTI 或 GraphQL 路径的结果。