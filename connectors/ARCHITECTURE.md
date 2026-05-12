# connectors 局部契约

## 1. 角色

本文件定义 `connectors/` 目录作为“集成扩展”一级元素的局部边界，只收纳仓库自研或仓库直接拥有的扩展实现，不复刻第三方 connector 的业务细节。

## 2. 作用域

本契约覆盖：

- `connectors/automotive-security-timeline/`

本契约不把上游 OpenCTI 官方 connector 镜像展开成本地稳定目录；这些能力继续由运行时平台中的 compose 服务定义直接承载。

参考根契约：`../OVERALL_ARCHITECTURE.md`

## 3. 稳定元素

- `automotive-security-timeline/`：当前唯一自研 connector 实现目录。
- `automotive-security-timeline/tests/`：普通非显性测试挂载点，不是根级显性验收入口。

## 4. 接口边界

- 对运行时平台暴露的稳定接口是容器 build context、环境变量边界与入口脚本。
- 对外部系统暴露的稳定接口是对 Automotive Security Timeline 源的 HTTP 拉取，以及对 OpenCTI connector helper 的调用。

## 5. 依赖方向

- 允许依赖：标准库、第三方库、OpenCTI runtime env。
- 禁止依赖：`tests/` 内部实现、`scripts/` 内部实现。

## 6. implements 追溯

- 当前意图图谱中未见 `automotive-security-timeline` 的显性 testcase 或直接意图元素，因此本目录不强行声明对意图层的直接 implements。
- 本目录通过运行时平台中的 `connector-automotive-security-timeline` 服务配置，间接承载“仓库可扩展自研 connector”的实现能力。

## 7. 显性 testcase 入口

本目录当前没有显性 testcase 主入口。若未来图谱为自研 connector 新增显性 testcase，应优先在对应实现目录下新增独立入口，而不是复用根级 connector 验收文件。

## 8. 关键非显性测试

- 由 `../tests/test_dependency_boundaries.py` 守护本目录不得依赖 `tests/` 或 `scripts/`。

## 9. 普通非显性测试

- `automotive-security-timeline/tests/test_support_guardrails.py` 是本目录当前的普通支撑护栏。

## 10. 保护对象

- `automotive-security-timeline/src/main.py` 的入口角色与环境变量边界。
- `automotive-security-timeline/tests/test_support_guardrails.py` 的挂载位置。

## 11. 变更规则

- 若新增第二个自研 connector，应为其创建独立子目录与局部契约，而不是把本目录退化为无边界的代码收纳箱。