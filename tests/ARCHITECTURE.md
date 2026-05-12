# tests 局部契约

## 1. 角色

本目录承载显性 testcase 主入口、关键非显性测试和运行时测试基线，是整个仓库的验证护栏一级元素。

## 2. 作用域

本契约覆盖：

- `test_architecture_connector_support.py`
- `test_architecture_contracts.py`
- `test_acceptance_baselines.py`
- `test_dependency_boundaries.py`
- `mirror/`
- `runtime/`

参考根契约：`../OVERALL_ARCHITECTURE.md`

## 3. 稳定元素

- `test_architecture_connector_support.py`：当前 connector 类显性 testcase 唯一主入口。
- `mirror/test_neo4j_sync_integrity.py`：Neo4j mirror 显性 testcase 唯一主入口。
- `test_architecture_contracts.py`：架构边界冻结测试。
- `test_acceptance_baselines.py`：显性入口与追溯冻结测试。
- `test_dependency_boundaries.py`：依赖方向冻结测试。
- `runtime/`：运行时恢复与配置基线目录。

## 4. 接口边界

- 本目录可以只读读取设计图谱、根契约、局部契约、compose、配置、脚本和自研 connector 源码。
- 本目录不得成为运行时代码的反向依赖。

## 5. 依赖方向

- 允许依赖：根契约、局部契约、仓库文件系统、pytest、标准库。
- 禁止依赖：让运行时代码导入本目录内部实现。

## 6. implements 追溯

- `test_architecture_connector_support.py` 直接 implements 当前图谱中的 connector 显性 testcase。
- `mirror/test_neo4j_sync_integrity.py` 直接 implements `OpenCTI 情报数据镜像至 Neo4j 完整性验证`。
- 其余三个冻结测试通过守护边界与入口，间接承载上述显性 testcase 的稳定性。

## 7. 显性 testcase 入口

- connector 类显性 testcase 固定在 `test_architecture_connector_support.py`。
- mirror 显性 testcase 固定在 `mirror/test_neo4j_sync_integrity.py`。

## 8. 关键非显性测试

- `test_architecture_contracts.py`
- `test_acceptance_baselines.py`
- `test_dependency_boundaries.py`

## 9. 普通非显性测试

- `runtime/` 下的恢复与配置支撑测试。
- `connectors/automotive-security-timeline/tests/` 下的本地支撑护栏。

## 10. 保护对象

- 根级显性入口文件名与路径。
- `mirror/protected_fixtures/` 与 `mirror/protected_baselines/`。

## 11. 变更规则

- 新增显性 testcase 时，必须明确唯一物理入口，并先回写本文件和根契约。
- 新增跨目录关键非显性测试时，默认挂在本目录而不是嵌入运行时代码目录。