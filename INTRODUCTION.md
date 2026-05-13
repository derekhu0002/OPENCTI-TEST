# OPENCTI-TEST 对外说明文档

## 产品概述

### 一句话定位

这是一个基于 Docker Compose 交付的本地化 OpenCTI 威胁情报平台集成工程，用于搭建可运行的威胁情报采集、存储、检索、关系建模与连接器编排环境。

### 解决的问题

根据仓库中的 Compose、配置、测试和架构图谱，这个项目主要解决以下问题：

- 为团队提供一个可直接运行的 OpenCTI 平台环境，而不是只提供零散的 OpenCTI 配置片段。
- 将威胁情报连接器、平台基础设施、访问入口、备份脚本和验证测试收敛到同一工作区中，降低落地成本。
- 让外部情报源和自定义连接器能够通过统一的容器运行方式接入 OpenCTI。
- 让部署结果可以通过架构图谱与测试脚本验证，而不是停留在文档描述层。

### 适用对象

更适合以下类型的团队：

- 想快速落地 OpenCTI 本地环境的安全运营、威胁情报或研判团队。
- 需要把多个情报连接器统一运行、统一管理、统一验证的集成团队。
- 想在现有 OpenCTI 环境上增加自定义连接器能力的开发团队。
- 需要把“架构声明”和“真实运行验证”绑定在一起的工程团队。

### 典型场景

- 本地或内网搭建威胁情报分析平台。
- 通过 MITRE、ThreatFox、CISA KEV、Ransomware.live 等源自动导入情报。
- 对接 MISP 或厂商情报源，作为后续扩展能力。
- 运行自定义的 Automotive Security Timeline 连接器，将特定垂直领域情报导入 OpenCTI。

### 对外判断

如实基于仓库内容判断，这个项目更像“面向内部部署和集成的产品化工程交付仓库”，而不是一个提供独立开放 API、SDK、SaaS 控制台或多租户能力的通用开放平台。外部团队应把它视为“可运行系统交付件”，而不是“轻量 API 服务”。

## 功能清单

### 1. OpenCTI 平台运行环境

业务价值：提供统一的威胁情报实体、关系和分析平台，作为所有连接器和数据流程的承载核心。

仓库证据：

- `docker-compose.yml` 定义了 `opencti` 服务。
- `README.md` 明确说明该仓库构建的是本地 OpenCTI threat-intelligence system。

### 2. 基础设施服务编排

业务价值：提供运行 OpenCTI 所需的消息队列、对象存储、缓存和索引能力，降低部署碎片化风险。

包含组件：

- Redis
- Elasticsearch
- MinIO
- RabbitMQ
- Caddy

仓库证据：

- `docker-compose.yml` 中存在 `redis`、`elasticsearch`、`minio`、`rabbitmq`、`caddy` 服务。
- `Caddyfile` 将 `https://localhost` 反向代理到 `opencti:8080`。

### 3. OpenCTI 内置连接器能力

业务价值：覆盖文件导入、文件导出、文档解析和分析等基础平台操作。

包含组件：

- Export File STIX
- Export File CSV
- Export File TXT
- Import File STIX
- Import Document
- Import Document Analysis

仓库证据：

- `docker-compose.yml` 中存在以上 `connector-*` 服务定义。

### 4. 外部威胁情报连接器能力

业务价值：将外部公共或厂商情报源接入 OpenCTI，构成可持续更新的情报输入面。

当前已建模并落地的外部连接器包括：

- MITRE ATT&CK
- NIST NVD CVE
- Google Threat Intelligence (GTI)
- CrowdStrike Falcon Intelligence
- Ransomware.live
- CISA Known Exploited Vulnerabilities (KEV)
- Mandiant
- ThreatFox
- MISP Intel

仓库证据：

- `design/KG/SystemArchitecture.json` 的 `ApplicationLayer` 元素与 testcase 描述。
- `docker-compose.yml` 与 `docker-compose.opensearch.yml` 中对应的连接器服务定义。
- `tests/test_architecture_connector_support.py` 中的连接器验收规格与真实容器覆盖逻辑。

### 5. 自定义行业连接器能力

业务价值：证明该项目不仅能运行官方连接器，也可以承载自定义领域连接器。

