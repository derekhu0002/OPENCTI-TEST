# OPENCTI-TEST 实现架构总契约

## 1. 角色

本文件是工作区唯一的根级实现架构入口。它负责定义一级稳定实现元素、全局依赖方向、implements 追溯链、显性 testcase 的唯一物理入口，以及关键非显性测试冻结规则。

本版基于仓库事实与人工拍板结果，采用“运行时平台 + 副本同步 + 查询后端 + 集成扩展 + 运维脚本 + 验证护栏”的一级分层，不把私有函数、普通 helper、机械拆分出来的文件级模块提升为稳定实现元素。query-backend 作为独立容器交付，但不额外升格出新的一级 Delivery 层；容器交付面继续收口在运行时平台，查询语义边界继续收口在 `query-backend/`，统一外部入口继续由 Caddy 承载。

## 2. 作用域

本契约覆盖下列稳定实现元素：

- 运行时平台：`.env`、`.env.sample`、`docker-compose.yml`、`docker-compose.opensearch.yml`、`docker-compose.misp-test.yml`、`Caddyfile`、`rabbitmq.conf`
- 副本同步：`mirror-sync/`
- 查询后端：`query-backend/`
- 集成扩展：`connectors/`
- 运维脚本：`scripts/`
- 验证护栏：`tests/`

## 3. 稳定元素

### 3.1 一级稳定实现元素

| 一级元素 | 稳定职责 | 主要物理载体 | 局部契约 |
| --- | --- | --- | --- |
| 运行时平台 | 承载 OpenCTI、Neo4j、副本依赖基础设施、connector profile，以及 query-backend 与 mirror-sync 的容器化集成交付入口 | 根目录 compose 与配置文件 | 本文件直接管理 |
| 副本同步 | 承载 OpenCTI 到 Neo4j 热子图副本的同步边界、新鲜度状态与对账职责 | `mirror-sync/` | `mirror-sync/ARCHITECTURE.md` |
| 查询后端 | 承载面向远端 AI Agent 的受控查询、schema 视图、预算与审计边界 | `query-backend/` | `query-backend/ARCHITECTURE.md` |
| 集成扩展 | 承载仓库自研扩展及其与运行时平台的稳定边界 | `connectors/` | `connectors/ARCHITECTURE.md` |
| 运维脚本 | 承载启动、停止、备份、恢复等稳定操作入口 | `scripts/` | `scripts/ARCHITECTURE.md` |
| 验证护栏 | 承载显性 testcase 主入口、关键非显性测试与运行时基线数据 | `tests/` | `tests/ARCHITECTURE.md` |

### 3.2 二级稳定元素

- `connectors/automotive-security-timeline/` 是当前唯一自研扩展实现目录，由 `connectors/automotive-security-timeline/ARCHITECTURE.md` 约束。
- `tests/mirror/` 是 Neo4j mirror 显性 testcase 的唯一物理入口与保护基线目录，由 `tests/mirror/ARCHITECTURE.md` 约束。
- `tests/query_backend/` 是查询后端显性 testcase 的唯一物理入口与保护基线目录，由 `tests/query_backend/ARCHITECTURE.md` 约束。
- `tests/runtime/` 是运行时恢复与配置基线目录，由 `tests/runtime/ARCHITECTURE.md` 约束。

## 4. 接口边界

### 4.1 运行时平台暴露的稳定接口

