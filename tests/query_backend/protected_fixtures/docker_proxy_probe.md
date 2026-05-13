# Query Backend Docker 统一代理保护夹具

本文件冻结 Docker 统一代理显性 testcase 的 GIVEN 与 WHEN，不允许在后续编码阶段改写为其它访问路径。

## GIVEN

1. 查询后端以独立 Docker 容器方式运行。
2. Caddy 作为统一 HTTPS 反向代理入口，把 `/graph/query` 转发到 `query-backend:8088`。
3. 调用方通过 `https://localhost/graph/query` 访问查询后端，而不是直连容器内部地址。

## WHEN

1. 调用方向统一代理入口提交一条包含写操作的 Cypher。
2. 请求经由 Caddy 转发到查询后端容器。