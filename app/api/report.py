# app/api/report.py — REST 接口层
# - POST   /api/report/upload          上传财报 PDF，启动流水线
# - GET    /api/report/status/{sid}    查询任务状态 + 进度
# - GET    /api/report/{report_id}     获取报告 Markdown 内容（JSON）
# - GET    /api/report/download/{rid}  下载报告文件
# - POST   /api/report/chat            多轮问答
# - 统一响应信封 { code, data / msg }