- Compose 服务名、profile、环境变量边界。
- OpenCTI HTTPS 入口与管理员 token 配置边界。
- `docker-compose.yml` 中 `opencti` 与 `neo4j` 同属默认 compose 内部网络，副本同步与后续查询实现必须优先复用该容器内连通性，而不是把 Neo4j 视为独立外置前提。
- `docker-compose.yml` 中 `mirror-sync` 作为独立容器服务运行，使用 `mirror-sync/Dockerfile` 交付并通过 `OPENCTI_URL`、`OPENCTI_TOKEN`、`STREAM_ID`、`BOOTSTRAP_START_AT`、`MIRROR_BOOTSTRAP_LOOKBACK_DAYS`、`MIRROR_POLL_INTERVAL_SECONDS` 与 Neo4j 连接变量，以及 `mirror-sync/sync_scope.json` 的只读节点/关系 scope 契约，收口运行时配置边界；该契约内容变化在容器重启后会触发启用 scope 的受控 bootstrap 回放，用于补齐新增元素或新增属性。当前契约允许 `sync_scope.json` 显式选择一次性启用 `sync_scope.full.json` 的全部 candidate node scopes。
- `docker-compose.yml` 中 `query-backend` 作为独立容器服务运行；统一外部入口由 `Caddyfile` 在 `https://localhost/graph/query` 反向代理到 `query-backend:8088`，内部仍通过 compose 网络访问 `neo4j` 与 `mirror-sync/runtime/freshness.json` 绑定目录。
- MISP 测试专用 compose 变体入口。
- Neo4j 容器与 mirror 环境变量边界：服务名 `neo4j`、`NEO4J_ADVERTISED_HOST`、`NEO4J_HTTP_PORT`、`NEO4J_BOLT_PORT`、`NEO4J_PASSWORD`、`MIRROR_*`。
- query-backend 容器与运行时装配边界：`QUERY_BACKEND_PORT`、`QUERY_BACKEND_HOST`、`QUERY_BACKEND_AUDIT_LOG`、`NEO4J_MIRROR_HTTP_HOST`、`NEO4J_MIRROR_HTTP_PORT`、`NEO4J_MIRROR_USERNAME`、`NEO4J_MIRROR_PASSWORD`，以及 `Caddyfile` 中 `https://localhost/graph/query` 到 `query-backend:8088` 的统一反向代理规则。
- `QUERY_BACKEND_PORT`：主机侧暴露 query-backend 容器的端口；当前默认值为 `8088`，用于 compose 端口映射与统一 HTTPS 代理下游目标。
- mirror-sync 容器与运行时装配边界：`OPENCTI_URL`、`OPENCTI_TOKEN`、`STREAM_ID`、`BOOTSTRAP_START_AT`、`MIRROR_BOOTSTRAP_LOOKBACK_DAYS`、`MIRROR_POLL_INTERVAL_SECONDS`、`NEO4J_MIRROR_HTTP_HOST`、`NEO4J_MIRROR_HTTP_PORT`、`NEO4J_MIRROR_USERNAME`、`NEO4J_MIRROR_PASSWORD`、`mirror-sync/sync_scope.json`、`mirror-sync/sync_scope.full.json`，以及 `mirror-sync/runtime` 的持久化运行时目录；其中 `sync_scope.json` 是运行时契约，`sync_scope.full.json` 是 live schema 候选目录。只有 `sync_scope.json` 显式启用全量 candidate node scope 开关时，运行时才会受控吸收 `sync_scope.full.json` 中的 node scope 模板；candidate relationship scope templates 仍然只作为审查清单存在，运行时不得自动吸收。
- `MIRROR_STREAM_ID`：由 `.env` 提供给 `STREAM_ID` 的上游 live stream 标识；在真实运行时必须替换占位值，在测试设计阶段只用于固定配置边界。
- `BOOTSTRAP_START_AT`：显式 bootstrap 启动锚点；为空时 mirror-sync 使用产品默认近一年窗口，非空时允许共享环境测试把初始扫描收窄到指定起点之后。
- `MIRROR_BOOTSTRAP_LOOKBACK_DAYS`：未指定 `BOOTSTRAP_START_AT` 时的默认 bootstrap 回看窗口天数；当前契约默认值为 `365`，代表产品默认近一年范围。
- `MIRROR_POLL_INTERVAL_SECONDS`：mirror-sync 主循环的轮询或检查间隔；当前默认值为 `15` 秒，用于控制增量检查与运行时刷新频率。

