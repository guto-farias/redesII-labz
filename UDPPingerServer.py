import random
from socket import *

# Criar um socket UDP
serverSocket = socket(AF_INET, SOCK_DGRAM)

# Atribuir endereço IP e número da porta ao socket
serverSocket.bind(('', 12000))

while True:
    # Gerar número aleatório entre 0 e 10
    rand = random.randint(0, 10)

    # Receber o pacote do cliente junto com o endereço de origem
    message, address = serverSocket.recvfrom(1024)

    # Colocar a mensagem recebida em maiúsculas
    message = message.upper()

    # Se o número rand for menor que 4, consideramos que o pacote foi perdido e não respondemos
    if rand < 4:
        continue

    # Caso contrário, o servidor responde
    serverSocket.sendto(message, address)
