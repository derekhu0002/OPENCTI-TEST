# Mirror 保护基线

本文件冻结 Neo4j mirror 显性 testcase 的 THEN 断言边界，不允许在后续编码阶段缩减。

## THEN

1. 必须存在标签为 `:ipv4-addr` 且 `value='1.2.3.4'` 的节点。
2. 上述节点的 `standard_id` 必须与 OpenCTI 中一致。
3. 执行 `MATCH (a:ipv4-addr)-[r:indicates]->(b:malware) RETURN r` 必须能查询到关系。