### 4.2 副本同步暴露的稳定接口

- 以独立容器服务运行、采用 connector-like deployment shape 的同步入口；部署形态可以表现为 connector 风格服务，但稳定实现边界继续收口在 `mirror-sync/`。
- 以 OpenCTI live stream 或增量拉取为输入的同步入口。
- 以 Neo4j 热子图、watermark、新鲜度状态、删除或失效对齐为输出的同步边界。
- 允许保留产品默认近一年 bootstrap 窗口，同时允许通过显式 bootstrap 启动锚点缩小真实环境验收测试的初始扫描范围；测试覆盖不得通过缩小产品默认窗口替代该锚点。
- 只负责副本写入与 freshness 维护，不暴露 Agent 查询接口。

### 4.3 查询后端暴露的稳定接口

- 面向 Agent 的图查询与受控 Cypher 执行入口。
- 面向 Agent 的裁剪后 schema 视图、`investigation_id` 会话语义、预算策略和结构化拒绝原因。
- 查询后端只能依赖副本读模型与同步状态，不得直接依赖 OpenCTI 或静默回退到 GraphQL 翻译路径。

### 4.4 集成扩展暴露的稳定接口

- 容器 build context 与容器入口文件。
- 通过 OpenCTI connector helper 与外部数据源交互的适配边界。

### 4.5 运维脚本暴露的稳定接口

- `scripts/opencti-stack.ps1` 的 `Stop|Start|Restart|Up|Status` 动作。
- `scripts/backup-opencti.ps1` 的备份入口。
- `scripts/restore-opencti.ps1` 的恢复入口。

### 4.6 验证护栏暴露的稳定接口

- 当前 connector 显性 testcase 的唯一主入口：`tests/test_architecture_connector_support.py`。
- mirror-sync 全量 schema introspection 显性 testcase 的唯一主入口：`tests/test_full_scope_introspection_acceptance.py`。
- Neo4j mirror 最小链路显性 testcase 的唯一主入口：`tests/mirror/test_neo4j_sync_integrity.py`。
- Neo4j mirror 时间窗与邻域显性 testcase 的固定主入口：`tests/mirror/test_bootstrap_window_acceptance.py`。
- Neo4j mirror 增量与恢复显性 testcase 的固定主入口：`tests/mirror/test_live_incremental_acceptance.py`。
- Neo4j mirror 属性投影显性 testcase 的固定主入口：`tests/mirror/test_projection_policy_acceptance.py`。
- Neo4j mirror 删除与修复显性 testcase 的固定主入口：`tests/mirror/test_reconcile_acceptance.py`。
- 查询后端显性 testcase 的唯一主入口：`tests/query_backend/test_query_backend_acceptance.py`。
- 关键非显性测试入口：`tests/test_architecture_contracts.py`、`tests/test_acceptance_baselines.py`、`tests/test_dependency_boundaries.py`、`tests/test_implementation_traceability.py`。

## 5. 依赖方向

全局依赖方向固定为：验证护栏、运维脚本、集成扩展、副本同步、查询后端 单向依赖 运行时平台契约；查询后端允许依赖副本同步暴露的读模型与 freshness 状态契约，但不得反向依赖 OpenCTI 或测试内部实现。运行时平台允许为 `query-backend` 提供容器 build、统一反向代理入口、只读 freshness 绑定与 `.env` 只读挂载，但这些交付细节不得反向侵入 `query-backend/` 的查询语义契约。

必须满足：

