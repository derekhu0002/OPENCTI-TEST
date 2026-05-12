# tests/mirror 局部契约

## 1. 角色

本目录承载 Neo4j mirror 显性 testcase 的唯一物理入口，以及该入口对应的保护夹具与保护基线。

## 2. 作用域

本契约覆盖：

- `test_neo4j_sync_integrity.py`
- `protected_fixtures/`
- `protected_baselines/`

参考根契约：`../../OVERALL_ARCHITECTURE.md`

## 3. 稳定元素

- `test_neo4j_sync_integrity.py`：只读显性入口。
- `protected_fixtures/manual_seed_steps.md`：受保护的场景夹具描述。
- `protected_baselines/cypher_assertions.md`：受保护的查询断言基线。

## 4. 接口边界

- 输入边界：`.env` 中的 Neo4j mirror 配置，以及运行时覆盖变量 `OPENCTI_MIRROR_VALIDATE`、`MIRROR_EXPECTED_IPV4_VALUE`、`MIRROR_EXPECTED_IPV4_STANDARD_ID`、`MIRROR_EXPECTED_MALWARE_NAME`。
- 输出边界：只读验证 Neo4j HTTP 查询结果，不负责创建业务数据。

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

- 当前无普通非显性测试；后续若需要补充 mirror 支撑测试，应放在本目录或未来 mirror 实现目录的 `tests/` 下，并在局部契约中回填归属。

## 10. 保护对象

- 入口文件路径与测试函数名。
- `protected_fixtures/manual_seed_steps.md`
- `protected_baselines/cypher_assertions.md`

## 11. 变更规则

- 后续编码阶段不得修改本入口的挂载位置、查询对象、断言边界与保护文件路径。