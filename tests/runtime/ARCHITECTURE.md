# tests/runtime 局部契约

## 1. 角色

本目录承载运行时恢复与配置类测试夹具和基线数据。

## 2. 作用域

本契约覆盖：

- `rabbitmq.conf/`
- `restore-validation/`

参考根契约：`../../OVERALL_ARCHITECTURE.md`

## 3. 稳定元素

- `restore-validation/metadata/`
- `restore-validation/volumes/`
- `rabbitmq.conf/`

## 4. 接口边界

- 本目录只作为只读测试基线数据目录，不承担业务实现职责。

## 5. 依赖方向

- 仅允许被 `tests/` 下的测试读取。
- 不允许脚本或运行时代码反向依赖本目录内部结构作为业务前提。

## 6. implements 追溯

- 本目录当前不直接 implements 意图图谱中的显性 testcase。
- 本目录通过为恢复与配置支撑测试提供基线数据，间接支撑运行时平台实现。

## 7. 显性 testcase 入口

本目录当前无显性 testcase 主入口。

## 8. 关键非显性测试

- 当前无冻结到本目录内的关键非显性测试。

## 9. 普通非显性测试

- 后续 restore/backup/config 支撑测试默认挂在最近公共祖先 `tests/`，并读取本目录基线数据。

## 10. 保护对象

- `restore-validation/metadata/`
- `restore-validation/volumes/`

## 11. 变更规则

- 若替换或扩充恢复基线数据，必须说明其对应的支撑测试归属与影响范围。