- `tests/` 可以只读读取根契约、局部契约、意图图谱、compose、配置与脚本文件，但不得成为运行时平台、副本同步或查询后端的反向依赖。
- `scripts/` 只能操作 Docker Compose 与备份元数据，不得读取或驱动 connector 源码内部流程，也不得成为副本同步或查询后端的内部依赖。
- `connectors/automotive-security-timeline/` 只能依赖 OpenCTI connector helper、标准库与第三方库，不得依赖 `tests/` 或 `scripts/`。
- `mirror-sync/` 只能向下依赖 OpenCTI、Neo4j、副本配置与自身局部契约，不得依赖 `tests/`、`scripts/` 或 `query-backend/` 的内部实现；其容器交付由运行时平台显式承载，但不改变职责归属。
- `query-backend/` 只能向下依赖副本读模型、schema 视图、freshness 状态、标准库与第三方库，不得直接依赖 OpenCTI、GraphQL 翻译路径、`tests/` 或 `scripts/` 的内部实现。
- `tests/mirror/` 的显性验收与支撑夹具只能通过真实 OpenCTI 行为建立场景，并通过真实副本结果做只读断言；不得直接 import 或调用 `mirror-sync/` 内部同步实现来伪造副本写入。

## 6. implements 追溯

### 6.1 直接实现意图元素的稳定实现元素

| 意图元素 / testcase | 直接实现元素 | 说明 |
| --- | --- | --- |
| `MITRE ATT&CK数据接入` 至 `MISP Intel接入` 这些 connector 显性 testcase | 运行时平台 + `tests/test_architecture_connector_support.py` | 仓库中的直接承载是 compose 服务定义、`.env` 配置入口与现有显性 pytest 主入口 |
| `OpenCTI 平台全量元素关系属性覆盖盘点` | `tests/test_full_scope_introspection_acceptance.py` | 通过 live OpenCTI GraphQL introspection 校验 `mirror-sync/runtime/full_scope_introspection.json` 覆盖当前平台的 schema 元素、关系与属性 |
| `OpenCTIToNeo4jMirrorSync` | `mirror-sync/` | 本阶段为同步职责建立独立稳定边界，后续编码阶段在该边界内补齐 live stream、增量拉取、对账与删除对齐实现 |
| `ReplicaGraphQueryBackend` | `query-backend/` | 本阶段为后端查询与受控执行建立独立稳定边界，后续编码阶段在该边界内补齐查询 API、schema 视图、预算与审计实现 |
| `AIAgentGraphInvestigation` | `query-backend/` | 调查会话、结构化反馈和人机共审输出边界由查询后端直接承载 |
| `OpenCTI 情报数据镜像至 Neo4j 完整性验证` | `tests/mirror/test_neo4j_sync_integrity.py` | 显性入口已物理化并冻结其保护基线，作为最小链路存在性验证保留 |
| `近一年窗口热子图初始化同步` 与 `二跳邻域补齐完整性` | `tests/mirror/test_bootstrap_window_acceptance.py` | 时间窗与 2 跳补齐显性入口已物理化，后续编码阶段必须直接满足该入口 |
| `Live Stream 增量实时同步` 与 `Watermark 恢复后幂等补偿` | `tests/mirror/test_live_incremental_acceptance.py` | 增量与恢复显性入口已物理化，后续编码阶段不得迁移到其他入口 |
| `属性名称与默认基线投影一致性` | `tests/mirror/test_projection_policy_acceptance.py` | 属性投影显性入口已物理化，后续编码阶段必须直接满足字段名与基线约束 |
| `删除与撤销状态对齐` | `tests/mirror/test_reconcile_acceptance.py` | 删除对齐与修复显性入口已物理化，后续编码阶段不得改写为仅 upsert 语义 |
| `ReplicaGraphQueryBackend` 与 `AIAgentGraphInvestigation` 的正常成功路径规格 | `tests/query_backend/test_query_backend_acceptance.py::test_successful_query_returns_graph_payload_and_freshness_metadata` | 查询后端显性入口现在同时冻结成功路径的结果载荷与 freshness 元数据，不再只覆盖异常路径 |
| `受控 Cypher 拒绝与结构化反馈` | `tests/query_backend/test_query_backend_acceptance.py::test_controlled_cypher_rejection_returns_structured_feedback` | 本阶段先把查询后端显性入口物理化并冻结保护基线，后续编码阶段不得迁移入口 |
| `副本降级不静默回退` | `tests/query_backend/test_query_backend_acceptance.py::test_replica_degradation_does_not_fall_back_silently` | 本阶段先把降级语义显性入口物理化并冻结保护基线，后续编码阶段不得改写为 GraphQL 回退 |
| `Docker统一代理查询入口可用性验证` | `tests/query_backend/test_query_backend_docker_acceptance.py::test_docker_proxy_entry_preserves_structured_rejection_contract` | 统一 HTTPS 反向代理入口下的容器化查询路径单独冻结为显性入口，后续编码阶段不得把该入口降级为非代理或非容器路径 |

