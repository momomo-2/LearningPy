from socket import *

serverName = 'localhost'
serverPort = 12000

# 创建UDP套接字
serverSocket = socket(AF_INET, SOCK_DGRAM)

# 绑定套接字到地址和端口
serverSocket.bind((serverName, serverPort))

print('The server is ready to receive')

while True:
    # 接收客户端消息
    message, clientAddress = serverSocket.recvfrom(2048)
    
    # 将消息转换为大写
    modifiedMessage = message.decode().upper()
    
    # 发送修改后的消息回客户端
    serverSocket.sendto(modifiedMessage.encode(), clientAddress)