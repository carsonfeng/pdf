import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect

def create_app(test_config=None):
    # 创建和配置应用
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        UPLOAD_FOLDER=os.path.join(app.root_path, 'uploads'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 限制上传文件大小为16MB
        ALLOWED_EXTENSIONS={'pdf'}
    )

    if test_config is None:
        # 非测试模式下加载实例配置
        app.config.from_pyfile('config.py', silent=True)
    else:
        # 测试模式下加载测试配置
        app.config.from_mapping(test_config)

    # 确保实例文件夹存在
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except OSError:
        pass

    # 初始化CSRF保护
    csrf = CSRFProtect()
    csrf.init_app(app)

    # 注册路由
    from app import routes
    app.register_blueprint(routes.bp)

    return app