当前可证实的自定义连接器：

- Automotive Security Timeline

根据现有代码推断，这个连接器会从汽车安全时间线数据源抓取事件，并通过 `pycti` 写入 OpenCTI。

仓库证据：

- `docker-compose.yml` 中的 `connector-automotive-security-timeline`。
- `connectors/automotive-security-timeline/src/main.py` 中使用 `OpenCTIConnectorHelper` 构造连接器配置，并请求外部 Timeline 数据源。

### 6. 连接器编排与管理能力

业务价值：为连接器生命周期管理预留统一编排入口。

仓库中已证实存在：

- `xtm-composer` 容器

根据现有代码推断，它用于连接器管理或编排，但仓库中未明确说明它的完整对外使用手册、命令集合或 UI 使用方式，因此不应把这部分包装成已完整文档化的产品能力。

仓库证据：

- `docker-compose.yml` 中的 `xtm-composer` 服务定义。

### 7. 运维与数据保护能力

业务价值：提供无损停启和备份脚本，降低本地部署运行风险。

已证实功能：

- 无损 Stop / Start / Restart / Up / Status
- 数据卷备份与元数据备份
- 备份前预演 `-WhatIf`

仓库证据：

- `scripts/opencti-stack.ps1`
- `scripts/backup-opencti.ps1`
- `README.md` 的使用说明

### 8. 架构一致性与运行验证能力

业务价值：不仅描述系统，而且通过测试验证架构声明和运行状态一致。

已证实能力：

- 校验架构图谱中的 testcase 与仓库文件是否一致。
- 对部分连接器执行真实 Docker 启动覆盖。
- 对 MISP Intel 等复杂运行场景执行测试期环境构建。

仓库证据：

- `design/KG/SystemArchitecture.json`
- `tests/test_architecture_connector_support.py`

## 接口与集成点

## 1. Web 访问入口

已证实：

- 通过 `https://localhost` 暴露 OpenCTI。

仓库证据：

- `Caddyfile`
- `.env.sample`
- `README.md`

## 2. GraphQL 接口

已证实：

- 仓库中的测试代码会调用 `OPENCTI_BASE_URL/graphql`。

根据现有代码推断：

- 对外系统级接口的核心入口之一是 OpenCTI 自身 GraphQL API，而不是该仓库额外实现的独立 API 服务。

仓库证据：

- `tests/test_architecture_connector_support.py` 中 `_graphql_request()` 会向 `/graphql` 发起请求。

## 3. CLI / 脚本入口

已证实入口：

- `docker compose up -d`
- `powershell -ExecutionPolicy Bypass -File .\scripts\opencti-stack.ps1 -Action ...`
- `powershell -ExecutionPolicy Bypass -File .\scripts\backup-opencti.ps1`
- `python -m pytest tests/test_architecture_connector_support.py -vv`

仓库证据：

- `README.md`
- `scripts/opencti-stack.ps1`
- `scripts/backup-opencti.ps1`

## 4. 配置入口

已证实配置入口：

- `.env`
- `.env.sample`
- `docker-compose.yml`
- `docker-compose.opensearch.yml`
- `docker-compose.misp-test.yml`
- `Caddyfile`
- `rabbitmq.conf`

用途包括：

- 平台基础配置
- 管理员账号配置
- Docker Compose profile 启用
- 连接器 ID 与运行参数配置
- 反向代理配置
- MISP 测试栈配置

## 5. 架构图谱入口

已证实：

- 系统用 `design/KG/SystemArchitecture.json` 作为架构声明与 testcase 绑定文件。

业务意义：

- 它不是纯展示文件，还参与测试验证和交付一致性校验。

## 6. 测试入口

已证实：

- `tests/test_architecture_connector_support.py` 是主要验收入口。
- `tests/query_backend/test_query_backend_acceptance.py` 是查询后端接口契约的显性验收入口。

业务意义：

- 外部采用方可以用它快速验证“仓库声明的能力是否真的可以跑起来”。
- 对查询后端而言，显性入口同时冻结了正常成功、结构化拒绝和副本降级三类响应规格。

## 7. VS Code 扩展命令

仓库中未明确说明：

- 没有找到 VS Code 扩展 `package.json`。
- 没有发现 `contributes.commands`、扩展激活入口或命令清单。

