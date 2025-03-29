import os
import uuid
import threading
import time
import json
import datetime
import logging
from logging.handlers import RotatingFileHandler
from flask import (
    Blueprint, flash, redirect, render_template, request, 
    url_for, current_app, send_from_directory, abort, jsonify
)
from werkzeug.utils import secure_filename
from app.utils import (
    allowed_file, pdf_to_word, pdf_to_excel, 
    pdf_to_ppt, pdf_to_markdown, extract_summary
)
from PyPDF2 import PdfReader

bp = Blueprint('pdf', __name__)

# 设置日志记录器
def setup_logger():
    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(current_app.root_path), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 统计日志记录器
    stat_logger = logging.getLogger('pdf_converter_stat')
    stat_logger.setLevel(logging.INFO)
    
    # 创建按大小滚动的文件处理器，单个文件最大10MB，保留30个旧文件
    stat_handler = RotatingFileHandler(
        os.path.join(log_dir, 'stat.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=30
    )
    stat_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(message)s'
    ))
    stat_logger.addHandler(stat_handler)
    
    return stat_logger

# 初始化日志记录器
stat_logger = None

@bp.before_app_request
def initialize_logger():
    global stat_logger
    if stat_logger is None:
        stat_logger = setup_logger()

def get_client_info():
    """获取客户端信息"""
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.user_agent.string
    referer = request.referrer or "direct"
    return {
        "ip": ip,
        "user_agent": user_agent,
        "referer": referer,
        "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

# 用于跟踪需要清理的文件
files_to_clean = {}

def schedule_file_cleanup(file_path, delay=1800):  # 默认30分钟
    """计划在指定延迟后删除文件"""
    def delete_later():
        time.sleep(delay)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"已清理文件: {file_path}")
        except Exception as e:
            print(f"清理文件时出错: {e}")
    
    thread = threading.Thread(target=delete_later)
    thread.daemon = True
    thread.start()

@bp.route('/', methods=['GET'])
def index():
    """应用首页"""
    return render_template('index.html')

