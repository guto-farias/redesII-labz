from socket import *

# Corpo da mensagem
msg = "\r\nEu amo redes de computadores!"
endmsg = "\r\n.\r\n"

# Credenciais do Mailtrap
mailserver = ("sandbox.smtp.mailtrap.io", 2525)
username = "20be3d4c32ca61"
password = "f343d78e7f9b68"

# 1. Criar socket TCP
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect(mailserver)

# 2. Ler mensagem inicial (220)
recv = clientSocket.recv(1024).decode()
print(recv)
if recv[:3] != '220':
    print('220 resposta não recebida do servidor.')

# 3. HELO
heloCommand = 'HELO alice\r\n'
clientSocket.send(heloCommand.encode())
recv1 = clientSocket.recv(1024).decode()
print(recv1)

# 4. Autenticação LOGIN (Mailtrap exige AUTH LOGIN)
import base64

clientSocket.send("AUTH LOGIN\r\n".encode())
recvAuth = clientSocket.recv(1024).decode()
print(recvAuth)

# Envia username em base64
clientSocket.send((base64.b64encode(username.encode()).decode() + "\r\n").encode())
recvUser = clientSocket.recv(1024).decode()
print(recvUser)

# Envia password em base64
clientSocket.send((base64.b64encode(password.encode()).decode() + "\r\n").encode())
recvPass = clientSocket.recv(1024).decode()
print(recvPass)

# 5. MAIL FROM
mailFrom = "MAIL FROM:<remetente@mailtrap.test>\r\n"
clientSocket.send(mailFrom.encode())
recv2 = clientSocket.recv(1024).decode()
print(recv2)

# 6. RCPT TO
rcptTo = "RCPT TO:<destinatario@mailtrap.test>\r\n"
clientSocket.send(rcptTo.encode())
recv3 = clientSocket.recv(1024).decode()
print(recv3)

# 7. DATA
dataCommand = "DATA\r\n"
clientSocket.send(dataCommand.encode())
recv4 = clientSocket.recv(1024).decode()
print(recv4)

# 8. Corpo do e-mail
clientSocket.send(msg.encode())

# 9. Fim do corpo
clientSocket.send(endmsg.encode())
recv5 = clientSocket.recv(1024).decode()
print(recv5)

# 10. QUIT
quitCommand = "QUIT\r\n"
clientSocket.send(quitCommand.encode())
recv6 = clientSocket.recv(1024).decode()
print(recv6)

clientSocket.close()
