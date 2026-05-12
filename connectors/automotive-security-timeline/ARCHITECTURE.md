# automotive-security-timeline 局部契约

## 1. 角色

本目录承载自研 `Automotive Security Timeline` connector 的稳定实现边界。

## 2. 作用域

本契约覆盖：

- `Dockerfile`
- `src/main.py`
- `tests/`

参考根契约：`../../OVERALL_ARCHITECTURE.md`

## 3. 稳定元素

- `src/main.py`：稳定入口文件。
- `AutomotiveSecurityTimelineConnector`：稳定入口组件。
- `tests/test_support_guardrails.py`：普通非显性支撑护栏。

## 4. 接口边界

- 输入边界：`OPENCTI_URL`、`OPENCTI_TOKEN`、`CONNECTOR_ID`、`CONNECTOR_DURATION_PERIOD`、`AUTOMOTIVE_TIMELINE_SOURCE_URL`、`AUTOMOTIVE_TIMELINE_VERIFY_TLS`、`AUTOMOTIVE_TIMELINE_REQUEST_TIMEOUT`。
- 输出边界：向 OpenCTI 发送 STIX bundle；向外部时间线源发起只读 HTTP 请求。

## 5. 依赖方向

- 本目录只能向外依赖第三方库和运行时环境。
- 本目录不得依赖 `scripts/` 与 `tests/` 的内部实现。

## 6. implements 追溯

- 本目录当前不直接 implements 意图图谱中的显性 testcase。
- 本目录通过 `docker-compose.yml` 中的 `connector-automotive-security-timeline` 服务，间接承载仓库的自研 connector 扩展能力。

## 7. 显性 testcase 入口

当前无显性 testcase 入口；后续若引入显性 testcase，应新增独立入口而不是修改普通支撑护栏。

## 8. 关键非显性测试

- 当前无冻结到本目录内的关键非显性测试；关键依赖方向由根级 `tests/test_dependency_boundaries.py` 守护。

## 9. 普通非显性测试

- `tests/test_support_guardrails.py` 守护入口类名、关键常量与环境变量边界。

## 10. 保护对象

- `src/main.py` 的入口类名、主要常量与外部环境变量名称。

## 11. 变更规则

- 后续编码可以扩展解析与映射细节，但不得把本目录拆成大量浅层稳定模块。