@bp.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传请求"""
    # 获取客户端信息
    client_info = get_client_info()
    
    # 检查是否有文件
    if 'file' not in request.files:
        flash('没有选择文件')
        if stat_logger:
            stat_logger.warning(json.dumps({
                "event": "upload_failed",
                "reason": "no_file_selected",
                "client": client_info
            }))
        return redirect(url_for('pdf.index'))
    
    file = request.files['file']
    
    # 如果用户没有选择文件，浏览器也会提交一个没有文件名的空文件部分
    if file.filename == '':
        flash('没有选择文件')
        if stat_logger:
            stat_logger.warning(json.dumps({
                "event": "upload_failed",
                "reason": "empty_filename",
                "client": client_info
            }))
        return redirect(url_for('pdf.index'))
    
    # 检查文件类型
    if file and allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
        # 检查文件大小
        content = file.read()
        file_size = len(content)
        if file_size > current_app.config['MAX_CONTENT_LENGTH']:
            flash('文件太大，请上传小于16MB的文件')
            if stat_logger:
                stat_logger.warning(json.dumps({
                    "event": "upload_failed",
                    "reason": "file_too_large",
                    "file_size": file_size,
                    "client": client_info
                }))
            return redirect(url_for('pdf.index'))
        
        # 重置文件指针
        file.seek(0)
        
        # 获取原始文件名（保留完整原始名称，只在服务器端使用安全版本）
        orig_filename = file.filename  # 原始文件名，将用于输出文件
        filename = secure_filename(orig_filename)  # 安全版本，用于服务器存储
        base_name = os.path.splitext(orig_filename)[0]  # 不包含扩展名的原始文件名
        
        # 添加UUID前缀防止文件名冲突
        unique_id = str(uuid.uuid4())
        unique_filename = f"{unique_id}_{filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        
        # 保存上传的文件
        file.save(file_path)
        
        # 记录文件上传成功
        if stat_logger:
            stat_logger.info(json.dumps({
                "event": "upload_success",
                "file_id": unique_id,
                "original_filename": orig_filename,
                "file_size": file_size,
                "client": client_info
            }))
        
        # 检查转换类型
        conversion_type = request.form.get('conversion_type', 'word')
        
        # 提取PDF预览信息
        try:
            pdf = PdfReader(file_path)
            total_pages = len(pdf.pages)
            
            # 提取第一页的文本作为摘要
            first_page_text = ""
            if total_pages > 0:
                first_page_text = pdf.pages[0].extract_text()
                first_page_text = extract_summary(first_page_text, 200)
                
            # 记录PDF信息
            if stat_logger:
                stat_logger.info(json.dumps({
                    "event": "pdf_info",
                    "file_id": unique_id,
                    "total_pages": total_pages,
                    "file_size": file_size,
                    "client": client_info
                }))
        except Exception as e:
            error_message = str(e)
            print(f"提取PDF信息时出错: {error_message}")
            total_pages = 0
            first_page_text = ""
            
            # 记录PDF信息提取错误
            if stat_logger:
                stat_logger.error(json.dumps({
                    "event": "pdf_info_failed",
                    "file_id": unique_id,
                    "error": error_message,
                    "client": client_info
                }))
        
        # 根据转换类型确定输出扩展名
        output_ext_map = {
            'word': '.docx',
            'excel': '.xlsx',
            'ppt': '.pptx',
            'markdown': '.md'
        }
        output_ext = output_ext_map.get(conversion_type, '.docx')
        
        # 确定输出文件路径
        output_filename = f"{unique_id}{output_ext}"
        output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], output_filename)
        
        # 生成下载文件名（保留原始文件名，更改扩展名）
        download_filename = f"{base_name}{output_ext}"
        
        # 记录开始转换
        if stat_logger:
            stat_logger.info(json.dumps({
                "event": "conversion_started",
                "file_id": unique_id,
                "conversion_type": conversion_type,
                "original_filename": orig_filename,
                "client": client_info
            }))
        
        # 开始计时
        start_time = time.time()
        
        # 根据转换类型调用适当的转换函数
        try:
            if conversion_type == 'word':
                output_path = pdf_to_word(file_path, output_path)
            elif conversion_type == 'excel':
                output_path = pdf_to_excel(file_path, output_path)
            elif conversion_type == 'ppt':
                output_path = pdf_to_ppt(file_path, output_path)
            elif conversion_type == 'markdown':
                output_path = pdf_to_markdown(file_path, output_path)
            else:
                flash(f'不支持的转换类型: {conversion_type}')
                
                # 记录不支持的转换类型
                if stat_logger:
                    stat_logger.error(json.dumps({
                        "event": "conversion_failed",
                        "file_id": unique_id,
                        "error": f"不支持的转换类型: {conversion_type}",
                        "client": client_info
                    }))
                return redirect(url_for('pdf.index'))
            
            # 计算转换时间
            conversion_time = time.time() - start_time
            
            # 获取输出文件大小
            output_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            
            # 记录转换成功
            if stat_logger:
                stat_logger.info(json.dumps({
                    "event": "conversion_success",
                    "file_id": unique_id,
                    "conversion_type": conversion_type,
                    "original_filename": orig_filename,
                    "output_size": output_size,
                    "conversion_time": conversion_time,
                    "client": client_info
                }))
        except Exception as e:
            error_message = str(e)
            print(f"文件转换时出错: {error_message}")
            
            # 记录转换失败
            if stat_logger:
                stat_logger.error(json.dumps({
                    "event": "conversion_failed",
                    "file_id": unique_id,
                    "conversion_type": conversion_type,
                    "error": error_message,
                    "client": client_info
                }))
            
            flash(f'文件转换失败: {error_message}')
            return redirect(url_for('pdf.index'))
        
        # 安排上传的原始PDF在转换完成后清理
        schedule_file_cleanup(file_path)
        
        # 成功，重定向到成功页面
        download_url = url_for('pdf.download_file', 
                              filename=os.path.basename(output_path),
                              original_filename=download_filename)
        
        return redirect(url_for('pdf.success', 
                              download_url=download_url,
                              total_pages=total_pages,
                              filename=orig_filename,
                              summary=first_page_text))
    
    # 不支持的文件类型
    if stat_logger:
        stat_logger.warning(json.dumps({
            "event": "upload_failed",
            "reason": "unsupported_file_type",
            "filename": file.filename if file else "unknown",
            "client": client_info
        }))
    
    flash('不支持的文件类型，请上传PDF文件')
    return redirect(url_for('pdf.index'))

@bp.route('/success')
def success():
    """转换成功页面"""
    download_url = request.args.get('download_url')
    total_pages = request.args.get('total_pages', '未知')
    filename = request.args.get('filename', '文档')
    summary = request.args.get('summary', '')
    
    return render_template('success.html', 
                          download_url=download_url,
                          total_pages=total_pages,
                          filename=filename,
                          summary=summary)

@bp.route('/download/<filename>')
def download_file(filename):
    """处理文件下载请求"""
    try:
        # 获取客户端信息
        client_info = get_client_info()
        
        # 检查文件是否存在
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            if stat_logger:
                stat_logger.error(json.dumps({
                    "event": "download_failed",
                    "filename": filename,
                    "reason": "file_not_found",
                    "client": client_info
                }))
            abort(404)
            
        original_filename = request.args.get('original_filename', filename)
        
        # 记录下载成功
        if stat_logger:
            stat_logger.info(json.dumps({
                "event": "download_started",
                "filename": filename,
                "original_filename": original_filename,
                "file_size": os.path.getsize(file_path),
                "client": client_info
            }))
            
        # 安排在文件下载后30分钟删除
        schedule_file_cleanup(file_path, 1800)  # 30分钟
        
        return send_from_directory(current_app.config['UPLOAD_FOLDER'],
                                  filename,
                                  as_attachment=True,
                                  download_name=original_filename)
    except Exception as e:
        error_message = str(e)
        if stat_logger:
            stat_logger.error(json.dumps({
                "event": "download_failed",
                "filename": filename,
                "error": error_message,
                "client": client_info
            }))
        flash(f'下载文件时出错: {error_message}')
        return redirect(url_for('pdf.index'))