因此不应把本仓库描述为“VS Code 扩展产品”或“提供 VS Code 命令面板接口”的项目。

## 8. npm / Node.js 包入口

仓库中未明确说明：

- 工作区内未找到 `package.json`。

因此不应把该项目描述为一个可通过 `npm install` 使用的 Node.js SDK、CLI 或扩展包。

## 9. 外部依赖

已证实依赖：

- Docker / Docker Compose
- OpenCTI upstream platform and connectors images
- Redis
- Elasticsearch
- MinIO
- RabbitMQ
- Python / pytest（用于验证）

根据现有代码推断，某些连接器还依赖各自上游服务或密钥，例如 MISP、NVD、Google TI、CrowdStrike、Mandiant，但仓库并没有提供这些第三方服务本身。

## 10. 查询后端接口契约

已证实：

- 实现架构已经为独立查询后端定义了稳定边界，见 `query-backend/ARCHITECTURE.md`。
- 当前唯一已冻结的调用接口是 `POST /graph/query`。
- 当前仓库已经交付最小可运行查询后端实现，入口为 `query-backend/server.py`，外部接口说明见 `query-backend/API.md`。
- 当前仓库尚未把该后端接入 compose 编排，因此默认运行方式是直接启动 Python HTTP 服务。

仓库证据：

- `query-backend/ARCHITECTURE.md`
- `tests/query_backend/test_query_backend_acceptance.py`
- `tests/query_backend/protected_fixtures/rejected_cypher_and_degraded_probe.md`
- `tests/query_backend/protected_baselines/response_contract.md`

### 10.1 接口定义

当前冻结的接口入口：

- 方法：`POST`
- 路径：`/graph/query`
- 认证：可选 `Authorization: Bearer <token>`
- 载荷类型：`application/json`

当前已冻结的请求字段：

- `investigation_id`：调查会话标识，用于串联一次调查中的多次查询和审计链路。
- `cypher`：调用方提交的只读图查询或待后端裁决的 Cypher。

当前已冻结的响应字段：

- 成功或降级路径共同需要的元数据：`backend`、`investigation_id`、`freshness_ts`、`staleness_seconds`、`sync_status`
- 成功路径需要的结果载荷：`results`
- 拒绝路径需要的控制元数据：`rejection_reason`、`budget_policy`
- 可选结果裁剪标记：`result_truncated`

### 10.2 成功响应规格

当副本可用且新鲜度处于允许范围时，查询后端必须：

- 返回 `backend=neo4j-replica`
- 原样返回调用方提交的 `investigation_id`
- 返回 `freshness_ts`、`staleness_seconds`、`sync_status`
- 返回机器可消费的 `results` 列表
- 不返回 `rejection_reason`

当前推荐把 `results` 设计为“结果项数组”，每个结果项对应一次 Cypher 返回记录，至少应满足以下格式约束：

- `results` 顶层必须是数组。
- 数组中的每一项必须是对象，而不是裸字符串或位置敏感数组。
- 每个结果项建议按返回语义显式命名字段，例如 `nodes`、`relationships`、`paths`、`metrics`、`evidence`。
- 当查询返回节点或关系时，建议保留稳定标识字段，例如 `standard_id`、内部追踪 ID、类型标签和关键属性，避免只返回展示文本。
- 当查询返回路径或子图时，建议把节点集合和关系集合拆开返回，而不是把整段路径压成不可解析字符串。

推荐的成功响应结果项格式示例：

```json
{
	"backend": "neo4j-replica",
	"investigation_id": "case-2026-05-13-001",
	"freshness_ts": "2026-05-13T08:00:00Z",
	"staleness_seconds": 42,
	"sync_status": "healthy",
	"results": [
		{
			"nodes": [
				{
					"entity_type": "ipv4-addr",
					"standard_id": "ipv4-addr--11111111-2222-3333-4444-555555555555",
					"id": "opencti--aaaa-bbbb-cccc",
					"value": "1.2.3.4"
				},
				{
					"entity_type": "malware",
					"standard_id": "malware--99999999-8888-7777-6666-555555555555",
					"id": "opencti--dddd-eeee-ffff",
					"name": "Mirai-Botnet"
				}
			],
			"relationships": [
				{
					"relationship_type": "indicates",
					"source_standard_id": "ipv4-addr--11111111-2222-3333-4444-555555555555",
					"target_standard_id": "malware--99999999-8888-7777-6666-555555555555"
				}
			],
			"evidence": {
				"summary": "IPv4 observable indicates Mirai-Botnet in the current replica view."
			}
		}
	],
	"result_truncated": false
}
```

