# tests/mirror 局部契约

## 1. 角色

本目录承载 Neo4j mirror 显性 testcase 的唯一物理入口，以及该入口对应的保护夹具与保护基线。

## 2. 作用域

本契约覆盖：

- `conftest.py`
- `test_neo4j_sync_integrity.py`
- `protected_fixtures/`
- `protected_baselines/`

参考根契约：`../../OVERALL_ARCHITECTURE.md`

## 3. 稳定元素

- `conftest.py`：镜像显性验收所需的自动夹具装配与 Neo4j 访问适配层；运行时事实上的一等 Neo4j 目标由主 compose 中与 OpenCTI 同网段的 `neo4j` service 提供。
- `test_neo4j_sync_integrity.py`：只读显性入口。
- `protected_fixtures/manual_seed_steps.md`：受保护的场景夹具描述。
- `protected_baselines/cypher_assertions.md`：受保护的查询断言基线。
- `test_fixture_setup_support.py`：镜像自动建夹具支撑测试入口。

## 4. 接口边界

- 输入边界：`.env` 中的 OpenCTI 与 Neo4j mirror 配置、主 compose 默认网络中的 `neo4j` service，以及运行时覆盖变量 `MIRROR_EXPECTED_IPV4_VALUE`、`MIRROR_EXPECTED_MALWARE_NAME`、`MIRROR_ASSERT_TIMEOUT_SECONDS`。
- 输出边界：显性入口测试体只读验证 Neo4j HTTP 查询结果；场景数据必须由本目录支撑 fixture 在断言前通过真实 OpenCTI GraphQL 自动建立。

## 5. 依赖方向

- 本目录可以只读依赖根契约、意图图谱、`.env` 和本目录内的保护文件。
- 本目录不得依赖未来 mirror 实现目录的内部细节；后续实现应反向满足本入口，而不是要求本入口迁移。

## 6. implements 追溯

- `test_neo4j_sync_integrity.py` 直接 implements 图谱中的 `OpenCTI 情报数据镜像至 Neo4j 完整性验证`。
- 保护夹具和保护基线通过实现链间接承载同一显性 testcase。

## 7. 显性 testcase 入口

- 唯一入口：`test_neo4j_sync_integrity.py`

## 8. 关键非显性测试

- 根级 `../test_acceptance_baselines.py` 冻结本目录入口路径与保护文件存在性。

## 9. 普通非显性测试

- `conftest.py`：通过本地 Neo4j HTTP 脚手架为显性入口提供最小执行环境，不上升为新的显性入口。
- `test_fixture_setup_support.py`：自动建夹具支撑测试，用于在显性验收前通过 OpenCTI GraphQL 建立固定场景数据。
- 后续若需要补充更多 mirror 支撑测试，应放在本目录或未来 mirror 实现目录的 `tests/` 下，并在局部契约中回填归属。

## 10. 保护对象

- 入口文件路径与测试函数名。
- `protected_fixtures/manual_seed_steps.md`
- `protected_baselines/cypher_assertions.md`

## 11. 变更规则

- 后续编码阶段不得修改本入口的挂载位置、查询对象、断言边界与保护文件路径。