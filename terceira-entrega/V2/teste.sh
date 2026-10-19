#!/bin/bash
# teste bem simples da V2. roda com: bash teste.sh (precisa do curl)
# ele sobe o servidor sozinho com vazao maxima 4000 kbps e usa o taxas.txt
# 127.0.0.1 = 2000 kbps e 127.0.0.2 = 3000 kbps (no linux todo 127.x.x.x eh localhost)

PORTA=8090
# arquivo pequeno de 500 KB pra nao demorar (as imagens de 12 MB levam quase 1 min)
head -c 512000 /dev/urandom > www/teste.bin

./server $PORTA www 4000 taxas.txt > /dev/null 2> server.log &
PID=$!
sleep 2

echo "== teste 1: html + objeto na mesma conexao (127.0.0.1, 2000 kbps) =="
# 500 KB a 2000 kbps tem que dar uns 2 segundos e ~250000 bytes/s
curl -s -o /dev/null -w "html: %{http_code} tempo=%{time_total}s\n" -o /dev/null \
  -w "objeto: %{http_code} tempo=%{time_total}s velocidade=%{speed_download} bytes/s\n" \
  http://127.0.0.1:$PORTA/ http://127.0.0.1:$PORTA/teste.bin

echo "== teste 2: duas conexoes do mesmo ip dividem a taxa (deve levar ~4s cada) =="
curl -s -o /dev/null -w "con1: tempo=%{time_total}s\n" http://127.0.0.1:$PORTA/teste.bin &
curl -s -o /dev/null -w "con2: tempo=%{time_total}s\n" http://127.0.0.1:$PORTA/teste.bin &
wait %2 %3 2>/dev/null; sleep 4.5

echo "== teste 3: controle de admissao (2000 + 3000 > 4000, o segundo ip tem que levar 503) =="
curl -s -o /dev/null http://127.0.0.1:$PORTA/teste.bin &
sleep 0.5
curl -s -o /dev/null -w "127.0.0.2: %{http_code} (esperado 503)\n" --interface 127.0.0.2 http://127.0.0.2:$PORTA/teste.bin
wait %4 2>/dev/null

echo "== teste 4: html nao eh limitado (tem que ser bem rapido) =="
curl -s -o /dev/null -w "html: %{http_code} tempo=%{time_total}s\n" http://127.0.0.1:$PORTA/

kill $PID
echo "fim. log do servidor em server.log"
