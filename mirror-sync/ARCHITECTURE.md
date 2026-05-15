# mirror-sync 局部契约

## 1. 角色

本目录承载 OpenCTI 到 Neo4j 热子图副本的同步实现边界，只负责副本写入、新鲜度与对账，不承载 Agent 查询入口。

## 2. 作用域

本契约覆盖 `mirror-sync/` 目录作为稳定实现元素的职责边界，以及后续在本目录下新增的实现与 `tests/` 挂载点。

参考根契约：`../OVERALL_ARCHITECTURE.md`

## 3. 稳定元素

- `mirror-sync/`：承载同步入口、watermark、新鲜度状态与删除对齐的稳定目录边界；即使运行时以 connector-like 容器服务部署，稳定实现归属仍留在本目录。
- `Dockerfile`：mirror-sync 容器化交付边界。
- `service.py`：mirror-sync 容器入口与运行时主循环边界。
- `runtime/full_scope_introspection.json`：当前 OpenCTI 平台 live GraphQL schema 的全量 introspection 快照，用于盘点 mirror-sync 可扩展的元素、关系与属性覆盖面。
- `sync_scope.json`：mirror-sync 节点与关系 scope 的只读实现契约，声明节点/关系 scope 的启用状态、GraphQL 字段、字段选择、节点与关系投影、搜索补全与 bootstrap 策略；运行时按该文件内容计算配置摘要，若容器重启时摘要变化，则对当前启用 scope 重新执行 bootstrap 窗口回放以补齐新增元素或属性。当前契约同时允许用显式布尔开关一次性启用 `sync_scope.full.json` 中的全部 candidate node scopes。
- `sync_scope.full.json`：基于 live OpenCTI GraphQL introspection 生成的备用候选目录，用于枚举当前 OpenCTI 可进一步纳入的 query field / node scope 模板；默认仍是扩容盘点资料，不单独替代 `sync_scope.json` 的运行时契约地位；只有 `sync_scope.json` 显式启用全量 candidate node scope 开关时，运行时才会受控吸收其中的 node scope 模板。
- `tests/`：后续编码阶段用于挂载同步支撑护栏的默认位置，不是显性 testcase 主入口。

## 4. 接口边界

- 输入边界：OpenCTI live stream、增量拉取能力、主 compose 默认网络中的 `opencti`/`neo4j` 服务，以及 `.env` 中的 `MIRROR_*` 与 Neo4j 连接变量。
- 容器运行时通过 `OPENCTI_URL`、`OPENCTI_TOKEN`、`STREAM_ID`、`BOOTSTRAP_START_AT`、`MIRROR_BOOTSTRAP_LOOKBACK_DAYS` 与 `MIRROR_POLL_INTERVAL_SECONDS` 收口流订阅、bootstrap 与轮询配置。
- 节点与关系同步范围通过 `sync_scope.json` 只读收口；当前版本允许声明节点 scope 的 `enabled`、`graphql_field`、`selection`、`projection`、`search` 与 `bootstrap_mode`，以及关系 scope 的 `bootstrap_mode`、source、participants、via relationship、投影关系、两跳 neighborhood 补全与命名回退规则。若 `sync_scope.json` 显式开启全量 candidate node scope 开关，则运行时在保留本地显式 scope 优先级的前提下，把 `sync_scope.full.json` 中的 candidate node scopes 追加为启用状态。
- `.env` 中 `MIRROR_STREAM_ID` 负责为 `STREAM_ID` 提供上游 live stream 标识；占位值只用于配置物理化，不代表已完成真实运行时装配。
- `.env` 中 `BOOTSTRAP_START_AT` 用于显式指定 bootstrap 起点；测试夹具可在共享环境中临时写入该锚点对应的时间语义，但不得借此改写产品默认近一年策略。
- `.env` 中 `MIRROR_BOOTSTRAP_LOOKBACK_DAYS` 用于声明未显式给出启动锚点时的默认回看范围；当前默认值为 `365` 天。
- `.env` 中 `MIRROR_POLL_INTERVAL_SECONDS` 用于声明 mirror-sync 容器主循环的轮询间隔；当前默认值为 `15` 秒。
- 输入边界允许声明两类 bootstrap 配置：产品默认近一年窗口，以及用于真实环境验收降噪的显式 bootstrap 启动锚点；测试锚点只缩小初始扫描范围，不改写产品默认语义。
- 输出边界：Neo4j 热子图、副本 freshness 状态、watermark、对账结果与删除或失效对齐状态。
- 输出边界同时包括 `runtime/full_scope_introspection.json` 这类只读 schema 盘点产物；其职责是描述当前 OpenCTI 平台可配置覆盖面，不参与查询后端读路径。
- 本目录不得向 `query-backend/` 暴露 Agent 查询接口；它只暴露副本读模型与 freshness 契约。
- 若 `sync_scope.json` 缺失、结构非法、缺少 acceptance baseline 所需 scope，或试图禁用基线必需 scope，mirror-sync 必须在运行时显式失败，而不是静默降级或跳过 해당 scope。
- 若 `sync_scope.json` 在容器重启前后发生变化，mirror-sync 必须把该变化视为受控 bootstrap 触发条件，对当前启用 scope 自 bootstrap floor 重新回放，以补齐新增节点类型、关系类型或新增属性投影。
- 当前关系 scope 仍受控为固定 schema 的配置解释执行，不允许在 `sync_scope.json` 内嵌任意脚本、Cypher 或开放式 DSL。

