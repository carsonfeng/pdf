# PDF转换工具

这是一个基于Python的Web应用，提供多种PDF转换功能，包括：

1. PDF转Word
2. PDF转Excel 
3. PDF转PowerPoint
4. PDF转Markdown

## 功能特点

- 简洁的Web界面
- 多种文档格式转换
- 安全的文件处理
- 快速的转换速度

## 安装

1. 克隆仓库
```bash
git clone https://github.com/username/pdf-converter.git
cd pdf-converter
```

2. 创建并激活虚拟环境（推荐）
```bash
python -m venv venv
source venv/bin/activate  # 在Windows上使用: venv\Scripts\activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法

1. 启动应用
```bash
python run.py
```

2. 在浏览器中访问应用
```
http://localhost:5000
```

3. 上传PDF文件并选择所需的转换格式

## 部署

本应用可以轻松部署到各种平台：

### 使用Docker部署

1. 构建Docker镜像
```bash
docker build -t pdf-converter .
```

2. 运行Docker容器
```bash
docker run -p 5000:5000 pdf-converter
```

### 部署到服务器

可以使用Gunicorn作为WSGI服务器，结合Nginx作为反向代理，部署到生产环境。

## 技术栈

- Flask: Web框架
- PyPDF2/pdfminer.six: PDF处理
- python-docx: Word文档生成
- openpyxl: Excel文档生成
- python-pptx: PowerPoint演示文稿生成
- markdown: Markdown转换
