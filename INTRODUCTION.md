# OPENCTI-TEST 对外产品说明

本文仅基于以下架构来源编写：

- `design/KG/SystemArchitecture.json`
- `OVERALL_ARCHITECTURE.md`
- 各稳定目录下的 `ARCHITECTURE.md`

本文面向外部调用方、潜在采用方与集成方，重点回答三件事：这个产品值不值得采用、如何开始接入、采用前需要满足什么前提。

## 先判断是否适合采用

如果你的目标是下面这类需求，这个产品值得优先评估：

- 你已经有 OpenCTI，希望在主源之外建立一个只读的 Neo4j 热子图副本，用于高级图查询、路径分析和调查式探索。
- 你希望远端 AI Agent 不直接拿到 Neo4j 凭证，而是通过统一后端入口执行受控查询，并拿到结构化拒绝、预算约束和新鲜度状态。
- 你需要把外部威胁情报源持续接入 OpenCTI，并用统一运行时方式管理这些接入能力。
- 你希望采用后可以通过固定验收入口验证“副本是否可用”“查询入口是否可用”“统一代理是否保留结构化拒绝契约”。

如果你的目标是下面这些，这个产品当前不适合直接采用：

- 需要一个新的主数据源或写入型图数据库平台。该产品明确把 OpenCTI 视为权威主源，Neo4j 副本只用于只读分析。
- 需要让外部 Agent 直接连接 Neo4j。架构明确要求 Agent 通过查询后端访问副本，而不是直接持有 Neo4j 访问凭证。
- 需要在副本不可用时自动无感切回不等价的 GraphQL 路径。架构明确禁止静默回退。
- 需要完整历史全量镜像且不接受时间窗边界。当前默认初始化语义是近一年窗口，并补齐两跳邻域，虽然可配置，但架构没有把“全量全历史副本”定义为默认产品语义。
- 无法提供 Docker/Compose 运行环境、OpenCTI 运行时、Neo4j 副本依赖和基础配置入口。

## 如何开始使用

最小开始方式如下：

1. 准备运行前提：Docker daemon、Docker Compose、OpenCTI 运行时、Neo4j、副本同步容器、查询后端容器、统一 HTTPS 代理，以及用于验证的 Python 和 pytest。
2. 在根目录配置运行时入口：`.env` 或 `.env.sample` 对应的环境变量边界，重点是 OpenCTI、Neo4j、副本同步、查询后端相关变量。
3. 启动运行时平台：使用 `scripts/opencti-stack.ps1` 的 `Up`、`Start` 或 `Restart` 动作，或按运行时平台合同装配 compose 服务。
4. 先验证副本最小链路，再验证查询入口：
   - `python -m pytest tests/mirror/test_neo4j_sync_integrity.py -q`
   - `python -m pytest tests/query_backend/test_query_backend_acceptance.py -q`
   - `python -m pytest tests/query_backend/test_query_backend_docker_acceptance.py -q`
5. 通过统一外部入口接入查询能力：`POST https://localhost/graph/query`。

如果你只想用最小路径判断能否采用，不需要先覆盖全部 connector；先把 OpenCTI、Neo4j 副本、mirror-sync、query-backend 和统一代理跑通即可。

如果当前调用方还在使用 OpenCTI 自带的 GraphQL 接口，可以把它理解为“主源访问路径”而不是本文新增产品能力的替代物：

- 当你的目标是继续围绕 OpenCTI 主源做对象读取、维护既有系统对接或复用现有调用链时，仍可保留现有 GraphQL 接入方式。
- 当你的目标转为面向远端 AI Agent 的调查式图探索、多跳遍历、受控 Cypher、结构化拒绝和副本 freshness 判断时，应优先接入本文的统一查询入口，而不是依赖 GraphQL 侧等价替代。
- 架构已经明确：查询后端不能在副本异常时静默回退到 GraphQL 路径，因此两者应被视为不同边界、不同语义的访问面。

## 产品概述

一句话定位：这是一个围绕 OpenCTI 构建的“只读 Neo4j 分析副本 + 统一受控查询后端 + 外部情报接入运行时”的产品化组合。

