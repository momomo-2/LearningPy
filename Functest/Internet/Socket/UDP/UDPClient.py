from socket import *

serverName = 'localhost'
serverPort = 12000

# 创建UDP套接字
clientSocket = socket(AF_INET, SOCK_DGRAM)

# 获取用户输入
message = input('Input lowercase sentence: ')

# 发送消息到服务器
clientSocket.sendto(message.encode(), (serverName, serverPort))

# 接收服务器返回的消息
modifiedMessage, serverAddress = clientSocket.recvfrom(2048)

# 打印接收到的消息
print(modifiedMessage.decode())

# 关闭套接字
clientSocket.close()

#等待关闭
input("Press Enter to close...")