如果调用方只需要聚合结果而不是子图明细，也应保持对象结构稳定，例如：

```json
{
	"backend": "neo4j-replica",
	"investigation_id": "case-2026-05-13-001",
	"freshness_ts": "2026-05-13T08:00:00Z",
	"staleness_seconds": 42,
	"sync_status": "healthy",
	"results": [
		{
			"metrics": {
				"match_count": 17,
				"relationship_count": 24
			}
		}
	]
}
```

### 10.3 拒绝响应规格

当调用方提交写操作、越界 schema 访问或明显超预算特征的 Cypher 时，查询后端必须：

- 不在副本上执行该请求
- 返回结构化 `rejection_reason`
- 返回本次裁决使用的 `budget_policy`
- 返回本次请求关联的 `investigation_id`

### 10.4 降级响应规格

当副本不可达、同步故障或新鲜度超阈值时，查询后端必须：

- 返回 `backend=neo4j-replica`
- 返回 `freshness_ts`、`staleness_seconds`、`sync_status`
- 不得静默回退到 GraphQL 翻译路径并伪装为成功结果

### 10.5 调用示例

请求示例：

```http
POST /graph/query
Content-Type: application/json
Authorization: Bearer <token>

{
	"investigation_id": "case-2026-05-13-001",
	"cypher": "MATCH (n) RETURN n LIMIT 1"
}
```

成功响应示例：

```json
{
	"backend": "neo4j-replica",
	"investigation_id": "case-2026-05-13-001",
	"freshness_ts": "2026-05-13T08:00:00Z",
	"staleness_seconds": 0,
	"sync_status": "healthy",
	"results": [
		{
			"value": "1.2.3.4",
			"standard_id": "ipv4-addr--7dd44d27-f473-5ba9-b12b-0d3a61bbed2e"
		}
	],
	"result_truncated": false
}
```

当前实现把 `results` 返回为“按 Cypher 返回列名映射后的记录对象数组”。调用方可以基于稳定列名继续做图遍历、证据提取或人工复核，不应假定这里只有自然语言摘要。

拒绝响应示例：

```json
{
	"backend": "neo4j-replica",
	"investigation_id": "case-2026-05-13-001",
	"rejection_reason": "write_operation_not_allowed",
	"budget_policy": "readonly-default"
}
```

降级响应示例：

```json
{
	"backend": "neo4j-replica",
	"investigation_id": "case-2026-05-13-001",
	"freshness_ts": "2026-05-13T07:52:00Z",
	"staleness_seconds": 960,
	"sync_status": "stale"
}
```

## 调用与使用方法

### 1. 运行前置条件

至少需要：

- 可用的 Docker daemon
- Docker Compose
- 能读取和修改 `.env` 的本地权限
- 如需运行验收测试，还需要 Python 和 pytest 环境

对部分能力还需要：

- 有效的第三方服务凭据或终端，例如 MISP、NVD 或厂商 API

### 2. 最小使用步骤

最小接入路径如下：

1. 基于 `.env.sample` 准备 `.env`
2. 校对 `OPENCTI_BASE_URL`、`OPENCTI_ADMIN_EMAIL`、`OPENCTI_ADMIN_PASSWORD`、`OPENCTI_ADMIN_TOKEN` 等核心配置
3. 执行 `docker compose up -d`
4. 访问 `https://localhost`
5. 用 `.env` 中的管理员账号登录 OpenCTI
6. 如需验证交付质量，再执行 pytest 验收套件

### 3. 连接器使用路径

默认随系统启动的能力：

- `threat-intel-connectors` profile 中的默认连接器集合

需要显式启用的能力：

- `connector-misp-intel`

显式启动方式：

```powershell
docker compose --profile misp-intel up -d connector-misp-intel
```

### 4. 停启与备份路径

