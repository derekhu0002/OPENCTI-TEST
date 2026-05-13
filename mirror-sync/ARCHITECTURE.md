# mirror-sync 局部契约

## 1. 角色

本目录承载 OpenCTI 到 Neo4j 热子图副本的同步实现边界，只负责副本写入、新鲜度与对账，不承载 Agent 查询入口。

## 2. 作用域

本契约覆盖 `mirror-sync/` 目录作为稳定实现元素的职责边界，以及后续在本目录下新增的实现与 `tests/` 挂载点。

参考根契约：`../OVERALL_ARCHITECTURE.md`

## 3. 稳定元素

- `mirror-sync/`：承载同步入口、watermark、新鲜度状态与删除对齐的稳定目录边界。
- `tests/`：后续编码阶段用于挂载同步支撑护栏的默认位置，不是显性 testcase 主入口。

## 4. 接口边界

- 输入边界：OpenCTI live stream、增量拉取能力、主 compose 默认网络中的 `opencti`/`neo4j` 服务，以及 `.env` 中的 `MIRROR_*` 与 Neo4j 连接变量。
- 输出边界：Neo4j 热子图、副本 freshness 状态、watermark、对账结果与删除或失效对齐状态。
- 本目录不得向 `query-backend/` 暴露 Agent 查询接口；它只暴露副本读模型与 freshness 契约。

## 5. 依赖方向

- 允许依赖：OpenCTI、Neo4j、运行时平台契约、标准库与第三方库。
- 禁止依赖：`tests/`、`scripts/`、`query-backend/` 的内部实现。

## 6. implements 追溯

- 本目录直接 implements `OpenCTIToNeo4jMirrorSync`。
- 本目录通过产出副本读模型与 freshness 状态，间接承载 `ReplicaGraphQueryBackend` 与 `AIAgentGraphInvestigation`。
- 显性 testcase `OpenCTI 情报数据镜像至 Neo4j 完整性验证` 固定由 `../tests/mirror/test_neo4j_sync_integrity.py` 直接承载，本目录后续实现必须满足该入口而不是改写入口。

## 7. 显性 testcase 入口

本目录无显性 testcase 主入口；与本目录相关的显性验收固定收口在 `../tests/mirror/test_neo4j_sync_integrity.py`。

## 8. 关键非显性测试

- `../tests/test_architecture_contracts.py` 冻结本目录必须存在局部契约并沿用共享骨架。
- `../tests/test_dependency_boundaries.py` 冻结本目录只负责同步入口，不得向查询后端边界泄漏 Agent 查询职责。
- `../tests/test_implementation_traceability.py` 冻结本目录与 `OpenCTIToNeo4jMirrorSync` 的直接实现关系。

## 9. 普通非显性测试

- 后续编码阶段默认在 `mirror-sync/tests/` 下补充增量同步、watermark、删除或 tombstone、reconcile 支撑测试。

## 10. 保护对象

- 本局部契约对 `OpenCTIToNeo4jMirrorSync` 的直接 implements 声明。
- `../tests/mirror/test_neo4j_sync_integrity.py` 作为只读显性入口的挂载关系。

## 11. 变更规则

- 不得把查询后端、脚本或测试内部实现塞进本目录，避免把同步边界退化成多职责浅层模块。
- 若后续需要拆分子目录，只允许围绕同步职责分解，且不得改变显性 testcase 的挂载位置。