### 6.2 通过实现链间接承载意图元素的稳定实现元素

- `mirror-sync/` 通过写入 Neo4j 热子图与 freshness 状态，间接承载 `ReplicaGraphQueryBackend` 的可查询前提。
- 运行时平台通过 `docker-compose.yml` 中的 `query-backend` 独立容器服务、`.env.sample` 与 `.env` 配置入口、`Caddyfile` 中的统一反向代理规则和只读运行时绑定，间接承载 `ReplicaGraphQueryBackend` 与 `AIAgentGraphInvestigation` 的容器化交付前提。
- `scripts/` 通过维护运行时平台生命周期、备份与恢复，间接承载 connector、mirror 与 query backend 显性 testcase 的可执行环境。
- `tests/test_architecture_contracts.py`、`tests/test_acceptance_baselines.py`、`tests/test_dependency_boundaries.py`、`tests/test_implementation_traceability.py` 通过守住根契约、局部契约、入口定位和依赖方向，间接承载全部显性 testcase 的只读验收基线。
- `connectors/automotive-security-timeline/` 是当前仓库内的自研扩展能力，但在当前意图图谱中未见对应显性 testcase，因此仅作为实现侧稳定扩展元素存在，不强行直连意图层。

## 7. 显性 testcase 入口

当前显性 testcase 物理入口固定如下：

- connector 类显性 testcase 继续只读收口在 `tests/test_architecture_connector_support.py`，后续编码阶段只能补齐运行时与实现，不得拆分、迁移或重命名该入口。
- mirror-sync 全量 schema introspection 显性 testcase 固定落在 `tests/test_full_scope_introspection_acceptance.py`，后续编码阶段必须直接维护该入口对 live OpenCTI schema 与 `mirror-sync/runtime/full_scope_introspection.json` 的覆盖校验。
- Neo4j mirror 最小链路显性 testcase 固定落在 `tests/mirror/test_neo4j_sync_integrity.py`，后续编码阶段必须直接调用该文件，不得重定向到其他入口。
- Neo4j mirror 时间窗与邻域显性 testcase 固定落在 `tests/mirror/test_bootstrap_window_acceptance.py`，其中“近一年窗口热子图初始化同步”与“二跳邻域补齐完整性”分别对应单一测试函数入口。
- Neo4j mirror 增量与恢复显性 testcase 固定落在 `tests/mirror/test_live_incremental_acceptance.py`，其中“Live Stream 增量实时同步”与“Watermark 恢复后幂等补偿”分别对应单一测试函数入口。
- Neo4j mirror 属性投影显性 testcase 固定落在 `tests/mirror/test_projection_policy_acceptance.py`。
- Neo4j mirror 删除与修复显性 testcase 固定落在 `tests/mirror/test_reconcile_acceptance.py`。
- Neo4j mirror 真实环境验收允许通过显式 `BOOTSTRAP_START_AT` 一类启动锚点把 bootstrap 范围限制到测试启动附近的窄时间窗；该机制只用于测试覆盖与共享环境降噪，不改变产品默认近一年语义。
- 查询后端 API 契约显性 testcase 固定落在 `tests/query_backend/test_query_backend_acceptance.py`，其中正常成功路径、“受控 Cypher 拒绝与结构化反馈”与“副本降级不静默回退”分别对应单一测试函数入口，后续编码阶段必须直接调用而不是重建入口。
- 查询后端 Docker 统一代理显性 testcase 固定落在 `tests/query_backend/test_query_backend_docker_acceptance.py`，后续编码阶段必须直接通过统一代理入口满足该入口，而不是把它回退成本机直连或辅助脚本。
- 查询后端 API 契约显性 testcase 的装配固定由 `tests/query_backend/conftest.py` 负责优先对接已运行的容器化健康实例；只有在显式环境变量缺位或降级实例不存在时，才允许为测试期补位独立实例。

