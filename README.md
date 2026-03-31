# 法律智能问答系统

基于RAG（检索增强生成）的法律智能问答系统，支持用户登录、多轮对话、法条溯源、混合检索、案例检索等功能。

## 系统架构

```
law03/
├── backend/                          # 后端服务
│   ├── modules/                      # 核心模块
│   │   ├── document_processor.py     # 文档处理与嵌入生成
│   │   ├── rag_retriever.py          # 混合检索（向量+BM25）
│   │   ├── optimized_workflow.py     # 优化版问答工作流
│   │   ├── memory_store.py           # 对话记忆持久化存储
│   │   ├── hierarchical_summary.py   # 滚动分层摘要（多级压缩策略）
│   │   ├── context_manager.py        # 上下文管理器（查询改写与指代消解）
│   │   ├── auth.py                   # 用户认证模块
│   │   └── langgraph_workflow.py     # LangGraph工作流（备用）
│   ├── utils/
│   │   └── exception_handler.py      # 异常处理
│   ├── data/                         # 数据存储目录
│   │   ├── conversation_memory.db    # 对话记忆数据库
│   │   └── users.db                  # 用户认证数据库
│   ├── main.py                       # FastAPI主程序
│   ├── config.py                     # 配置文件
│   ├── run.py                        # 启动脚本
│   ├── embed_from_jsonl.py           # 数据嵌入脚本
│   ├── requirements.txt              # Python依赖
│   └── .env                          # 环境变量配置
├── frontend/                          # 前端界面
│   ├── src/
│   │   ├── components/               # Vue组件
│   │   │   ├── LoginView.vue         # 登录界面
│   │   │   ├── AnswerDisplay.vue     # 回答展示（含查看原文按钮）
│   │   │   ├── FileFilter.vue        # 文件筛选（法律法规/案例文书分类）
│   │   │   ├── FileList.vue          # 文件列表
│   │   │   └── QueryInput.vue        # 查询输入
│   │   ├── App.vue                   # 主应用组件
│   │   └── main.js                   # 入口文件
│   ├── index.html                    # HTML模板
│   ├── package.json                  # Node依赖
│   └── vite.config.js                # Vite配置
├── process-data/                      # 数据预处理模块
│   ├── main.py                       # 预处理主程序
│   ├── word_processor.py             # Word文档处理
│   ├── pdf_processor.py              # PDF文档处理
│   ├── text_cleaner.py               # 文本清洗
│   ├── jsonl_writer.py               # JSONL输出
│   ├── requirements.txt              # 预处理依赖
│   └── processed_data/               # 预处理输出目录
│       ├── article_chunks.jsonl      # 法条数据
│       ├── cases.jsonl               # 案例数据
│       └── processing_stats.json     # 处理统计
├── knowledge_base/                    # 知识库文档
│   ├── laws/                         # 法律法规文档
│   │   ├── 内蒙古自治区专利促进与保护条例.docx
│   │   ├── 内蒙古自治区中医药条例.docx
│   │   ├── 内蒙古自治区促进民族团结进步条例.docx
│   │   ├── 内蒙古自治区保障农民工工资支付条例.docx
│   │   ├── 内蒙古自治区反家庭暴力条例.docx
│   │   ├── 内蒙古自治区噪声污染防治条例.docx
│   │   ├── 内蒙古自治区安全生产条例.docx
│   │   ├── 内蒙古自治区宗教事务条例.docx
│   │   ├── 内蒙古自治区筑牢祖国北疆安全稳定屏障促进条例.docx
│   │   └── 包头市实施《内蒙古自治区文明行为促进条例》办法.docx
│   └── cases/                        # 案例文书文档
│       ├── 何某张某民间借贷纠纷再审审查和审判监督民事裁定书.doc
│       ├── 包头市某代建中心建设工程施工合同纠纷民事裁定书.doc
│       ├── 张某院某民间借贷纠纷再审审查民事裁定书.doc
│       ├── 赵某某白某某吴某某房屋买卖合同纠纷民事裁定书.doc
│       └── 郭某华诉李某希等机动车交通事故责任纠纷案.pdf
├── start.bat                         # Windows一键启动脚本
└── README.md                         # 项目说明文档
```

