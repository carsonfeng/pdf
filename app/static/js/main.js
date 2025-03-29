document.addEventListener('DOMContentLoaded', function() {
    // 拖放功能
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.querySelector('.upload-btn');
    
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            dropArea.classList.add('highlight');
        }
        
        function unhighlight() {
            dropArea.classList.remove('highlight');
        }
        
        dropArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                fileInput.files = files;
                handleFiles(files);
            }
        }
        
        if (uploadButton) {
            uploadButton.addEventListener('click', function() {
                fileInput.click();
            });
        }
        
        if (fileInput) {
            fileInput.addEventListener('change', function() {
                if (fileInput.files.length > 0) {
                    handleFiles(fileInput.files);
                }
            });
        }
    }
    
    function handleFiles(files) {
        const file = files[0];
        if (file) {
            // 检查文件类型
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                showAlert('请选择PDF文件', 'warning');
                return;
            }
            
            // 检查文件大小
            if (file.size > 16 * 1024 * 1024) { // 16MB
                showAlert('文件太大，请上传小于16MB的文件', 'warning');
                return;
            }
            
            // 显示已选择的文件
            const fileInfo = document.getElementById('file-info');
            if (fileInfo) {
                fileInfo.innerHTML = `
                    <div class="alert alert-success">
                        <i class="bi bi-file-earmark-pdf me-2"></i>
                        已选择: <strong>${file.name}</strong> (${formatFileSize(file.size)})
                    </div>
                `;
                fileInfo.style.display = 'block';
            }
            
            // 激活"转换"按钮
            const convertBtn = document.getElementById('convert-btn');
            if (convertBtn) {
                convertBtn.disabled = false;
                convertBtn.classList.add('animate-pulse');
            }
            
            // 显示格式选择步骤
            const formatStep = document.getElementById('format-step');
            if (formatStep) {
                formatStep.classList.add('animate-fade-in');
            }
        }
    }
    
    // 格式选择卡片点击事件
    const formatCards = document.querySelectorAll('.format-card');
    if (formatCards.length > 0) {
        formatCards.forEach(card => {
            card.addEventListener('click', function() {
                // 移除所有卡片的选中状态
                formatCards.forEach(c => c.classList.remove('selected'));
                
                // 添加当前卡片的选中状态
                this.classList.add('selected');
                
                // 选中对应的单选按钮
                const radio = this.querySelector('input[type="radio"]');
                if (radio) {
                    radio.checked = true;
                }
            });
        });
    }
    
    // 表单提交前显示加载指示器
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            // 检查文件是否已选择
            if (fileInput && fileInput.files.length === 0) {
                e.preventDefault();
                showAlert('请先选择PDF文件', 'warning');
                return;
            }
            
            // 显示加载指示器
            const convertBtn = document.getElementById('convert-btn');
            if (convertBtn) {
                convertBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>转换中...';
                convertBtn.disabled = true;
            }
            
            // 显示进度条
            const progressContainer = document.getElementById('progress-container');
            if (progressContainer) {
                progressContainer.style.display = 'block';
                
                // 模拟进度
                let progress = 0;
                const progressBar = document.querySelector('.progress-bar');
                const progressInterval = setInterval(function() {
                    progress += Math.random() * 10;
                    if (progress > 90) {
                        progress = 90; // 最多到90%，剩下的10%在服务器完成时更新
                        clearInterval(progressInterval);
                    }
                    progressBar.style.width = progress + '%';
                    progressBar.setAttribute('aria-valuenow', progress);
                }, 300);
            }
        });
    }
    
    // 自动下载功能（成功页面）
    const urlParams = new URLSearchParams(window.location.search);
    const downloadUrl = urlParams.get('download_url');
    
    if (downloadUrl) {
        setTimeout(function() {
            window.location.href = downloadUrl;
        }, 1000);
        
        // 设置下载按钮链接
        const downloadBtn = document.getElementById('downloadBtn');
        if (downloadBtn) {
            downloadBtn.setAttribute('href', downloadUrl);
        }
        
        // 添加复制链接功能
        const copyLinkBtn = document.getElementById('copyLinkBtn');
        if (copyLinkBtn) {
            copyLinkBtn.addEventListener('click', function() {
                const tempInput = document.createElement('input');
                tempInput.value = window.location.origin + downloadUrl;
                document.body.appendChild(tempInput);
                tempInput.select();
                document.execCommand('copy');
                document.body.removeChild(tempInput);
                
                // 显示复制成功提示
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="bi bi-check-lg me-1"></i>已复制';
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 2000);
            });
        }
    }
    
    // 工具函数
    function formatFileSize(bytes) {
        if (bytes < 1024) {
            return bytes + ' B';
        } else if (bytes < 1024 * 1024) {
            return (bytes / 1024).toFixed(2) + ' KB';
        } else {
            return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
        }
    }
    
    function showAlert(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        const container = document.querySelector('.container');
        container.insertBefore(alertDiv, container.firstChild);
        
        // 自动关闭
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => {
                alertDiv.remove();
            }, 300);
        }, 5000);
    }
    
    // 暗色模式切换
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    if (darkModeToggle) {
        // 检查用户偏好
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.body.classList.add('dark-mode');
            darkModeToggle.innerHTML = '<i class="bi bi-sun"></i>';
        }
        
        darkModeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            if (document.body.classList.contains('dark-mode')) {
                this.innerHTML = '<i class="bi bi-sun"></i>';
                localStorage.setItem('darkMode', 'enabled');
            } else {
                this.innerHTML = '<i class="bi bi-moon"></i>';
                localStorage.setItem('darkMode', 'disabled');
            }
        });
        
        // 检查本地存储
        if (localStorage.getItem('darkMode') === 'enabled') {
            document.body.classList.add('dark-mode');
            darkModeToggle.innerHTML = '<i class="bi bi-sun"></i>';
        }
    }
}); 