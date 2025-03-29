import os
import uuid
import threading
import time
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
    # 检查是否有文件
    if 'file' not in request.files:
        flash('没有选择文件')
        return redirect(url_for('pdf.index'))
    
    file = request.files['file']
    
    # 如果用户没有选择文件，浏览器也会提交一个没有文件名的空文件部分
    if file.filename == '':
        flash('没有选择文件')
        return redirect(url_for('pdf.index'))
    
    # 检查文件类型
    if file and allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
        # 检查文件大小
        content = file.read()
        if len(content) > current_app.config['MAX_CONTENT_LENGTH']:
            flash('文件太大，请上传小于16MB的文件')
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
        except Exception as e:
            print(f"提取PDF信息时出错: {e}")
            total_pages = 0
            first_page_text = ""
        
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
        
        # 根据转换类型调用适当的转换函数
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
        # 检查文件是否存在
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            abort(404)
            
        original_filename = request.args.get('original_filename', filename)
        
        # 安排在文件下载后30分钟删除
        schedule_file_cleanup(file_path, 1800)  # 30分钟
        
        return send_from_directory(current_app.config['UPLOAD_FOLDER'],
                                  filename,
                                  as_attachment=True,
                                  download_name=original_filename)
    except Exception as e:
        flash(f'下载文件时出错: {str(e)}')
        return redirect(url_for('pdf.index'))

# 新增API路由：获取PDF信息
@bp.route('/api/pdf-info', methods=['POST'])
def get_pdf_info():
    """返回PDF文件的基本信息，如页数、大小等"""
    if 'file' not in request.files:
        return jsonify({'error': '未找到文件'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    if file and allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
        try:
            # 读取文件内容
            content = file.read()
            file_size = len(content)
            
            if file_size > current_app.config['MAX_CONTENT_LENGTH']:
                return jsonify({'error': '文件太大，请上传小于16MB的文件'}), 400
            
            # 创建临时文件
            temp_file_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], 
                f"temp_{str(uuid.uuid4())}.pdf"
            )
            
            # 保存临时文件
            with open(temp_file_path, 'wb') as f:
                f.write(content)
            
            # 读取PDF信息
            pdf = PdfReader(temp_file_path)
            total_pages = len(pdf.pages)
            
            # 提取第一页文本作为摘要
            summary = ""
            if total_pages > 0:
                summary = pdf.pages[0].extract_text()
                summary = extract_summary(summary, 200)
            
            # 删除临时文件
            os.remove(temp_file_path)
            
            # 返回信息
            return jsonify({
                'success': True,
                'filename': file.filename,
                'size': file_size,
                'size_formatted': f"{file_size/1024/1024:.2f} MB" if file_size > 1024*1024 else f"{file_size/1024:.2f} KB",
                'pages': total_pages,
                'summary': summary
            })
        except Exception as e:
            # 确保临时文件被删除
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return jsonify({'error': f'处理PDF时出错: {str(e)}'}), 500
    
    return jsonify({'error': '不支持的文件类型'}), 400

@bp.errorhandler(413)
def request_entity_too_large(error):
    """处理文件过大错误"""
    flash('文件太大，请上传小于16MB的文件')
    return redirect(url_for('pdf.index')), 413

@bp.errorhandler(404)
def not_found(error):
    """处理404错误"""
    flash('请求的资源不存在')
    return redirect(url_for('pdf.index')), 404

@bp.errorhandler(500)
def internal_server_error(error):
    """处理500错误"""
    flash('服务器内部错误，请稍后再试')
    return redirect(url_for('pdf.index')), 500