## 技术栈

### 后端
- **框架**: Python 3.8+, FastAPI, Uvicorn
- **LLM框架**: LangChain, LangGraph
- **向量数据库**: Milvus
- **嵌入模型**: Qwen3-Embedding-0.6B (通过SentenceTransformer加载)
- **大语言模型**: qwen3.5-35b-a3b (通过OpenAI API调用)
- **重排模型**: bge-reranker-base
- **关键词检索**: BM25 (jieba分词，挂载法律专有词典)
- **工具库**: cn2an (法律编号解析), tiktoken (精确 Token 计数), tenacity (故障自动重试)

### 前端
- **框架**: Vue 3
- **构建工具**: Vite 5
- **HTTP客户端**: Axios
- **Markdown解析**: Marked

## 核心功能

### 1. 用户认证
- 用户登录/登出功能
- JWT Token认证机制
- Token有效期24小时
- 默认管理员账户：admin / 123456
- 用户会话隔离，每个用户只能查看自己的对话历史

### 2. 智能问答
- 流式输出回答，实时显示生成内容
- **持久化对话记忆**：使用SQLite存储对话历史，重启后不丢失
- **滚动分层摘要 (Rolling Hierarchical Summary)**：
  - **Layer 0 (近期消息)**：完整保留最近几轮对话，确保近期上下文精准。
  - **Layer 1 (短期摘要)**：对近期对话进行压缩，保留关键法律事实。
  - **Layer 2 (长期摘要)**：对历史对话进行高度压缩，保留核心法律问题。
  - **持久化存储**：摘要数据通过 SQLite 实时持久化，支持跨 Session 恢复对话背景。
  - 有效解决长对话带来的 Token 溢出问题，同时保持超长对话的连贯性。
- **精确 Token 控制**：集成 `tiktoken` 库，按模型真实分词策略进行 Token 计数，防止上下文长度超限。
- **上下文感知的查询改写 (Query Rewriting)**：
  - 自动识别并补全用户提问中的代词（如“它”、“该条款”、“这个人”）。
  - 结合历史对话背景重写查询，显著提升 RAG 的检索准确率。
- **历史会话侧边栏**：左侧显示历史会话列表，按时间命名（今天/昨天/具体日期）
- **会话管理**：支持新建会话、切换会话、删除会话
- 法条引用自动添加"查看原文"按钮
- 点击按钮可预览法条完整内容
- 检索质量不佳时自动使用基座大模型回答

### 3. 混合检索
- **向量检索**: 基于语义相似度，使用Qwen3-Embedding模型
- **BM25检索**: 基于关键词匹配，使用jieba分词
- **重排优化**: 使用bge-reranker提升检索准确性
- **融合算法**: 采用 **RRF (Reciprocal Rank Fusion)** 算法融合向量与 BM25 检索结果，显著提升排序公平性与准确度
- **索引优化**: Milvus 接口由 IVF_FLAT 升级为 **HNSW** 高性能索引，大幅提升高并发下的搜索效率
- **质量检测**: 自动评估检索结果相关性
- **BM25 索引持久化**: 实现 BM25 索引的序列化存储与快速恢复，避免每次启动重构索引带来的 CPU 开销
- **法律条文解析**: 集成 `cn2an` 逻辑，支持复杂中文法律条文编号（如“二十一条”、“第一百一十三条”）的自动转换与精准匹配

### 4. 法条溯源
- 回答中的法条引用可点击
- 弹出模态框展示法条原文
- 支持下载原文件或打开文件所在位置

### 5. 文件管理
- **分类筛选**: 法律法规 / 案例文书 分类展示
- **法律法规筛选**: 按法律名称、法条编号筛选
- **案例文书筛选**: 按案件类型、案号、涉及法律筛选
- 支持文件预览

## 快速开始

### 1. 环境准备

```bash
# 安装Python依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
npm install
```

或使用一键脚本（Windows）：
```bash
start.bat
```

### 2. 启动Milvus