它解决的问题是：把 OpenCTI 作为权威主源保留下来，同时为远端 AI Agent 和分析场景提供更适合图探索、路径分析和结构化审计的只读图副本与统一查询入口，并通过运行时平台承载外部威胁情报接入能力。

适用对象包括：

- 需要在 OpenCTI 之上增加图分析能力的安全团队
- 需要给远端 AI Agent 提供受控图查询能力的集成方
- 需要把多种威胁情报源接入 OpenCTI 的平台团队
- 需要在采用前通过固定验收路径判断系统是否可落地的技术评估方

典型场景包括：

- 远端 AI Agent 发起调查式图查询，由后端统一裁决是否执行、是否拒绝、以及当前副本是否足够新鲜
- 通过 OpenCTI live stream 和增量拉取，把近一年内的热点实体与关系同步到 Neo4j 热子图副本
- 对副本执行删除、撤销、失效和漂移修复对账，保持分析结果与主源一致
- 接入官方或自研情报源，把外部数据持续导入 OpenCTI

## 功能清单

### 1. 运行时平台能力

- 统一承载 OpenCTI、Neo4j、副本同步、查询后端、connector profile 和统一 HTTPS 代理入口。
- 通过根目录 compose 与配置文件提供稳定运行时装配边界。
- 对外收口运行前提、容器服务名、profile 和环境变量边界。

### 2. OpenCTI 到 Neo4j 副本同步能力

- 默认按近一年时间窗进行初始化同步。
- 默认补齐命中对象两跳邻域内的实体与关系，并保持关系方向语义。
- 以 live stream 为优先同步路径，以增量拉取作为补偿路径。
- 维护 freshness 状态和 watermark。
- 提供周期性 reconcile/repair，用于修复漏同步、漏删除、脏边和状态漂移。
- 将物理删除、逻辑删除、撤销和失效状态同步到副本侧。
- 保持属性名称与 OpenCTI 字段名一致，并保留默认基线字段。

### 3. 统一查询后端能力

- 面向远端 AI Agent 提供图查询与受控 Cypher 执行入口。
- 只允许访问副本读模型，不直接依赖 OpenCTI。
- 提供裁剪后 schema 视图、调查会话语义和 `investigation_id` 上下文。
- 提供预算控制、审计与结构化拒绝。
- 在副本不可安全使用时返回降级状态或结构化反馈，而不是静默切换到不等价路径。

### 4. 外部情报接入与富化能力

意图架构当前明确列出的外部情报接入或富化点包括：

- MITRE ATT&CK
- NIST NVD CVE
- Google Threat Intelligence (GTI)
- CrowdStrike Falcon Intelligence
- Ransomware.live
- CISA Known Exploited Vulnerabilities (KEV)
- Mandiant
- ThreatFox
- Kaspersky Enrichment
- VirusTotal
- 自研 `Automotive Security Timeline` connector

其中，架构能明确证明的能力边界是：这些集成点由运行时平台承载，目标是把外部数据导入或富化到 OpenCTI；但并不是所有集成点都在当前允许来源中冻结了同等粒度的外部参数细节。

### 5. 运维与验证能力

- 提供统一的生命周期脚本入口。
- 提供备份和恢复入口。
- 提供固定显性验收入口，用于验证 connector 运行时定义、副本同步完整性、查询契约和统一代理路径。

## 接口、集成点与配置入口

### A. 对外调用接口

#### 1. 统一查询入口

**用途**

- 为远端 AI Agent 提供统一图查询入口。
- 承载受控 Cypher 执行、结构化拒绝、预算信息和 freshness 信息。

**调用方式**

- 固定通过统一 HTTPS 代理入口调用：`POST https://localhost/graph/query`
- 架构明确该入口由 Caddy 反向代理到查询后端容器。

**输入参数边界**

- Agent 图查询请求
- 受控 Cypher
- 调查会话上下文
- `investigation_id`
- 调用认证 token

