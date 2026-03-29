# 法律智能问答系统

基于RAG（检索增强生成）的法律智能问答系统，支持多轮对话、法条溯源、混合检索等功能。

## 系统架构

```
├── backend/                    # 后端服务
│   ├── modules/               # 核心模块
│   │   ├── document_processor.py  # 文档处理与嵌入生成
│   │   ├── rag_retriever.py       # 混合检索（向量+BM25）
│   │   └── optimized_workflow.py  # 优化版问答工作流
│   ├── utils/                 # 工具模块
│   │   └── exception_handler.py   # 异常处理
│   ├── main.py                # FastAPI主程序
│   ├── config.py              # 配置文件
│   ├── embed_from_jsonl.py    # 数据嵌入脚本
│   ├── requirements.txt       # Python依赖
│   └── .env                   # 环境变量
├── frontend/                   # 前端界面
│   ├── src/
│   │   ├── components/        # Vue组件
│   │   │   ├── AnswerDisplay.vue    # 回答展示（含查看原文按钮）
│   │   │   ├── FileFilter.vue       # 文件筛选
│   │   │   ├── FileList.vue         # 文件列表
│   │   │   └── QueryInput.vue       # 查询输入
│   │   ├── App.vue           # 主应用
│   │   └── main.js           # 入口文件
│   ├── package.json          # Node依赖
│   └── vite.config.js        # Vite配置
├── process-data/              # 数据预处理
│   ├── main.py               # 预处理主程序
│   ├── word_processor.py     # Word文档处理
│   ├── pdf_processor.py      # PDF文档处理
│   ├── text_cleaner.py       # 文本清洗
│   ├── jsonl_writer.py       # JSONL输出
│   └── processed_data/       # 预处理输出目录
└── knowledge_base/            # 知识库文档
    ├── laws/                  # 法条文档（支持DOCX、PDF、TXT）
    └── cases/                 # 案例文档
```

## 技术栈

- **后端**: Python 3.8+, FastAPI, LangChain
- **前端**: Vue 3, Vite, Marked
- **向量数据库**: Milvus
- **嵌入模型**: Qwen3-Embedding-0.6B (通过SentenceTransformer加载)
- **大语言模型**: 通过OpenAI API调用（如qwen3.5）
- **重排模型**: bge-reranker-base
- **关键词检索**: BM25 (jieba分词)

## 核心功能

### 1. 智能问答
- 流式输出回答
- 多轮对话上下文记忆
- 法条引用自动添加"查看原文"按钮
- 点击按钮可预览法条完整内容

### 2. 混合检索
- **向量检索**: 基于语义相似度
- **BM25检索**: 基于关键词匹配
- **重排优化**: 使用bge-reranker提升准确性

### 3. 法条溯源
- 回答中的法条引用可点击
- 弹出模态框展示法条原文
- 支持下载原文件或打开文件位置

### 4. 文件管理
- 按法律名称、案件类型、法条编号筛选
- 文件列表展示
- 支持文件上传和预览

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd law03

# 安装Python依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
npm install
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
EMBEDDING_MODEL_PATH=D:\develop1\Qwen3-Embedding-0.6B
RERANK_MODEL_PATH=D:\develop1\bge-reranker-base
```

### 4. 数据预处理与嵌入

**步骤1：预处理文档**

将法律文档放入 `knowledge_base/laws/` 和 `knowledge_base/cases/`，然后运行：

```bash
cd process-data
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

## 使用说明

### 提问示例

- "内蒙古自治区宗教事务条例第三条内容是什么？"
- "专利促进与保护条例的第5条内容是什么？"
- "我想了解有关家暴的法律"

### 查看原文

回答中的法条引用（如"第 26 条"）旁边会显示 📄**查看原文** 按钮，点击可：
- 查看法条完整原文
- 下载原文件
- 打开文件所在位置

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

### 文件筛选
```
POST /api/file/filter
{
  "law_name": "内蒙古自治区宗教事务条例",
  "article_number": "3"
}
```

### 获取文件内容
```
GET /api/file/content?file_path=xxx
```

## 项目优化点

1. **模型预加载**: 启动时预加载嵌入模型和重排模型，减少首次查询等待时间
2. **混合检索**: 向量检索 + BM25关键词检索，提升检索准确性
3. **法条匹配**: 支持多种格式的法条引用（"第26条"、"第 26 条"等）
4. **旧版DOC兼容**: 支持扩展名为.docx但实际为.doc格式的文件

## 注意事项

1. 确保Milvus服务正常运行
2. 嵌入模型和重排模型路径配置正确
3. API Key配置有效且有足够额度
4. 知识库文档建议为DOCX、PDF或TXT格式

## 免责声明

本系统提供的法律信息仅供参考，不构成法律意见或建议。具体法律问题请咨询专业律师。

## 许可证

MIT License
