# Mirror 保护夹具

本文件冻结 Neo4j mirror 显性 testcase 的 GIVEN 与 WHEN，不允许在后续编码阶段改写为其它场景。

## GIVEN

1. OpenCTI 容器环境已启动。
2. 镜像专用 Neo4j 容器已启动，并与主环境隔离。
3. 同步插件、脚本或 connector 已具备 Live Stream 权限。

## WHEN

1. 在 OpenCTI 中创建 `IPv4-Addr`，值为 `1.2.3.4`。
2. 在 OpenCTI 中创建 `Malware`，名称为 `Mirai-Botnet`。
3. 在两者之间建立 `indicates` 关系。