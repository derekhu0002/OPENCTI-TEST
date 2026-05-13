# Query Backend 保护基线

本文件冻结查询后端显性 testcase 的 THEN 断言边界，不允许在后续编码阶段缩减。

## THEN

1. 对正常成功的图查询，响应必须返回 `backend=neo4j-replica`、`investigation_id`、`freshness_ts`、`staleness_seconds`、`sync_status` 和机器可消费的 `results` 载荷，且不得返回 `rejection_reason`。
2. 对被拒绝的 Cypher，请求不得在副本上执行，响应必须返回结构化 `rejection_reason`、`budget_policy` 与 `investigation_id`。
3. 对副本不可安全使用的场景，响应必须返回 `backend=neo4j-replica`、`freshness_ts`、`staleness_seconds` 与 `sync_status`。
4. 副本降级时不得静默回退到 GraphQL 翻译路径并伪装为成功结果。