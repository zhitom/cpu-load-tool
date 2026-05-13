# 使用 manylinux2014 镜像（glibc 2.17）来打包
# docker build -t cpu-load-tool .&&docker run --rm cpu-load-tool cat /output/cpu-load-tool > ./dist/cpu-load-tool
# 使用 Nuitka 替代 PyInstaller（不需要共享库）
FROM quay.io/pypa/manylinux2014_x86_64

# 激活 Python 3.9 环境
ENV PATH=/opt/python/cp39-cp39/bin:$PATH

# 配置 pip 使用清华镜像源（国内加速）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set global.extra-index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip config set global.trusted-host "pypi.tuna.tsinghua.edu.cn mirrors.aliyun.com"

# 安装 Nuitka 和依赖（使用国内镜像）
# 解压 manylinux 静态库（Nuitka 需要）
RUN pip install nuitka psutil numpy \
    && cd /opt/_internal && tar xf static-libs-for-embedding-only.tar.xz \
    && echo "ip_resolve=4" >> /etc/yum.conf \
    && yum install -y patchelf

# 复制代码到容器
COPY cpu-load-tool.py /app/
WORKDIR /app

# 使用 Nuitka 编译（生成单个可执行文件）
RUN python3.9 -m nuitka \
    --onefile \
    --standalone \
    --remove-output \
    --output-filename=cpu-load-tool \
    --output-dir=/output \
    cpu-load-tool.py
    
# 验证 glibc 版本要求
RUN echo "========================================" \
    && echo "构建完成！可执行文件: /output/cpu-load-tool" \
    && echo "glibc 版本要求:" \
    &&  readelf -V /output/cpu-load-tool || true