## 8. 关键非显性测试

本阶段冻结下列关键非显性测试；后续 `/work` 阶段不得修改其入口、断言边界、挂载对象、追溯关系与受保护基线：

| 类别 | 冻结入口 | 守护目标 |
| --- | --- | --- |
| 架构边界 | `tests/test_architecture_contracts.py` | 根契约、局部契约、共享骨架与根契约引用关系 |
| 显性入口正确性 | `tests/test_acceptance_baselines.py` | 意图层 acceptanceCriteria 或根契约声明的显性入口与实际物理入口的一致性 |
| 依赖方向 | `tests/test_dependency_boundaries.py` | `tests/`、`scripts/`、`connectors/`、`mirror-sync/`、`query-backend/` 的稳定依赖方向，以及 query-backend 统一外部入口只能经 Caddy 暴露、内部仍不得反向依赖 OpenCTI |
| 关键实现追溯 | `tests/test_implementation_traceability.py` | `mirror-sync/`、`query-backend/`、`tests/mirror/`、`tests/query_backend/` 与意图元素、显性 testcase 的实现链可追溯性，以及运行时平台对 query-backend 的间接交付链 |
| 显性入口冻结 | `tests/mirror/test_neo4j_sync_integrity.py` + `tests/mirror/protected_*` | mirror 显性入口、保护夹具与保护基线的存在性与查询断言边界 |
| 显性入口冻结 | `tests/mirror/test_bootstrap_window_acceptance.py` + `tests/mirror/protected_fixtures/bootstrap_window_probe.md` + `tests/mirror/protected_baselines/bootstrap_window_contract.md` | 时间窗与 2 跳补齐显性入口、保护夹具与保护基线的存在性与范围断言边界 |
| 显性入口冻结 | `tests/mirror/test_live_incremental_acceptance.py` + `tests/mirror/protected_fixtures/live_incremental_probe.md` + `tests/mirror/protected_baselines/live_incremental_contract.md` | 增量与恢复显性入口、保护夹具与保护基线的存在性与恢复断言边界 |
| 显性入口冻结 | `tests/mirror/test_projection_policy_acceptance.py` + `tests/mirror/protected_fixtures/projection_policy_probe.md` + `tests/mirror/protected_baselines/projection_policy_contract.md` | 属性投影显性入口、保护夹具与保护基线的存在性与字段名断言边界 |
| 显性入口冻结 | `tests/mirror/test_reconcile_acceptance.py` + `tests/mirror/protected_fixtures/reconcile_probe.md` + `tests/mirror/protected_baselines/reconcile_contract.md` | 删除与修复显性入口、保护夹具与保护基线的存在性与对齐断言边界 |
| 依赖方向 | `tests/test_dependency_boundaries.py` | mirror 测试不得直接调用同步实现、mirror-sync 保持 connector-like 部署而不迁移职责、真实环境验收允许 bootstrap 启动锚点而不改变产品默认窗口 |
| 显性入口冻结 | `tests/query_backend/test_query_backend_acceptance.py` + `tests/query_backend/protected_fixtures/rejected_cypher_and_degraded_probe.md` + `tests/query_backend/protected_baselines/response_contract.md` | query backend API 契约显性入口、保护夹具与保护基线的存在性与成功/拒绝/降级断言边界 |
| 显性入口冻结 | `tests/query_backend/test_query_backend_docker_acceptance.py` + `tests/query_backend/protected_fixtures/docker_proxy_probe.md` + `tests/query_backend/protected_baselines/docker_proxy_contract.md` | query backend Docker 统一代理显性入口、保护夹具与保护基线的存在性与代理路径断言边界 |