无损停启：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\opencti-stack.ps1 -Action Stop
powershell -ExecutionPolicy Bypass -File .\scripts\opencti-stack.ps1 -Action Start
powershell -ExecutionPolicy Bypass -File .\scripts\opencti-stack.ps1 -Action Restart
```

备份：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup-opencti.ps1
```

备份预演：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup-opencti.ps1 -WhatIf
```

### 5. 验证路径

最直接的验收路径：

```powershell
d:/Projects/OPENCTI-TEST/.venv/Scripts/python.exe -m pytest tests/test_architecture_connector_support.py -vv
```

查询后端显性验收路径：

```powershell
d:/Projects/OPENCTI-TEST/.venv/Scripts/python.exe -m pytest tests/query_backend/test_query_backend_acceptance.py -vv
```

这条路径适合外部采用方在接入前验证：

- 架构图谱是否与运行配置一致
- 关键连接器是否已在仓库中落地
- 部分连接器是否能达到真实容器运行覆盖
- 查询后端是否满足成功、结构化拒绝和副本降级三类冻结响应规格

### 6. 查询后端调用方关键流程

以下流程描述的是当前已经在实现架构、显性测试和最小运行时代码中对齐的调用方式。默认启动入口为 `query-backend/server.py`，更细的接口字段见 `query-backend/API.md`。

补充说明：

- 对外运行时入口仍然是直接启动 `query-backend/server.py`。
- 查询后端显性验收 `tests/query_backend/test_query_backend_acceptance.py` 现在会在测试期自动装配真实的健康实例和降级实例；当默认端口已被其他本地进程占用时，测试会自动切换到空闲端口，而不是要求调用方手工设置 `QUERY_BACKEND_DEGRADED_BASE_URL`。

最小启动示例：

```powershell
d:/Projects/OPENCTI-TEST/.venv/Scripts/python.exe query-backend/server.py
```

默认监听地址：

- `http://127.0.0.1:8088/graph/query`
- 通过环境变量 `QUERY_BACKEND_HOST`、`QUERY_BACKEND_PORT`、`QUERY_BACKEND_SYNC_STATUS`、`QUERY_BACKEND_STALENESS_SECONDS` 调整监听地址和降级模拟状态

#### 成功查询流程

1. 调用方向 `POST /graph/query` 发送只读 Cypher 和 `investigation_id`。
2. 查询后端使用副本读模型和 freshness 状态进行执行前校验。
3. 若副本健康且查询被允许执行，后端返回 `results`、`freshness_ts`、`staleness_seconds` 和 `sync_status`。
4. 调用方继续消费 `results`，并把 `investigation_id` 作为后续多次查询的统一会话标识。

#### 拒绝查询流程

1. 调用方向 `POST /graph/query` 发送包含写操作或越界特征的 Cypher。
2. 查询后端在执行前进行只读、schema 白名单和预算裁决。
3. 后端拒绝执行，并返回结构化 `rejection_reason` 与 `budget_policy`。
4. 调用方根据拒绝原因修正查询，而不是假定后端会自动改写 Cypher。

#### 副本降级流程

1. 调用方向 `POST /graph/query` 发送需要图遍历的查询。
2. 查询后端在执行前发现副本不可达、同步故障或 freshness 超阈值。
3. 后端返回 `freshness_ts`、`staleness_seconds`、`sync_status` 等降级元数据。
4. 调用方根据降级状态决定等待、缩小范围或终止调查，而不是把返回结果当作等价成功。

#### 调用方最小接入注意事项

- 调用方必须自行生成并稳定传递 `investigation_id`。
- 调用方不应直接持有 Neo4j 凭证，也不应绕过后端直连副本。
- 调用方必须区分成功、拒绝、降级三种路径，不能把所有 `200/非200` 响应简单折叠成“成功/失败”二元模型。
- 调用方应把 freshness 元数据纳入结果消费逻辑，而不是忽略副本时效性。

## 评估采用时应关注的约束

### 1. 运行环境约束

- 这是 Docker Compose 部署形态，不是无状态单二进制程序。
- 依赖多种基础设施组件联合运行。
- 更适合本地、测试、实验室或受控内网环境。

仓库中未明确说明：