说明：允许来源已经证明这些输入边界存在，但没有把完整请求报文字段名、Header 名称和 JSON 契约逐项冻结下来。因此接入时应以“必须携带调查上下文和查询语义”为准，而不要假设未在架构中出现的字段。

**所有可能输出**

- 成功结果：返回机器可消费的图结果，以及 `freshness_ts`、`staleness_seconds`、`sync_status` 等 freshness 元数据。
- 结构化拒绝：返回 `rejection_reason`、适用的 `budget_policy`，以及必要的纠正线索；对应查询不会在副本上执行。
- 副本降级：返回明确的降级状态、freshness 信息或同步异常状态；不会静默伪装成成功，也不会静默回退到 GraphQL 翻译路径。

**约束**

- 只读访问副本，不是 OpenCTI 写入接口。
- 不保证副本不可用时仍返回等价成功结果。
- 统一代理入口下，结构化拒绝语义必须保持不变，不能被包装成普通网络错误。

**示例**

- 最小操作路径：向 `https://localhost/graph/query` 发送一个带 `investigation_id` 和 Cypher 查询语义的请求。
- 期望结果只有三类：成功、结构化拒绝、明确降级。

#### 2. 生命周期运维入口

**入口**

- `scripts/opencti-stack.ps1`

**用途**

- 控制整套运行时平台的生命周期。

**输入参数**

- `Stop`
- `Start`
- `Restart`
- `Up`
- `Status`

**所有可能输出**

- 停止、启动、重启、拉起或状态查询对应的运行时结果。

**调用方式**

- 通过 PowerShell 调用该脚本，并传入上面的动作之一。

**约束**

- 该入口是运维入口，不是业务接口。
- 它依赖 Docker CLI、Compose 项目目录与根级运行时配置。

**示例**

- 以 `Up` 启动整套平台。
- 以 `Status` 检查平台状态。

#### 3. 备份与恢复入口

**入口**

- `scripts/backup-opencti.ps1`
- `scripts/restore-opencti.ps1`

**用途**

- 分别触发备份与恢复操作。

**输入参数边界**

- 当前允许来源只冻结了“备份入口”和“恢复入口”的存在性，没有展开更多稳定参数。

**所有可能输出**

- 备份执行结果或恢复执行结果，以及对应的运行时/元数据影响。

**调用方式**

- 通过 PowerShell 调用对应脚本。

**约束**

- 依赖备份目录元数据和运行时平台。
- 不应被当作业务数据导入接口使用。

### B. 外部集成点

#### 1. OpenCTI 主源集成

**用途**

- 作为权威主源，承接外部情报导入、自研 connector 输出以及副本同步的上游数据源。

**输入参数/配置入口**

- `OPENCTI_URL`
- `OPENCTI_TOKEN`
- OpenCTI HTTPS 入口
- 管理员 token 配置边界

**输出**

- 为副本同步提供 live stream、增量拉取和主源数据。
- 接收 connector 发送的 STIX bundle 或情报导入结果。

**调用方式**

- 作为运行时平台的一部分，与副本同步和 connector 通过运行时装配边界集成。

**约束**

- 它是主源，不是副本的下游缓存替代品。

#### 1.1 关于当前仍在使用的 GraphQL 接口

**如何理解它在本产品中的位置**

- 当前架构明确保留 OpenCTI 的 HTTPS 主源入口，因此如果你的现有系统已经接入 OpenCTI GraphQL，可以继续把它作为主源访问面使用。
- 但 GraphQL 不是本文新增“统一查询入口”的同义替代。本文新增的查询能力是建立在 Neo4j 只读副本之上的独立后端边界，面向的是远端 AI Agent 的图探索与受控 Cypher 执行。

**适合继续使用 GraphQL 的场景**

- 你已经有现成的 OpenCTI 主源对接链路，短期目标只是延续现有调用方式。
- 你的调用重点仍然是围绕 OpenCTI 主源对象访问，而不是副本侧的图探索能力。

**更适合切到统一查询入口的场景**