### 4.1 正式生产启动清单

- 启动前必须确认 `docker-compose.yml` 中的 `mirror-sync` 服务与 `opencti`、`neo4j` 同属主 compose 默认网络，并继续通过该服务名部署，不单独发明旁路启动入口。
- 启动前必须确认 `.env` 中 `MIRROR_STREAM_ID` 已替换为真实可用的 OpenCTI live stream id；占位值或失效 stream id 不构成正式装配完成。
- 若要按产品默认近一年窗口执行首次 bootstrap，必须保证 `.env` 中 `BOOTSTRAP_START_AT` 为空，且 `mirror-sync/runtime/test_bootstrap_anchor.json` 不存在；否则运行时会把该测试锚点视为有效 bootstrap 起点。
- 若要在生产变更窗口中人为收窄首次 bootstrap 范围，必须显式填写 `.env` 中 `BOOTSTRAP_START_AT`，并把该时间点当作受控运维决策，而不是测试遗留副作用。
- `MIRROR_BOOTSTRAP_LOOKBACK_DAYS` 在未显式设置 `BOOTSTRAP_START_AT` 时保持默认 `365`；正式部署不得通过修改测试夹具文件来替代该配置边界。
- 启动命令固定为 `docker compose up -d mirror-sync`，或者在冷启动场景使用 `docker compose up -d opencti neo4j mirror-sync`；正式运行后由 compose 的 `restart: always` 负责常驻拉起。
- 启动后必须观察 `mirror-sync/runtime/freshness.json` 与 `mirror-sync/runtime/stream.watermark.json` 是否持续刷新；最小健康判据为 `sync_status` 为 `healthy`、`staleness_seconds` 为 `0` 或可接受小值、`last_poll_at` 持续推进。
- 启动后应以 `tests/mirror/test_neo4j_sync_integrity.py` 作为最小链路验收入口，验证 OpenCTI 写入后的代表性对象能在 Neo4j 副本中被只读查询到。
- 若生产环境曾执行过 mirror 验收测试，正式切换前必须审计并清理 `mirror-sync/runtime/` 下的测试锚点与仅测试期有意义的运行时残留，避免把共享环境的测试时间窗带入长期运行。

## 5. 依赖方向

- 允许依赖：OpenCTI、Neo4j、运行时平台契约、标准库与第三方库。
- 禁止依赖：`tests/`、`scripts/`、`query-backend/` 的内部实现。
- 测试目录不得反向以 import 方式调用本目录内部同步函数；真实环境验收只能通过 OpenCTI 侧刺激和副本侧只读观察来满足本边界。

## 6. implements 追溯

- 本目录直接 implements `OpenCTIToNeo4jMirrorSync`。
- 本目录通过产出副本读模型与 freshness 状态，间接承载 `ReplicaGraphQueryBackend` 与 `AIAgentGraphInvestigation`。
- 显性 testcase `OpenCTI 情报数据镜像至 Neo4j 完整性验证` 固定由 `../tests/mirror/test_neo4j_sync_integrity.py` 直接承载，本目录后续实现必须满足该入口而不是改写入口。
- 显性 testcase `OpenCTI 平台全量元素关系属性覆盖盘点` 固定由 `../tests/test_full_scope_introspection_acceptance.py` 直接承载，本目录后续实现必须保证 `runtime/full_scope_introspection.json` 持续覆盖当前 OpenCTI live schema。

## 7. 显性 testcase 入口

本目录无显性 testcase 主入口；与本目录相关的显性验收固定收口在 `../tests/test_full_scope_introspection_acceptance.py`、`../tests/mirror/test_neo4j_sync_integrity.py`、`../tests/mirror/test_bootstrap_window_acceptance.py`、`../tests/mirror/test_live_incremental_acceptance.py`、`../tests/mirror/test_projection_policy_acceptance.py` 与 `../tests/mirror/test_reconcile_acceptance.py`。

## 8. 关键非显性测试

- `../tests/test_architecture_contracts.py` 冻结本目录必须存在局部契约并沿用共享骨架。
- `../tests/test_dependency_boundaries.py` 冻结本目录只负责同步入口，不得向查询后端边界泄漏 Agent 查询职责。
- `../tests/test_dependency_boundaries.py` 同时冻结 mirror 测试不得直接 import 本目录内部同步实现，以及真实环境验收允许 bootstrap 启动锚点而不改写默认近一年窗口。
- `../tests/test_implementation_traceability.py` 冻结本目录与 `OpenCTIToNeo4jMirrorSync` 的直接实现关系。

## 9. 普通非显性测试

- 后续编码阶段默认在 `mirror-sync/tests/` 下补充增量同步、watermark、删除或 tombstone、reconcile 支撑测试。

## 10. 保护对象

- 本局部契约对 `OpenCTIToNeo4jMirrorSync` 的直接 implements 声明。
- `runtime/full_scope_introspection.json` 作为可配置覆盖面盘点基线的存在性。
- `../tests/mirror/test_neo4j_sync_integrity.py` 作为只读显性入口的挂载关系。

## 11. 变更规则

- 不得把查询后端、脚本或测试内部实现塞进本目录，避免把同步边界退化成多职责浅层模块。
- 若后续需要拆分子目录，只允许围绕同步职责分解，且不得改变显性 testcase 的挂载位置。
- 若后续以 connector 风格服务落地 compose，允许新增 Dockerfile、入口脚本与运行时配置，但不得因此把本目录的稳定职责迁移到 `connectors/`。
