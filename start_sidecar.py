import os
import subprocess

os.environ['TEMI_IP'] = '192.168.31.121'
os.environ['TEMI_PORT'] = '8175'
os.environ['LOG_LEVEL'] = 'INFO'

result = subprocess.run(
    ['uvicorn', 'server:app', '--host', '127.0.0.1', '--port', '8091'],
    cwd=r'D:\University\fyp\temi\FeishuCLassmate\temi-sidecar',
)