- 需要多跳图查询、路径分析或探索式调查。
- 需要后端对查询进行只读约束、预算控制、审计和结构化拒绝。
- 需要根据副本 freshness 或降级状态决定是否继续调查。

**约束**

- 当前允许来源没有冻结 OpenCTI GraphQL 的具体外部路径、字段级契约或示例请求，因此本文不扩写这些细节。
- 可以确认的是：GraphQL 属于 OpenCTI 主源访问面；查询后端属于副本访问面；两者不应被混同，也不应假设查询后端会在内部自动改走 GraphQL。

#### 2. Neo4j 副本集成

**用途**

- 作为只读热子图副本，为查询后端提供读模型。

**输入参数/配置入口**

- `NEO4J_ADVERTISED_HOST`
- `NEO4J_HTTP_PORT`
- `NEO4J_BOLT_PORT`
- `NEO4J_PASSWORD`
- `NEO4J_MIRROR_HTTP_HOST`
- `NEO4J_MIRROR_HTTP_PORT`
- `NEO4J_MIRROR_USERNAME`
- `NEO4J_MIRROR_PASSWORD`

**输出**

- 只读图副本
- freshness 状态
- watermark
- 删除/撤销/失效对齐后的分析读模型

**调用方式**

- 由副本同步写入，由查询后端只读访问。

**约束**

- 对外推荐通过查询后端使用，不推荐把 Neo4j 作为外部 Agent 的直连接口。

#### 3. mirror-sync 运行时集成点

**用途**

- 把 OpenCTI 中近一年热点子图及后续变动同步到 Neo4j 副本。

**输入参数/配置入口**

- `OPENCTI_URL`
- `OPENCTI_TOKEN`
- `STREAM_ID`
- `MIRROR_STREAM_ID`（作为 `STREAM_ID` 的上游 live stream 标识）
- `BOOTSTRAP_START_AT`
- `MIRROR_BOOTSTRAP_LOOKBACK_DAYS`
- `MIRROR_POLL_INTERVAL_SECONDS`
- `NEO4J_MIRROR_HTTP_HOST`
- `NEO4J_MIRROR_HTTP_PORT`
- `NEO4J_MIRROR_USERNAME`
- `NEO4J_MIRROR_PASSWORD`
- `mirror-sync/runtime` 持久化运行时目录

**输出**

- Neo4j 热子图副本
- freshness 状态
- watermark
- 对账修复结果
- 删除或失效对齐状态

**调用方式**

- 作为独立容器服务运行。

**约束**

- 优先路径是 live stream，补偿路径是 incremental pull，修复路径是 reconcile。
- `BOOTSTRAP_START_AT` 可以缩小真实环境验收时的初始化扫描范围，但不改变产品默认近一年语义。

**示例**

- 评估时最小配置只需要先把 OpenCTI 连接信息、Neo4j 连接信息、stream 标识和 bootstrap/freshness 相关变量补齐，然后启动 mirror-sync。

#### 4. 官方与自研 connector 集成点

下表只列出当前允许来源中可以证明的集成点、用途、已冻结配置边界和输出边界。未在架构来源中冻结的参数，不在此处臆造。

