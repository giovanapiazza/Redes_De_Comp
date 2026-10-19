#!/usr/bin/env bash
# Captura local autorizada do experimento. Apoio: OpenAI ChatGPT, 19/10/2026.
set -euo pipefail
cd "$(dirname "$0")"
INTERFACE=${1:-lo}
IP_SERVIDOR=${2:-127.0.0.1}
PORTA=${PORTA:-8095}
SAIDA=../evidencias/ferramentas-v2
for programa in tcpdump curl python3; do
 command -v "$programa" >/dev/null || { echo "Instale $programa antes de continuar." >&2; exit 1; }
done
mkdir -p "$SAIDA"
make
make fixtures
# O script inicia o servidor local. Para rede fisica, execute no host servidor.
./server "$PORTA" www 5000 taxas.txt > "$SAIDA/painel.txt" 2> "$SAIDA/server.log" &
SERVIDOR=$!
CAPTURA=''
cleanup() {
 if [[ -n "$CAPTURA" ]]; then sudo kill -INT "$CAPTURA" 2>/dev/null || true; wait "$CAPTURA" 2>/dev/null || true; fi
 kill -TERM "$SERVIDOR" 2>/dev/null || true
 wait "$SERVIDOR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
sudo -v
sudo tcpdump -i "$INTERFACE" -nn -s 0 -U -w "$SAIDA/imagens.pcap" "tcp port $PORTA" > "$SAIDA/tcpdump.log" 2>&1 &
CAPTURA=$!
sleep 2
kill -0 "$SERVIDOR"
kill -0 "$CAPTURA"
echo 'Abra em outro terminal: sudo iptraf-ng'
echo "Selecione $INTERFACE e registre a taxa durante os downloads."
echo 'cliente,objeto,status,bytes,tempo_s,bytes_s' > "$SAIDA/imagens.csv"
cliente() {
 local id=$1
 curl --noproxy '*' --http1.1 --fail --silent --show-error \
  -o /dev/null "http://$IP_SERVIDOR:$PORTA/" \
  -o /dev/null "http://$IP_SERVIDOR:$PORTA/imagem1.bmp" \
  -o /dev/null "http://$IP_SERVIDOR:$PORTA/imagem2.bmp" \
  -w "$id,%{url_effective},%{http_code},%{size_download},%{time_total},%{speed_download}\n" > "$SAIDA/cliente-$id.csv"
}
# Duas conexoes do mesmo IP dividem sua taxa; o objeto leva minutos a 1000/2000 kbps.
cliente 1 & P1=$!
cliente 2 & P2=$!
wait "$P1"
wait "$P2"
cat "$SAIDA/cliente-1.csv" "$SAIDA/cliente-2.csv" >> "$SAIDA/imagens.csv"
echo "Concluido. Abra $SAIDA/imagens.pcap no Wireshark."
echo "Filtro: tcp.port == $PORTA ; Follow > TCP Stream para a persistencia."
echo 'As telas e os valores do IPTraf precisam ser registrados pela equipe.'
