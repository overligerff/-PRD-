# PRD Agent Ollama

基于 Ollama 的产品需求文档（PRD）生成代理。

## 快速开始

### 环境要求

- Python 3.10+
- Ollama 服务

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

复制 `.env.example` 文件并修改配置：

```bash
cp .env.example .env
```

### 启动应用

```bash
streamlit run app.py
```

## 使用说明

1. 确保 Ollama 服务已启动：`ollama serve`
2. 拉取所需模型：`ollama pull llama3`
3. 启动 Streamlit 应用

## 项目结构

```
prd_agent_ollama/
├── app.py              # Streamlit 主程序
├── requirements.txt     # 依赖列表
├── .env.example        # 环境变量示例
├── .env.example.txt    # 环境变量示例（可选）
└── README.md.md        # 快速启动说明
```