| 集成点 | 用途 | 已证实输入参数/配置入口 | 已证实输出 | 调用方式 | 约束与说明 |
| --- | --- | --- | --- | --- | --- |
| MITRE ATT&CK | 向 OpenCTI 导入 MITRE Enterprise、Mobile、ICS 矩阵及相关实体 | 已证实存在运行时服务定义；允许来源未冻结具体变量名 | 导入工具、恶意软件、活动、攻击模式、缓解措施及 MITRE 专用框架对象 | 作为运行时平台中的 connector 服务启用 | 当前文档只能确认有该集成能力和运行时承载，不扩写未冻结参数 |
| NIST NVD CVE | 按计划导入 CVE 漏洞数据 | `CONNECTOR_CVE_ID`、`CVE_INTERVAL`、`CVE_API_KEY` | 转换为 STIX2 后导入 OpenCTI 的漏洞情报 | 作为运行时平台中的 connector 服务启用 | 真实运行依赖 NVD API Key |
| Google Threat Intelligence (GTI) | 导入报告、位置、行业、恶意软件、入侵集合、攻击模式、漏洞和原始 IOC | `CONNECTOR_GOOGLE_TI_FEEDS_ID`、`GOOGLE_TI_FEEDS_INTERVAL`、`GOOGLE_TI_FEEDS_API_KEY` | 结构化威胁情报导入 OpenCTI | 作为运行时平台中的 connector 服务启用 | 运行时需 GTI API Key |
| CrowdStrike Falcon Intelligence | 导入威胁行为体、指标、报告、YARA 等情报 | `CONNECTOR_CROWDSTRIKE_ID`、`CROWDSTRIKE_FALCON_INTERVAL`、`CROWDSTRIKE_FALCON_BASE_URL`、`CROWDSTRIKE_FALCON_CLIENT_ID`、`CROWDSTRIKE_FALCON_CLIENT_SECRET` | 情报导入 OpenCTI | 作为运行时平台中的 connector 服务启用 | 运行时需 CrowdStrike 凭据 |
| Ransomware.live | 导入勒索软件活动、团伙声明和受害者相关情报 | 已证实存在运行时服务定义；允许来源未冻结具体变量名 | 勒索软件相关建模与跟踪数据导入 OpenCTI | 作为运行时平台中的 connector 服务启用 | 架构已记录上游 `https://www.ransomware.live/v2/groups` 可能返回 `404`；该已知外部错误不等于本产品运行时失败 |
| CISA KEV | 导入已知被利用漏洞及相关 Identity、Infrastructure、Vulnerability 对象 | 已证实存在运行时服务定义；允许来源未冻结具体变量名 | 已知被利用漏洞情报导入 OpenCTI | 作为运行时平台中的 connector 服务启用 | 当前文档不扩写未冻结变量 |
| Mandiant | 导入行为体、恶意软件家族、活动、漏洞、IOC 与分析报告 | `CONNECTOR_MANDIANT_ID`、`MANDIANT_IMPORT_INTERVAL`、`MANDIANT_API_V4_KEY_ID`、`MANDIANT_API_V4_KEY_SECRET` | 综合威胁情报导入 OpenCTI | 作为运行时平台中的 connector 服务启用 | 运行时需 Mandiant API V4 凭据 |
| ThreatFox | 导入 IOC 与 Malware，覆盖 `file-md5`、`file-sha1`、`file-sha256`、`ipv4-addr`、`domain-name`、`url` | 已证实存在运行时服务定义；允许来源未冻结具体变量名 | IOC 与 Malware 数据导入 OpenCTI | 作为运行时平台中的 connector 服务启用 | 当前文档不扩写未冻结变量 |
| Kaspersky Enrichment | 对观测对象做威胁情报富化 | 已证实存在该富化能力；允许来源未冻结具体变量名 | 当前明确支持文件类 observable 富化 | 作为 OpenCTI 富化 connector 集成 | 架构明确说明当前只支持文件 observable，IP、域名、URL 支持属于未来扩展 |
| VirusTotal | 导入文件和 URL 的分析结果 | 已证实存在该富化能力；允许来源未冻结具体变量名 | 文件与 URL 分析结果导入 OpenCTI | 作为 OpenCTI 富化 connector 集成 | 当前文档只确认该能力存在，不补写未冻结参数 |
| Automotive Security Timeline | 从 Automotive Security Timeline 源拉取数据并发送 STIX bundle 到 OpenCTI | `OPENCTI_URL`、`OPENCTI_TOKEN`、`CONNECTOR_ID`、`CONNECTOR_DURATION_PERIOD`、`AUTOMOTIVE_TIMELINE_SOURCE_URL`、`AUTOMOTIVE_TIMELINE_VERIFY_TLS`、`AUTOMOTIVE_TIMELINE_REQUEST_TIMEOUT` | 向 OpenCTI 发送 STIX bundle | 作为自研 connector 集成到运行时平台 | 这是当前仓库唯一在局部合同中明确的自研 connector |

### C. 配置入口

#### 1. 根级运行时配置入口

