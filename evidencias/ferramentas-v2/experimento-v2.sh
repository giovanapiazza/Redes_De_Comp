#!/bin/bash
# Roteiro do experimento da Secao 4.3. Escrito com apoio de IA (Anthropic Claude).
# Experimento V2 com captura dumpcap (Wireshark) na interface lo, sem root
# (usuario no grupo wireshark). Uso: experimento-equipe.sh DIR_V2 DIR_SAIDA
V2=$1; OUT=$(realpath "$2"); PORTA=8095; URL=http://127.0.0.1:$PORTA
cd "$V2"
dumpcap -q -i lo -s 128 -F pcap -w "$OUT/experimento-v2.pcap" -f "tcp port $PORTA" 2> "$OUT/dumpcap.txt" &
TD=$!
sleep 2
./server $PORTA www 6000 taxas.txt > "$OUT/painel.txt" 2> "$OUT/server.log" &
SV=$!
sleep 2
cliente() { # ip, rotulo, objeto
  curl -s --interface $1 -o /dev/null -o /dev/null $URL/ $URL/$3 \
    -w "$2,$1,%{url_effective},%{http_code},%{size_download},%{time_total},%{speed_download}\n" >> "$OUT/curl.csv"
}
echo "cenario,ip,url,http_code,bytes,tempo_s,bytes_por_s" > "$OUT/curl.csv"
# A: tres IPs com taxas diferentes, em paralelo
cliente 127.0.0.1 A_tres_ips imagem1.bmp & A1=$!
cliente 127.0.0.3 A_tres_ips imagem1.bmp & A3=$!
cliente 127.0.0.4 A_tres_ips imagem1.bmp & A4=$!
sleep 3
# B: admissao. reservado 2000+1500+1000=4500; .2 pede 3000 -> 503
curl -s --interface 127.0.0.2 -o /dev/null $URL/imagem2.bmp -w "B_admissao,127.0.0.2,%{url_effective},%{http_code},%{size_download},%{time_total},%{speed_download}\n" >> "$OUT/curl.csv"
wait $A1 $A3 $A4
# C: duas conexoes do mesmo IP (127.0.0.1, 2000 kbps) dividem a taxa
cliente 127.0.0.1 C_mesmo_ip imagem2.bmp & C1=$!
cliente 127.0.0.1 C_mesmo_ip imagem2.bmp & C2=$!
wait $C1 $C2
# D: .2 de novo, agora com reserva livre -> 200
curl -s --interface 127.0.0.2 -o /dev/null $URL/index.html -w "D_readmissao,127.0.0.2,%{url_effective},%{http_code},%{size_download},%{time_total},%{speed_download}\n" >> "$OUT/curl.csv"
sleep 2
kill $SV; wait $SV
sleep 1; kill -INT $TD; wait $TD
uname -a > "$OUT/maquina.txt"
echo FIM
