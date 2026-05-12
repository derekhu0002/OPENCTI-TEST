# OPENCTI-TEST 实现架构总契约

## 1. 角色

本文件是工作区唯一的根级实现架构入口。它负责定义一级稳定实现元素、全局依赖方向、implements 追溯链、显性 testcase 的唯一物理入口，以及关键非显性测试冻结规则。

本版按推荐方案先行落盘为当前基线，后续若人类决策改变一级分层或接口边界，必须同步更新本文件与对应局部契约，而不是仅修改目录或测试实现。

## 2. 作用域

本契约覆盖下列稳定实现元素：

- 运行时平台：`.env`、`docker-compose.yml`、`docker-compose.opensearch.yml`、`docker-compose.misp-test.yml`、`Caddyfile`、`rabbitmq.conf`
- 集成扩展：`connectors/`
- 运维脚本：`scripts/`
- 验证护栏：`tests/`

本契约不把私有函数、普通 helper、机械拆分出来的文件级模块提升为稳定实现元素。

## 3. 稳定元素

### 3.1 一级稳定实现元素

| 一级元素 | 稳定职责 | 主要物理载体 | 局部契约 |
| --- | --- | --- | --- |
| 运行时平台 | 承载 OpenCTI、基础设施、connector profile 与容器化集成入口 | 根目录 compose 与配置文件 | 本文件直接管理 |
| 集成扩展 | 承载仓库自研扩展及其与运行时平台的稳定边界 | `connectors/` | `connectors/ARCHITECTURE.md` |
| 运维脚本 | 承载启动、停止、备份、恢复等稳定操作入口 | `scripts/` | `scripts/ARCHITECTURE.md` |
| 验证护栏 | 承载显性 testcase 主入口、关键非显性测试与运行时基线数据 | `tests/` | `tests/ARCHITECTURE.md` |

### 3.2 二级稳定元素

- `connectors/automotive-security-timeline/` 是当前唯一自研扩展实现目录，由 `connectors/automotive-security-timeline/ARCHITECTURE.md` 约束。
- `tests/mirror/` 是 Neo4j mirror 显性 testcase 的唯一物理入口与保护基线目录，由 `tests/mirror/ARCHITECTURE.md` 约束。
- `tests/runtime/` 是运行时恢复与配置基线目录，由 `tests/runtime/ARCHITECTURE.md` 约束。

## 4. 接口边界

### 4.1 运行时平台暴露的稳定接口

- Compose 服务名、profile、环境变量边界。
- OpenCTI HTTPS 入口与管理员 token 配置边界。
- MISP 测试专用 compose 变体入口。
- Neo4j mirror 预留环境变量边界：`NEO4J_ADVERTISED_HOST`、`NEO4J_HTTP_PORT`、`NEO4J_BOLT_PORT`、`NEO4J_PASSWORD`、`MIRROR_*`。

### 4.2 集成扩展暴露的稳定接口

- 容器 build context 与容器入口文件。
- 通过 OpenCTI connector helper 与外部数据源交互的适配边界。

### 4.3 运维脚本暴露的稳定接口

- `scripts/opencti-stack.ps1` 的 `Stop|Start|Restart|Up|Status` 动作。
- `scripts/backup-opencti.ps1` 的备份入口。
- `scripts/restore-opencti.ps1` 的恢复入口。

### 4.4 验证护栏暴露的稳定接口

- 当前 connector 显性 testcase 的唯一主入口：`tests/test_architecture_connector_support.py`。
- Neo4j mirror 显性 testcase 的唯一主入口：`tests/mirror/test_neo4j_sync_integrity.py`。
- 关键非显性测试入口：`tests/test_architecture_contracts.py`、`tests/test_acceptance_baselines.py`、`tests/test_dependency_boundaries.py`。

## 5. 依赖方向

全局依赖方向固定为：验证护栏、运维脚本、集成扩展 单向依赖 运行时平台契约；局部实现只能依赖其下层稳定边界，不得反向依赖测试内部实现或脚本内部实现。

必须满足：

- `tests/` 可以只读读取根契约、局部契约、意图图谱、compose 与脚本文件，但不得成为运行时平台的反向依赖。
- `scripts/` 只能操作 Docker Compose 与备份元数据，不得读取或驱动 connector 源码内部流程。
- `connectors/automotive-security-timeline/` 只能依赖 OpenCTI connector helper、标准库与第三方库，不得依赖 `tests/` 或 `scripts/`。
- Neo4j mirror 后续实现若引入新目录，必须依赖运行时平台与其自身局部契约，不得让运行时平台反向依赖该实现目录。