- Kubernetes 生产部署方案
- 高可用方案
- 多节点扩容策略
- SLA / SLO / 容灾等级

### 2. 第三方依赖约束

- 某些连接器即使能启动，也未必能在没有真实凭据时拉到有效数据。
- `connector-cve` 当前可以在空 key 下保持容器运行，但没有真实 NVD key 时只能完成启动覆盖，不能视为已具备完整数据接入能力。
- `connector-misp-intel` 需要真实 MISP 端点与 live stream 条件，默认不会自动启用。

### 3. 产品边界约束

根据现有代码推断，该项目更偏“可运行的集成工程与部署仓库”，而不是：

- 通用 SaaS 产品
- 面向第三方开发者的独立 SDK
- 已完整产品化的多租户平台
- 已文档化的开放 API 网关

### 4. 适合集成方式

更适合：

- 作为本地或私有化 OpenCTI 交付底座
- 作为威胁情报集成试验平台
- 作为连接器开发和运行验证环境

不太适合：

- 只想消费一个轻量 HTTP API 的外部系统
- 不接受 Docker 多组件依赖的团队
- 需要现成商业级多租户控制面的采购场景

### 5. 不适用场景

- 只需要单一脚本或 SDK 的项目
- 没有 Docker 运维能力的纯业务团队
- 需要仓库直接提供完整云托管服务说明的场景

## 证据来源

以下关键结论可以直接从仓库中找到依据：

- 系统是 OpenCTI Docker Compose 平台：`README.md`、`docker-compose.yml`
- HTTPS 本地入口是 `https://localhost`：`README.md`、`Caddyfile`、`.env.sample`
- 默认 profile 为 `threat-intel-connectors`：`.env.sample`
- MISP Intel 需要单独 profile：`docker-compose.yml`、`README.md`、`tests/test_architecture_connector_support.py`
- CVE 在空 key 下通过 fallback 保持容器启动：`docker-compose.yml`、`docker-compose.opensearch.yml`、`tests/test_architecture_connector_support.py`、`design/KG/SystemArchitecture.json`
- 自定义 Automotive Security Timeline 连接器存在且使用 `pycti`：`docker-compose.yml`、`connectors/automotive-security-timeline/src/main.py`
- 备份脚本与无损停启脚本存在：`scripts/backup-opencti.ps1`、`scripts/opencti-stack.ps1`
- GraphQL 被仓库测试直接调用：`tests/test_architecture_connector_support.py`
- 架构图谱参与能力声明与 testcase 绑定：`design/KG/SystemArchitecture.json`
- 主要验收入口为 Python pytest：`tests/test_architecture_connector_support.py`
- 仓库中未找到 `package.json`：工作区文件搜索结果为空

## 快速结论

### 谁应该使用它

- 需要本地或私有化部署 OpenCTI 的安全团队
- 需要统一运行多个威胁情报连接器的集成团队
- 需要验证自定义连接器接入能力的工程团队
- 需要“架构图谱 + 真实测试覆盖”交付方式的研发团队

### 谁不适合使用它

- 只想拿一个现成公开 API 或 SDK 的外部调用方
- 不具备 Docker / Compose 运维能力的团队
- 需要多租户 SaaS、托管服务、商业 SLA 的采购方
- 不接受多组件基础设施依赖的轻量化接入场景

### 最小接入路径是什么

1. 用 `.env.sample` 准备 `.env`
2. 执行 `docker compose up -d`
3. 访问 `https://localhost`
4. 用 `.env` 中的管理员账号登录 OpenCTI
5. 如需验证交付质量，再执行 pytest 验收套件
6. 如需验证查询后端契约，再执行 `tests/query_backend/test_query_backend_acceptance.py`

### 采用前最需要验证的 3 个风险点是什么

1. 基础设施承载风险：目标环境是否能稳定运行 OpenCTI + Redis + Elasticsearch + MinIO + RabbitMQ + 多个连接器。
2. 第三方源可用性风险：是否具备真实的厂商 API key、MISP 端点、外部网络访问条件，否则部分连接器只能启动不能产出有效数据。
3. 产品边界风险：团队是否接受这是一套“部署与集成工程交付仓库”，而不是一个已完整抽象成开放 API / SaaS 的通用产品。