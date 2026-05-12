# scripts 局部契约

## 1. 角色

本目录承载稳定的运维动作入口，而不是业务实现或测试实现。

## 2. 作用域

本契约覆盖：

- `opencti-stack.ps1`
- `backup-opencti.ps1`
- `restore-opencti.ps1`

参考根契约：`../OVERALL_ARCHITECTURE.md`

## 3. 稳定元素

- `opencti-stack.ps1`：生命周期控制入口。
- `backup-opencti.ps1`：备份入口。
- `restore-opencti.ps1`：恢复入口。

## 4. 接口边界

- 只向外暴露 PowerShell 参数和 Docker Compose 操作语义。
- 允许读取根目录配置文件和备份目录元数据。

## 5. 依赖方向

- 允许依赖：Docker CLI、Compose 项目目录、备份元数据。
- 禁止依赖：connector 源码内部实现、pytest 测试内部实现。

## 6. implements 追溯

- 本目录不直接 implements 意图图谱中的显性 testcase。
- 本目录通过维护 runtime 生命周期与备份恢复能力，间接承载显性 testcase 所需运行环境。

## 7. 显性 testcase 入口

本目录无显性 testcase 主入口。

## 8. 关键非显性测试

- `../tests/test_dependency_boundaries.py` 冻结本目录不得跨层引用 connector 或 pytest 内部实现。

## 9. 普通非显性测试

- 允许后续在最近公共祖先 `tests/` 下增加脚本 `-WhatIf` 冒烟或恢复流程支撑测试。

## 10. 保护对象

- 三个脚本的入口文件名与动作参数边界。

## 11. 变更规则

- 新增脚本必须承担清晰的稳定职责；不要把局部流程或一次性操作脚本提升为长期稳定元素。