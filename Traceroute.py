from socket import *
import os
import sys
import struct
import time
import select

ICMP_ECHO_REQUEST = 8
MAX_HOPS = 30          # número máximo de saltos (TTL)
TIMEOUT = 2.0          # tempo máximo de espera por resposta (segundos)
TRIES = 4              # ✅ 4 pings por TTL, como o PDF pede


def checksum(string):
    """
    Calcula o checksum do cabeçalho/dados ICMP.
    Mesma lógica usada no laboratório de ICMP Pinger.
    """
    csum = 0
    countTo = (len(string) // 2) * 2

    count = 0
    while count < countTo:
        thisVal = string[count + 1] * 256 + string[count]
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count = count + 2

    if countTo < len(string):
        csum = csum + string[-1]
        csum = csum & 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff

    # inverter bytes (little/big endian)
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer


def build_packet():
    """
    Monta o pacote ICMP Echo Request:
      - Tipo = 8 (echo request)
      - Código = 0
      - Checksum calculado
      - ID = PID do processo
      - Sequência = 1
      - Dados = timestamp (double)
    """
    myID = os.getpid() & 0xFFFF
    myChecksum = 0

    # Cabeçalho temporário com checksum 0
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, myID, 1)
    data = struct.pack("d", time.time())

    # Calcula checksum sobre cabeçalho + dados
    myChecksum = checksum(header + data)

    # Ajuste de endianess (especialmente para macOS)
    if sys.platform == 'darwin':
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)

    # Cabeçalho final com checksum correto
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, myID, 1)
    packet = header + data
    return packet


def get_route(hostname):
    """
    Implementa o traceroute:
      - TTL de 1 até MAX_HOPS
      - Para cada TTL, envia TRIES (=4) mensagens ICMP
      - Usa select() e timeout para esperar resposta
      - Mostra: TTL, 4 RTTs (ou *), IP e NOME (extra do laboratório)
    """
    destAddr = gethostbyname(hostname)
    print(f"Traceroute para {hostname} ({destAddr}), máximo de {MAX_HOPS} saltos:")
    print(f"(Cada linha tem {TRIES} tentativas de ping por TTL)\n")

    for ttl in range(1, MAX_HOPS + 1):
        resultados = []      # guarda rtts ou '*' de cada tentativa
        current_ip = None
        current_host = None
        reached_dest = False
        unreachable = False
        type_label = ""

        for tries in range(TRIES):
            # Criar socket raw para ICMP
            mySocket = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP)
            mySocket.setsockopt(IPPROTO_IP, IP_TTL, struct.pack('I', ttl))
            mySocket.settimeout(TIMEOUT)

            try:
                # Monta pacote ICMP
                packet = build_packet()
                send_time = time.time()

                # Envia pacote para o destino
                mySocket.sendto(packet, (hostname, 0))

                # Aguarda até TIMEOUT por alguma resposta
                ready = select.select([mySocket], [], [], TIMEOUT)
                if ready[0] == []:
                    resultados.append("*")
                    continue

                recvPacket, addr = mySocket.recvfrom(1024)
                recv_time = time.time()

                # Cabeçalho IP costuma ter 20 bytes, cabeçalho ICMP vem depois disso
                icmp_header = recvPacket[20:28]
                icmp_type, code, icmp_checksum, packet_id, sequence = struct.unpack(
                    "bbHHh", icmp_header
                )

                rtt_ms = (recv_time - send_time) * 1000
                ip_addr = addr[0]

                # EXTRA: tentar resolver nome do roteador a partir do IP
                try:
                    host_name = gethostbyaddr(ip_addr)[0]
                except Exception:
                    host_name = ip_addr  # se não resolver, fica igual

                current_ip = ip_addr
                current_host = host_name
                resultados.append(f"{rtt_ms:.0f}ms")

                if icmp_type == 11:  # Time Exceeded (roteador intermediário)
                    type_label = ""
                    # continua para mais tentativas com mesmo TTL

                elif icmp_type == 3:  # Destination Unreachable
                    type_label = "[Destination unreachable]"
                    unreachable = True

                elif icmp_type == 0:  # Echo Reply (chegou ao destino)
                    type_label = "[Destino]"
                    reached_dest = True

                else:
                    type_label = f"[ICMP tipo {icmp_type}]"

            except timeout:
                resultados.append("*")

            finally:
                mySocket.close()

        # Impressão da linha por TTL
        if current_ip is None:
            # todas as tentativas deram timeout
            print(f"{ttl:2d}  {'  '.join(resultados)}")
        else:
            print(f"{ttl:2d}  {'  '.join(resultados):20}  {current_ip}  ({current_host}) {type_label}")

        # Se chegou ao destino ou erro definitivo, para o laço
        if reached_dest or unreachable:
            break


if __name__ == "__main__":
    # Você pode trocar o destino aqui
    destino = "google.com"
    get_route(destino)
