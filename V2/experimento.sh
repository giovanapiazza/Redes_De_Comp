#!/bin/bash
# experimento da entrega 3: varios clientes ao mesmo tempo, cada um de um IP diferente
# (no linux da pra usar 127.0.0.2, 127.0.0.3... tudo cai no loopback)
# roda com: bash experimento.sh
# se rodar com sudo ele tambem grava um pcap pra abrir no wireshark
#
# taxas.txt: 127.0.0.1=2000  127.0.0.2=3000  127.0.0.3=1500  127.0.0.4 nao ta (=1000 padrao)
# vazao maxima do servidor = 5000 kbps

PORTA=8095
VAZAO=5000
SAIDA=../evidencias/experimento-repetido-v2
mkdir -p $SAIDA

# arquivo de 1 MB pra cada download levar alguns segundos (com as imagens de 12 MB demora demais)
head -c 1048576 /dev/urandom > www/medio.bin

if [ "$(id -u)" = "0" ] && command -v tcpdump >/dev/null; then
    echo "rodando como root, vou capturar com tcpdump"
    tcpdump -i lo -s 0 -w $SAIDA/experimento.pcap tcp port $PORTA 2>/dev/null &
    TCPDUMP=$!
    sleep 1
fi

./server $PORTA www $VAZAO taxas.txt > $SAIDA/painel_raw.txt 2> $SAIDA/server.log &
SERVIDOR=$!
sleep 2

echo "cenario,ip,taxa_config_kbps,http_code,bytes,tempo_s,vazao_kbps" > $SAIDA/resultados.csv

# baixa o html e depois o medio.bin na mesma conexao (assim o servidor calcula o RTT)
# $1 = cenario  $2 = ip de origem  $3 = taxa que ta no taxas.txt
cliente() {
    R=$(curl --noproxy '*' -s --interface $2 -o /dev/null http://$2:$PORTA/ -o /dev/null \
        -w "%{http_code} %{size_download} %{time_total} %{speed_download}\n" http://$2:$PORTA/medio.bin | tail -n 1)
    # o curl imprime o -w pra CADA arquivo (achei que era so pro ultimo e o csv saiu com os dados do html),
    # por isso o \n e o tail -n 1 pra ficar so com a linha do medio.bin
    set -- $1 $2 $3 $R
    # VAZAO_KBPS=$(( $7 * 8 / 1000 ))  # ERRADO: o bash nao faz conta com virgula, deu erro de sintaxe
    VAZAO_KBPS=$(echo "$7" | awk '{printf "%.1f", $1 * 8 / 1000}')
    echo "$1,$2,$3,$4,$5,$6,$VAZAO_KBPS" >> $SAIDA/resultados.csv
}

# pega so o ultimo "quadro" do painel (cada quadro comeca com =====) e tira os codigos de limpar tela
foto_painel() {
    awk '/=====/{q=""} {q=q $0 "\n"} END{printf "%s", q}' $SAIDA/painel_raw.txt | sed 's/\x1b\[[0-9;]*[HJ]//g' > $1
}

echo "cenario 1: um cliente sozinho (127.0.0.1, 2000 kbps)"
cliente 1_sozinho 127.0.0.1 2000
sleep 1

echo "cenario 2: tres IPs diferentes ao mesmo tempo (2000 + 1500 + 1000 = 4500 de 5000)"
cliente 2_tres_ips 127.0.0.1 2000 & P1=$!
cliente 2_tres_ips 127.0.0.3 1500 & P2=$!
cliente 2_tres_ips 127.0.0.4 1000 & P3=$!
sleep 1
echo "cenario 3: chega o 127.0.0.2 (3000 kbps) com 4500 em uso -> tem que ser recusado"
cliente 3_admissao 127.0.0.2 3000
# tira uma "foto" do painel enquanto os 3 tao baixando
sleep 2
foto_painel $SAIDA/painel_cenario2.txt
# sleep 10  # antes tava assim mas as vezes o cenario 2 nao tinha terminado
# wait      # ERRADO: o wait sozinho espera o servidor tambem (que ta em background) e trava pra sempre
wait $P1 $P2 $P3
sleep 1

echo "cenario 4: duas conexoes do mesmo IP (127.0.0.1) dividindo 2000 kbps"
cliente 4_mesmo_ip 127.0.0.1 2000 & P1=$!
cliente 4_mesmo_ip 127.0.0.1 2000 & P2=$!
sleep 3
foto_painel $SAIDA/painel_cenario4.txt
wait $P1 $P2

kill $SERVIDOR
sleep 1
if [ -n "$TCPDUMP" ]; then
    kill $TCPDUMP
    python3 tools/inspect_pcap.py $SAIDA/experimento.pcap > $SAIDA/resumo_pcap.json
fi

rm -f www/medio.bin

echo
echo "resultados ($SAIDA/resultados.csv):"
column -t -s, $SAIDA/resultados.csv
