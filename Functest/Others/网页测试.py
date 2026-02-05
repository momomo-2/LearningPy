import socket

from flask import Flask


def get_local_ipv4():                             #读取IPv4
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print("获取 IPv4 地址时出错: {e}")

app = Flask(__name__)


@app.route('/')
def index():
    return '你瞅啥'

'''
@app.route('/wtf')
def wtf():
 '''

if __name__ == '__main__':
    app.run(host=str(get_local_ipv4()),port=8080)  #IP每周都会变
