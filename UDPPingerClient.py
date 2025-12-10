from socket import *
import time

serverName = '127.0.0.1'
serverPort = 12000

clientSocket = socket(AF_INET, SOCK_DGRAM)
clientSocket.settimeout(1.0)

print("Iniciando UDP Ping...\n")

for sequence in range(1, 11):
    message = f"Ping {sequence} {time.perf_counter()}"
    send_time = time.perf_counter()

    try:
        clientSocket.sendto(message.encode(), (serverName, serverPort))
        data, address = clientSocket.recvfrom(1024)

        rtt = time.perf_counter() - send_time
        print(f"Resposta: {data.decode()} | RTT = {rtt:.8f} s")

    except timeout:
        print("Request timed out")

clientSocket.close()