```bash
docker run -d --name milvus \
  -p 19530:19530 \
  milvusdb/milvus:latest
```

### 3. 配置环境变量

编辑 `backend/.env`：

```env
OPENAI_API_KEY=your_api_key
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
MILVUS_HOST=localhost
MILVUS_PORT=19530
EMBEDDING_MODEL_PATH=D:\develop1\Qwen3-Embedding-0.6B
RERANK_MODEL_PATH=D:\develop1\bge-reranker-base
COLLECTION_NAME=legal_knowledge
VECTOR_DIMENSION=1024
```

### 4. 数据预处理与嵌入

**步骤1：预处理文档**

将法律文档放入 `knowledge_base/laws/` 和 `knowledge_base/cases/`，然后运行：

```bash
cd process-data
pip install -r requirements.txt
python main.py
```

预处理后会生成：
- `processed_data/article_chunks.jsonl` - 法条数据
- `processed_data/cases.jsonl` - 案例数据

**步骤2：嵌入到Milvus**

```bash
cd backend
python embed_from_jsonl.py
```

### 5. 启动服务

```bash
# 启动后端（端口8000）
cd backend
python run.py

# 启动前端（新终端，端口3000）
cd frontend
npm run dev
```

### 6. 访问系统

- 前端界面: http://localhost:3000
- API文档: http://localhost:8000/docs
- API交互文档: http://localhost:8000/redoc

## 使用说明

### 用户登录

首次访问系统会显示登录界面：
- 默认管理员账户：**admin**
- 默认密码：**123456**

登录后可以：
- 查看自己的历史会话
- 继续之前的对话
- 创建新的会话

### 历史会话

智能助手页面左侧为历史会话侧边栏：
- **会话命名**：按时间自动命名（今天 HH:MM / 昨天 HH:MM / MM-DD HH:MM）
- **切换会话**：点击历史会话可继续之前的对话
- **新建会话**：点击顶部 + 按钮创建新会话
- **删除会话**：鼠标悬停会话项，点击右侧 × 按钮删除
- **消息数量**：每个会话显示包含的消息条数

### 智能问答

支持多种类型的法律问题：

- "内蒙古自治区宗教事务条例第三条内容是什么？"
- "专利促进与保护条例的第5条内容是什么？"
- "我想了解有关家暴的法律"
- "我想了解一下借贷的法律"

### 查看原文

回答中的法条引用（如"第 26 条"）旁边会显示 📄**查看原文** 按钮，点击可：
- 查看法条完整原文
- 下载原文件
- 打开文件所在位置

### 文件检索

在"文件检索"页面：
1. 选择文档类型：**法律法规** 或 **案例文书**
2. 根据类型使用不同的筛选条件：
   - 法律法规：法律名称、法条编号
   - 案例文书：案件类型、案号、涉及法律
3. 点击文件可预览内容

## API接口

### 用户认证

**登录**
```
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "123456"
}

# 返回
{
  "success": true,
  "token": "xxx",
  "user_id": 1,
  "username": "admin",
  "expires_at": "2026-03-30T12:00:00"
}
```

**登出**
```
POST /api/auth/logout
Authorization: Bearer {token}
```

**验证Token**
```
GET /api/auth/check
Authorization: Bearer {token}
```

### 会话管理

**获取用户会话列表**
```
GET /api/conversation/sessions
Authorization: Bearer {token}
```

**获取会话消息**
```
GET /api/conversation/messages?session_id=xxx
Authorization: Bearer {token}
```

**删除会话**
```
DELETE /api/conversation/session?session_id=xxx
Authorization: Bearer {token}
```

### 用户提问（流式）
```
POST /api/legal/query/stream
Content-Type: application/json
Authorization: Bearer {token}

{
  "query": "什么是正当防卫？",
  "session_id": "optional_session_id"
}

# 返回: text/event-stream
```

### 用户提问（非流式）
```
POST /api/legal/query
Content-Type: application/json
Authorization: Bearer {token}

{
  "query": "什么是正当防卫？",
  "session_id": "optional_session_id"
}
```

