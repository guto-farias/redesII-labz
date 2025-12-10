from socket import *
import os
import sys
import struct
import time
import select
import binascii

ICMP_ECHO_REQUEST = 8

def checksum(source_bytes):
    """
    Calcula o checksum ICMP em Python 3, trabalhando com bytes.
    """
    if isinstance(source_bytes, str):
        # se vier str por algum motivo, converte para bytes em latin-1
        source_bytes = source_bytes.encode('latin-1')

    csum = 0
    countTo = (len(source_bytes) // 2) * 2
    count = 0

    # soma de 16 bits
    while count < countTo:
        thisVal = source_bytes[count+1] * 256 + source_bytes[count]
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count += 2

    # se sobrar um byte ímpar
    if countTo < len(source_bytes):
        csum = csum + source_bytes[-1]
        csum = csum & 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    # inverte byte order (big/little endian)
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer


# Mapeamento de alguns erros ICMP para mensagens amigáveis
ICMP_ERROR_MAP = {
    (3, 0): "Destination network unreachable",
    (3, 1): "Destination host unreachable",
    (3, 2): "Destination protocol unreachable",
    (3, 3): "Destination port unreachable",
    (3, 4): "Fragmentation needed and DF set",
    (3, 5): "Source route failed",
    (11, 0): "Time exceeded in transit",
    (11, 1): "Fragment reassembly time exceeded",
}

def describe_icmp_error(icmp_type, code):
    if (icmp_type, code) in ICMP_ERROR_MAP:
        return ICMP_ERROR_MAP[(icmp_type, code)]
    if icmp_type == 3:
        return "Destination unreachable (unknown code {})".format(code)
    elif icmp_type == 11:
        return "Time exceeded (unknown code {})".format(code)
    else:
        return "ICMP error (type {} code {})".format(icmp_type, code)

def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout

    while True:
        startedSelect = time.time()
        ready = select.select([mySocket], [], [], timeLeft)
        timeInSelect = time.time() - startedSelect

        if ready[0] == []:
            return "Request timed out."

        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        # ======= PARTE DO LAB: extrair cabeçalho IP e ICMP =======
        # Cabeçalho IP (primeiros 20 bytes)
        ipHeader = recPacket[:20]
        iph = struct.unpack("!BBHHHBBH4s4s", ipHeader)
        ttl = iph[5]

        # Cabeçalho ICMP começa depois (bytes 20..28)
        icmpHeader = recPacket[20:28]
        icmph = struct.unpack("bbHHh", icmpHeader)

        icmpType = icmph[0]
        code = icmph[1]
        packetID = icmph[3]

        # Tratamento de Echo Reply (tipo 0) – caso de sucesso
        if packetID == ID and icmpType == 0:
            timeSent = struct.unpack("d", recPacket[28:28 + 8])[0]
            rtt = (timeReceived - timeSent) * 1000.0  # ms
            return f"Reply from {destAddr}: TTL={ttl} RTT={round(rtt, 3)} ms"

        # Tratamento de erros ICMP (extra 2)
        if icmpType != 0:
            desc = describe_icmp_error(icmpType, code)
            return f"ICMP error from {destAddr}: {desc} (type {icmpType} code {code})"
        # =========================================================

        timeLeft -= timeInSelect
        if timeLeft <= 0:
            return "Request timed out."

def sendOnePing(mySocket, destAddr, ID):
    myChecksum = 0

    # Header: type (8), code (8), checksum (16), id (16), sequence (16)
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())

    # Calcula checksum
    myChecksum = checksum(header + data)

    if sys.platform == 'darwin':
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data

    mySocket.sendto(packet, (destAddr, 1))  # porta dummy

def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")
    mySocket = socket(AF_INET, SOCK_RAW, icmp)

    myID = os.getpid() & 0xFFFF

    sendOnePing(mySocket, destAddr, myID)
    result = receiveOnePing(mySocket, myID, timeout, destAddr)

    mySocket.close()
    return result

def ping_multiple_locations(timeout=1):
    locations = {
        "América (USA)": "171.67.215.200",  # Stanford (não-anycast)
        "Europa (Reino Unido)": "1.1.1.1", # cloudflare usa anycast
        "Ásia (Singapura)": "asia.pool.ntp.org",
        "Oceania (Austrália)": "203.26.27.38"  # Univ. de Melbourne
    }

    print("=== ICMP Pinger – Teste Global (4 Continentes x 4 Pings) ===\n")

    total_sent = 0
    total_received = 0
    total_rtts = []

    for region, host in locations.items():
        print(f"\n>>> Testando {region} ({host})\n")

        dest = gethostbyname(host)
        sent = 0
        received = 0
        rtts = []

        # Agora enviaremos 4 pings por região
        for i in range(4):
            sent += 1
            result = doOnePing(dest, timeout)
            print(result)

            if result.startswith("Reply from"):
                try:
                    rtt = float(result.split("RTT=")[1].split(" ")[0])
                    rtts.append(rtt)
                    received += 1
                except:
                    pass
            elif not result.startswith("Request timed out."):
                # ICMP error conta como recebido, porém sem RTT
                received += 1

            time.sleep(1)

        # Estatísticas por região
        print(f"\n--- Estatísticas de {region} ---")
        loss = (sent - received) / sent * 100
        print(f"{sent} packets enviados, {received} recebidos, {round(loss,2)}% de perda")

        if rtts:
            print(f"RTT min/avg/max = {round(min(rtts),3)}/{round(sum(rtts)/len(rtts),3)}/{round(max(rtts),3)} ms")

        # Soma para estatísticas globais
        total_sent += sent
        total_received += received
        total_rtts.extend(rtts)

    # Estatísticas globais (somando tudo)
    print("\n=== Estatísticas Globais ===")
    total_loss = (total_sent - total_received) / total_sent * 100
    print(f"{total_sent} packets enviados, {total_received} recebidos, {round(total_loss,2)}% de perda")

    if total_rtts:
        print(f"RTT min/avg/max = {round(min(total_rtts),3)}/{round(sum(total_rtts)/len(total_rtts),3)}/{round(max(total_rtts),3)} ms")


if __name__ == "__main__":
    ping_multiple_locations(timeout=1)