| 配置入口 | 用途 | 说明 |
| --- | --- | --- |
| `.env` | 主运行时配置入口 | 承载 OpenCTI、Neo4j、副本同步、查询后端与部分 connector 的变量边界 |
| `.env.sample` | 配置模板入口 | 用于初始化环境变量边界 |
| `docker-compose.yml` | 主 compose 运行时入口 | 承载默认运行时服务定义 |
| `docker-compose.opensearch.yml` | 运行时变体入口 | 用于特定运行时变体 |
| `docker-compose.misp-test.yml` | MISP 测试变体入口 | 仅能确认这是运行时平台定义的一种变体入口 |
| `Caddyfile` | 统一 HTTPS 代理配置入口 | 把 `https://localhost/graph/query` 反向代理到查询后端 |
| `rabbitmq.conf` | 运行时基础配置入口 | 属于根级稳定运行时配置的一部分 |

#### 2. 查询后端配置入口

- `QUERY_BACKEND_HOST`
- `QUERY_BACKEND_PORT`
- `QUERY_BACKEND_AUDIT_LOG`
- `NEO4J_MIRROR_HTTP_HOST`
- `NEO4J_MIRROR_HTTP_PORT`
- `NEO4J_MIRROR_USERNAME`
- `NEO4J_MIRROR_PASSWORD`

作用：控制查询后端监听地址、审计输出，以及其对副本读模型的访问边界。

#### 3. 副本同步配置入口

- `OPENCTI_URL`
- `OPENCTI_TOKEN`
- `STREAM_ID`
- `MIRROR_STREAM_ID`
- `BOOTSTRAP_START_AT`
- `MIRROR_BOOTSTRAP_LOOKBACK_DAYS`
- `MIRROR_POLL_INTERVAL_SECONDS`
- `NEO4J_MIRROR_HTTP_HOST`
- `NEO4J_MIRROR_HTTP_PORT`
- `NEO4J_MIRROR_USERNAME`
- `NEO4J_MIRROR_PASSWORD`

作用：控制 OpenCTI 上游接入、bootstrap 起点、默认回看窗口、轮询间隔和 Neo4j 副本连接。

## 调用与使用方法

### 安装与运行前置条件

- 需要 Docker daemon 和 Docker Compose。
- 需要 OpenCTI 运行时。
- 需要 Neo4j 副本依赖。
- 需要统一 HTTPS 代理入口。
- 需要 Python 与 pytest，以运行架构冻结的验收入口。
- 如果采用外部情报 connector，还需要视集成点提供相应 API Key 或凭据。允许来源中已明确需要凭据的至少包括 NVD、GTI、CrowdStrike、Mandiant。

### 最小使用步骤

1. 用 `.env` 或 `.env.sample` 补齐最小配置：OpenCTI 连接信息、Neo4j 副本连接信息、mirror-sync 变量、query-backend 变量。
2. 启动运行时平台。
3. 确认 mirror-sync 已开始把 OpenCTI 数据写入 Neo4j 副本。
4. 运行最小链路验收，验证副本与查询能力：
   - `python -m pytest tests/mirror/test_neo4j_sync_integrity.py -q`
   - `python -m pytest tests/query_backend/test_query_backend_acceptance.py -q`
5. 通过 `POST https://localhost/graph/query` 接入统一查询能力。

### 调用示例或操作路径

#### 示例 1：最小查询接入路径

1. 启动运行时平台。
2. 准备一个带 `investigation_id` 的查询请求。
3. 通过 `POST https://localhost/graph/query` 发起调用。
4. 判断返回属于成功、结构化拒绝还是副本降级。

#### 示例 2：最小副本可用性验证路径

1. 启动 OpenCTI、Neo4j、副本同步。
2. 运行 `python -m pytest tests/mirror/test_neo4j_sync_integrity.py -q`。
3. 只要该入口通过，就表示最小“OpenCTI -> Neo4j 副本”链路成立。

#### 示例 3：最小统一代理验证路径