## 9. 普通非显性测试

普通非显性测试作为后续编码阶段的支撑护栏，允许在契约规定的位置补充：

- 已创建：`connectors/automotive-security-timeline/tests/test_support_guardrails.py`
- 已保留：`tests/runtime/restore-validation/` 下的运行时恢复基线可继续作为后续 restore 类支撑测试挂载点
- 预留给后续编码阶段：`mirror-sync/tests/` 下的增量同步、watermark、删除或 tombstone、reconcile 支撑测试
- 已保留：`query-backend/tests/test_server_support.py` 作为本地支撑护栏，覆盖只读 Cypher 分类与降级响应结构
- 预留给后续编码阶段：`query-backend/tests/` 下的容器启动冒烟、健康探针、审计日志、schema 视图、预算策略、响应元数据与调查会话支撑测试

## 10. 保护对象

下列对象在当前阶段冻结为只读架构基线：

- `tests/test_architecture_connector_support.py`
- `tests/test_full_scope_introspection_acceptance.py`
- `tests/mirror/test_neo4j_sync_integrity.py`
- `tests/mirror/protected_fixtures/manual_seed_steps.md`
- `tests/mirror/protected_baselines/cypher_assertions.md`
- `tests/mirror/test_bootstrap_window_acceptance.py`
- `tests/mirror/test_live_incremental_acceptance.py`
- `tests/mirror/test_projection_policy_acceptance.py`
- `tests/mirror/test_reconcile_acceptance.py`
- `tests/mirror/protected_fixtures/bootstrap_window_probe.md`
- `tests/mirror/protected_fixtures/live_incremental_probe.md`
- `tests/mirror/protected_fixtures/projection_policy_probe.md`
- `tests/mirror/protected_fixtures/reconcile_probe.md`
- `tests/mirror/protected_baselines/bootstrap_window_contract.md`
- `tests/mirror/protected_baselines/live_incremental_contract.md`
- `tests/mirror/protected_baselines/projection_policy_contract.md`
- `tests/mirror/protected_baselines/reconcile_contract.md`
- `tests/query_backend/test_query_backend_acceptance.py`
- `tests/query_backend/test_query_backend_docker_acceptance.py`
- `tests/query_backend/protected_fixtures/rejected_cypher_and_degraded_probe.md`
- `tests/query_backend/protected_fixtures/docker_proxy_probe.md`
- `tests/query_backend/protected_baselines/response_contract.md`
- `tests/query_backend/protected_baselines/docker_proxy_contract.md`
- `tests/test_architecture_contracts.py`
- `tests/test_acceptance_baselines.py`
- `tests/test_dependency_boundaries.py`
- `tests/test_implementation_traceability.py`
- `mirror-sync/Dockerfile`
- `mirror-sync/service.py`
- `query-backend/Dockerfile`

## 11. 变更规则

- 新增稳定实现元素时，必须先更新本文件，再创建对应目录与 `ARCHITECTURE.md`。
- 局部契约可以补充本地职责、接口与测试挂载点，但不得重复定义根级规则。
- `mirror-sync/` 与 `query-backend/` 的实现细节只能在各自边界内扩展，不得互相吞并为浅层模块集合。
- 任何 future mirror 或 query backend 实现都必须声明自己满足既有显性入口，而不是改写 `tests/mirror/` 或 `tests/query_backend/` 的冻结入口。
- 若副本同步以 connector 风格容器服务交付，必须保持 `mirror-sync/` 作为稳定实现边界，禁止仅因部署形态变化把同步职责重命名或迁移为 `connectors/` 下的普通接入扩展。