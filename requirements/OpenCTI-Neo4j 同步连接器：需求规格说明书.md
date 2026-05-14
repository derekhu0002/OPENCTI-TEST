# OpenCTI-Neo4j 同步连接器：需求规格说明书

## 1. 项目目标

开发一个基于 Python 的 OpenCTI 实时流（Stream）连接器，将 OpenCTI 平台中的 STIX 2.1 结构化情报数据实时同步到 Neo4j 图数据库中，以支持复杂的关联分析、路径追踪和图计算（GDS）。

## 2. 核心功能需求 (Functional Requirements)

### 2.1 数据流订阅 (Data Ingestion)

- **实时流接入**：连接器必须通过 EventSource (SSE) 或 OpenCTI 的 Python 库 (pycti) 订阅指定的 Live Stream ID。
    
- **断点续传**：支持保存上一次同步的 Listen ID 或时间戳，确保连接中断后重启时，数据不丢失、不重复。
    

### 2.2 数据映射逻辑 (Data Mapping)

- **实体转换 (Entities -> Nodes)**：
    
    - 将 STIX 实体（如 Malware, Threat-Actor, Indicator, Identity）转换为 Neo4j 节点。
        
    - **标签(Label)**：使用实体的 standard_id 的类型或 entity_type 作为 Neo4j 的 Label。
        
    - **属性(Properties)**：同步关键字段（Name, Description, Created_at, Confidence 等），并支持自定义排除不需要的元数据。
        
- **关系转换 (Relationships -> Edges)**：
    
    - 将 STIX 关系（SRO）转换为 Neo4j 的边。
        
    - **类型(Type)**：使用关系类型（如 indicates, targets, uses）作为边的 Type。
        
    - **方向**：严格遵循 STIX 的 source_ref -> target_ref 方向。
        
- **嵌套属性处理**：处理 STIX 中的 marking-definitions（TLP 级别）和 labels（标签），建议在 Neo4j 中作为节点的属性数组存储。
    

### 2.3 数据一致性维护 (CRUD Operations)

- **Create/Update**：使用 Neo4j 的 MERGE 语句。必须基于 OpenCTI 的 standard_id（或内部 ID）作为唯一键，防止重复生成节点。
    
- **Delete/Missing**：
    
    - 当 OpenCTI 发送 delete 事件时，同步删除 Neo4j 中的对应节点及其关联边。
        
    - 处理“逻辑删除”与“物理删除”的同步。
        
- **原子性**：确保一个 STIX Bundle 中的所有变更在一个 Neo4j 事务中完成。
    

### 2.4 初始化同步 (Initial Synchronization)

- 支持“全量同步”模式：在首次启动时，从 Stream 的起始点（或指定时间点）拉取所有历史存量数据。
    

---

## 3. 非功能需求 (Non-Functional Requirements)

### 3.1 性能与伸缩性

- **吞吐量**：支持每秒处理不少于 500 个事件（取决于 Neo4j 写入性能）。
    
- **批量处理**：支持将流中的事件进行微批处理（Micro-batching），以减少 Neo4j 的事务开销。
    
- **并发控制**：防止多个线程同时修改同一个节点导致 Neo4j 死锁。
    

### 3.2 鲁棒性与可靠性

- **重试机制**：当 Neo4j 暂时不可用（如网络波动、数据库锁定）时，连接器应具备指数退避重试策略。
    
- **死信队列**：对于格式错误无法解析的事件，应记录到错误日志或特定存储，而不应中断同步进程。
    

### 3.3 可观察性

- **日志**：记录同步进度、错误堆栈、过滤掉的事件。
    
- **健康检查**：提供一个简单的状态接口，供 Docker 或 Kubernetes 检查容器是否存活。
    

---

## 4. 技术栈建议

- **开发语言**：Python 3.10+（与 OpenCTI 生态兼容性最好）。
    
- **核心库**：
    
    - pycti: OpenCTI 官方 SDK，用于处理流。
        
    - neo4j: Neo4j 官方 Python Driver。
        
- **数据库**：Neo4j 4.4+ 或 5.x (支持 Bolt 协议)。
    

---

## 5. 关键配置参数 (Configuration)

连接器应通过环境变量或 config.yml 接收以下参数：

|   |   |   |
|---|---|---|
|参数名|说明|示例|
|OPENCTI_URL|OpenCTI 平台地址|http://localhost:8080|
|OPENCTI_TOKEN|API 令牌|your-uuid-token|
|STREAM_ID|在 OpenCTI 创建的实时流 ID|live-stream-uuid|
|NEO4J_URL|Neo4j 地址|bolt://localhost:7687|
|NEO4J_USER|用户名|neo4j|
|NEO4J_PASSWORD|密码|password|
|IMPORT_EXISTING|是否同步历史数据|true/false|
|EXCLUDE_TYPES|过滤掉不需要同步的实体类型|Observed-Data,Note|

---

## 6. 核心开发难点提示（避坑指南）

1. **Standard ID 映射**：OpenCTI 使用特定的算法生成 ID。在 Neo4j 中，务必将 standard_id 设为节点的唯一索引（Unique Constraint），否则你的图会迅速变成一团乱麻。
    
2. **异步处理**：SSE 流是单向长连接。如果写入 Neo4j 太慢，会导致客户端缓冲区溢出。建议内部使用 Queue（队列）解耦“接收”和“写入”逻辑。
    
3. **模式演进**：STIX 2.1 允许自定义属性。你的代码需要具备泛化能力，能够动态处理节点属性，而不是硬编码字段名。