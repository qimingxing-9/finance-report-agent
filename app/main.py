# app/main.py — FastAPI 应用入口
# - 创建 FastAPI 实例，注册路由
# - lifespan 管理生命周期：启动时初始化连接（Redis/MySQL/Milvus），关闭时释放
# - 挂载 api/report.py 的 5 个路由