### 文件筛选
```
POST /api/file/filter
{
  "doc_type": "law",           // "law" 或 "case"
  "law_name": "内蒙古自治区宗教事务条例",
  "article_number": "3"
}

# 案例筛选
{
  "doc_type": "case",
  "case_type": "民事",
  "case_number": "（2026）内民申"
}
```

### 获取文件列表
```
GET /api/file/list
```

### 获取文件内容
```
GET /api/file/content?file_path=xxx
```

### 清除对话历史
```
POST /api/legal/clear-history
Content-Type: application/json

{
  "session_id": "your_session_id"
}
```

## 项目优化点

1. **滚动分层摘要与持久化**: 实现 Layer 0/1/2 三级缓存策略，并支持 SQLite 异步持久化，同步历史记忆
2. **查询改写与指代消解**: 解决对话中的代词跳变问题，使 RAG 检索更精准
3. **混合检索与 RRF 融合**: 引入 Reciprocal Rank Fusion 算法，完美结合语义与词法检索优势
4. **高性能索引**: 升级 Milvus 索引至 HNSW，优化大规模法律文书下的检索时延
5. **异步 IO 调度**: 对 Word/PDF 内容提取等耗时 IO 操作进行异步化处理，保障 API 响应的高并发吞吐
6. **故障自愈机制**: 为大模型调用引入 Tenacity 智能重试策略，应对网络抖动与接口限流
7. **精准 Token 计数**: 使用 tiktoken 实现真正的 Token 级别上下文窗口管理
8. **法条精准匹配**: 结合 cn2an 与自定义词库，支持各种复杂格式的法条引用识别与原文回溯
9. **用户认证与启动自检**: 前端引入启动即时身份校验与加载遮罩，确保授权状态的严格同步
10. **“零阻塞”瞬时启动 (Zero-Wait Boot)**：
    - **后台异步初始化**：所有重量级组件（Milvus 连接、模型加载、索引恢复、图编译）全部移至后台任务，实现 API 服务 **1秒内** 闪电启动。
    - **并行预加载策略**：利用 `asyncio` 并行加载多个 AI 模型与法律词典，大幅缩短系统完全就绪的等待时间。
    - **智能就绪守护**：内置系统状态监控，在后台预热期间提供友好的用户反馈，确保系统平稳过渡。
11. **BM25 缓存加速**：通过本地 Pickle 持久化技术，将 BM25 索引冷启动耗时从数秒缩减至毫秒级。

## 数据流程

```
原始文档 (Word/PDF)
    ↓
process-data/main.py (预处理)
    ↓
JSONL文件 (article_chunks.jsonl, cases.jsonl)
    ↓
embed_from_jsonl.py (嵌入)
    ↓
Milvus向量数据库
    ↓
智能问答系统
```

## 配置参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| OPENAI_API_KEY | - | OpenAI API密钥 |
| OPENAI_API_BASE | https://dashscope.aliyuncs.com/compatible-mode/v1 | API基础URL |
| MILVUS_HOST | localhost | Milvus服务地址 |
| MILVUS_PORT | 19530 | Milvus服务端口 |
| EMBEDDING_MODEL_PATH | - | 嵌入模型路径 |
| RERANK_MODEL_PATH | BAAI/bge-reranker-base | 重排模型路径 |
| COLLECTION_NAME | legal_knowledge | Milvus集合名称 |
| VECTOR_DIMENSION | 1024 | 向量维度 |
| TOP_K_VECTOR | 10 | 向量检索返回数量 |
| TOP_K_BM25 | 10 | BM25检索返回数量 |
| TOP_K_RERANK | 5 | 重排后返回数量 |

## 注意事项

1. 确保Milvus服务正常运行
2. 嵌入模型和重排模型路径配置正确
3. API Key配置有效且有足够额度
4. 知识库文档支持DOCX、DOC、PDF、TXT格式
5. 首次运行需要先执行数据预处理和嵌入

## 免责声明

本系统提供的法律信息仅供参考，不构成法律意见或建议。具体法律问题请咨询专业律师。

## 许可证

MIT License
