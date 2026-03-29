# 法律智能问答系统

基于RAG（检索增强生成）的法律智能问答系统，支持多轮对话、法条溯源、混合检索、案例检索等功能。

## 系统架构

```
law03/
├── backend/                          # 后端服务
│   ├── modules/                      # 核心模块
│   │   ├── document_processor.py     # 文档处理与嵌入生成
│   │   ├── rag_retriever.py          # 混合检索（向量+BM25）
│   │   ├── optimized_workflow.py     # 优化版问答工作流
│   │   └── langgraph_workflow.py     # LangGraph工作流（备用）
│   ├── utils/
│   │   └── exception_handler.py      # 异常处理
│   ├── main.py                       # FastAPI主程序
│   ├── config.py                     # 配置文件
│   ├── run.py                        # 启动脚本
│   ├── embed_from_jsonl.py           # 数据嵌入脚本
│   ├── requirements.txt              # Python依赖
│   └── .env                          # 环境变量配置
├── frontend/                          # 前端界面
│   ├── src/
│   │   ├── components/               # Vue组件
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
- **关键词检索**: BM25 (jieba分词)

### 前端
- **框架**: Vue 3
- **构建工具**: Vite 5
- **HTTP客户端**: Axios
- **Markdown解析**: Marked

## 核心功能

### 1. 智能问答
- 流式输出回答，实时显示生成内容
- 多轮对话上下文记忆
- 法条引用自动添加"查看原文"按钮
- 点击按钮可预览法条完整内容
- 检索质量不佳时自动使用基座大模型回答

### 2. 混合检索
- **向量检索**: 基于语义相似度，使用Qwen3-Embedding模型
- **BM25检索**: 基于关键词匹配，使用jieba分词
- **重排优化**: 使用bge-reranker提升检索准确性
- **质量检测**: 自动评估检索结果相关性

### 3. 法条溯源
- 回答中的法条引用可点击
- 弹出模态框展示法条原文
- 支持下载原文件或打开文件所在位置

### 4. 文件管理
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

### 用户提问（流式）
```
POST /api/legal/query/stream
Content-Type: application/json

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

1. **模型预加载**: 启动时预加载嵌入模型和重排模型，减少首次查询等待时间
2. **混合检索**: 向量检索 + BM25关键词检索，提升检索准确性
3. **检索质量检测**: 自动评估检索结果相关性，质量不佳时使用基座大模型回答
4. **法条匹配**: 支持多种格式的法条引用（"第26条"、"第 26 条"等）
5. **旧版DOC兼容**: 支持扩展名为.docx但实际为.doc格式的文件
6. **分类筛选**: 法律法规和案例文书分开管理，提供更精准的筛选体验

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