## 6. implements 追溯

### 6.1 直接实现意图元素的稳定实现元素

| 意图元素 / testcase | 直接实现元素 | 说明 |
| --- | --- | --- |
| `MITRE ATT&CK数据接入` 至 `MISP Intel接入` 这些 connector 显性 testcase | 运行时平台 + `tests/test_architecture_connector_support.py` | 仓库中的直接承载是 compose 服务定义、`.env` 配置入口与现有显性 pytest 主入口 |
| `OpenCTI 情报数据镜像至 Neo4j 完整性验证` | `tests/mirror/test_neo4j_sync_integrity.py` | 本阶段先把显性入口物理化并冻结其保护基线，运行时 mirror 实现仍待后续编码补齐 |

### 6.2 通过实现链间接承载意图元素的稳定实现元素

- `scripts/` 通过维护运行时平台生命周期、备份与恢复，间接承载 connector 显性 testcase 的可执行环境。
- `tests/test_architecture_contracts.py`、`tests/test_acceptance_baselines.py`、`tests/test_dependency_boundaries.py` 通过守住根契约、局部契约、入口定位和依赖方向，间接承载全部显性 testcase 的只读验收基线。
- `connectors/automotive-security-timeline/` 是当前仓库内的自研扩展能力，但在当前意图图谱中未见对应显性 testcase，因此仅作为实现侧稳定扩展元素存在，不强行直连意图层。

## 7. 显性 testcase 入口

当前显性 testcase 物理入口固定如下：

- connector 类显性 testcase 继续只读收口在 `tests/test_architecture_connector_support.py`，后续编码阶段只能补齐运行时与实现，不得拆分、迁移或重命名该入口。
- Neo4j mirror 显性 testcase 固定落在 `tests/mirror/test_neo4j_sync_integrity.py`，后续编码阶段必须直接调用该文件，不得重定向到其他入口。

## 8. 关键非显性测试

本阶段冻结下列关键非显性测试；后续 `/work` 阶段不得修改其入口、断言边界、挂载对象、追溯关系与受保护基线：

| 类别 | 冻结入口 | 守护目标 |
| --- | --- | --- |
| 架构边界 | `tests/test_architecture_contracts.py` | 根契约、局部契约、共享骨架与根契约引用关系 |
| 显性入口正确性 | `tests/test_acceptance_baselines.py` | 意图层 acceptanceCriteria 或显式路径声明与实际物理入口的一致性 |
| 依赖方向 | `tests/test_dependency_boundaries.py` | `tests/`、`scripts/`、`connectors/` 的稳定依赖方向 |
| 关键实现追溯 | `tests/mirror/test_neo4j_sync_integrity.py` + `tests/mirror/protected_*` | mirror 显性入口、保护夹具与保护基线的存在性与查询断言边界 |

## 9. 普通非显性测试

普通非显性测试作为后续编码阶段的支撑护栏，允许在契约规定的位置补充：

- 已创建：`connectors/automotive-security-timeline/tests/test_support_guardrails.py`
- 已保留：`tests/runtime/restore-validation/` 下的运行时恢复基线可继续作为后续 restore 类支撑测试挂载点
- 可追加但不应上升为根契约稳定元素：自研 connector 解析单测、PowerShell `-WhatIf` 冒烟、compose 配置校验

## 10. 保护对象

下列对象在当前阶段冻结为只读架构基线：

- `tests/test_architecture_connector_support.py`
- `tests/mirror/test_neo4j_sync_integrity.py`
- `tests/mirror/protected_fixtures/manual_seed_steps.md`
- `tests/mirror/protected_baselines/cypher_assertions.md`
- `tests/test_architecture_contracts.py`
- `tests/test_acceptance_baselines.py`
- `tests/test_dependency_boundaries.py`

## 11. 变更规则

- 新增稳定实现元素时，必须先更新本文件，再创建对应目录与 `ARCHITECTURE.md`。
- 局部契约可以补充本地职责、接口与测试挂载点，但不得重复定义根级规则。
- 若 future mirror 实现引入独立目录，其局部契约必须声明自己实现的是 `tests/mirror/` 所冻结的显性入口，而不是改写显性入口。