1. 启动查询后端与统一 HTTPS 代理。
2. 运行 `python -m pytest tests/query_backend/test_query_backend_docker_acceptance.py -q`。
3. 通过后表示 Docker 代理入口能够保留结构化拒绝契约。

## 评估采用时应关注的约束

### 运行环境与依赖组件

- 该产品不是单进程工具，而是运行时平台组合。
- 采用至少需要 OpenCTI、Neo4j、副本同步、查询后端、统一 HTTPS 代理和基础运行时配置。
- 验收和采用评估依赖 Python/pytest；如果没有这套验证链，就无法按当前架构合同完成可验证采用。

### 当前局限

- 只读副本不是主数据治理面，也不是写接口。
- 查询后端不承诺在副本异常时提供等价成功回退。
- 默认初始化语义是近一年窗口和两跳邻域，不应把它理解为默认全量历史镜像。
- Kaspersky Enrichment 当前只明确支持文件 observable 富化。
- 并非所有 connector 都在当前允许来源中冻结了同样详细的外部参数边界；因此可证明的是“存在该集成能力与运行时承载”，不是“所有部署参数都已在本文中固定”。

### 适合集成方式

- 作为现有 OpenCTI 平台旁路的只读分析与查询能力采用。
- 让远端 AI Agent 只接入统一查询后端，而不直连 Neo4j。
- 把外部情报导入能力作为运行时平台中的受控 connector 集启用。

### 不适用场景

- 需要直接把该产品当作 OpenCTI 替代品。
- 需要对外暴露未受控的 Neo4j 直连访问。
- 需要副本异常时无感切换到其他不等价查询路径。
- 需要脱离 Docker/Compose 与稳定运行时配置入口的轻量化部署模型。

## 运行验证方式

当前架构已经冻结了外部团队最有价值的几条验证路径：

- connector 运行时定义验证：`python -m pytest tests/test_architecture_connector_support.py -q`
- 副本最小链路验证：`python -m pytest tests/mirror/test_neo4j_sync_integrity.py -q`
- 初始化时间窗与两跳邻域验证：`python -m pytest tests/mirror/test_bootstrap_window_acceptance.py -q`
- 增量同步与 watermark 恢复验证：`python -m pytest tests/mirror/test_live_incremental_acceptance.py -q`
- 属性投影一致性验证：`python -m pytest tests/mirror/test_projection_policy_acceptance.py -q`
- 删除/撤销对齐验证：`python -m pytest tests/mirror/test_reconcile_acceptance.py -q`
- 查询后端成功/拒绝/降级契约验证：`python -m pytest tests/query_backend/test_query_backend_acceptance.py -q`
- Docker 统一代理入口验证：`python -m pytest tests/query_backend/test_query_backend_docker_acceptance.py -q`

对外评估建议至少跑通其中三条：副本最小链路、查询后端契约、Docker 统一代理入口。这样就能判断这个产品是否已经满足“可接入、可验证、可受控”的最小采用标准。

## 最小接入路径

最小接入路径是：

1. 准备 OpenCTI、Neo4j、Docker Compose、Caddy 代理、Python/pytest。
2. 在 `.env` 中至少补齐 `OPENCTI_URL`、`OPENCTI_TOKEN`、`MIRROR_STREAM_ID` 或 `STREAM_ID`、`NEO4J_MIRROR_HTTP_HOST`、`NEO4J_MIRROR_HTTP_PORT`、`NEO4J_MIRROR_USERNAME`、`NEO4J_MIRROR_PASSWORD`、`QUERY_BACKEND_HOST`、`QUERY_BACKEND_PORT`。
3. 启动运行时平台，并确保 mirror-sync 与 query-backend 已装配。
4. 先运行 `python -m pytest tests/mirror/test_neo4j_sync_integrity.py -q`，再运行 `python -m pytest tests/query_backend/test_query_backend_acceptance.py -q`。
5. 通过 `POST https://localhost/graph/query` 开始接入统一查询能力。

如果这五步都成立，就说明你已经完成该产品的最小采用闭环：主源存在、只读副本存在、统一查询入口存在、验证路径存在。
