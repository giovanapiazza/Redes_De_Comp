# Evidências de Wireshark e IPTraf-ng da V2

## Como foi feito

- Máquina: notebook da equipe, Ubuntu 24.04, kernel 7.0.0-38, x86_64 (`maquina.txt`), em 19/10/2026, na interface `lo`.
- Código: `V2/src/server.c`, compilado com o Makefile da V2.
- Servidor: `./server 8095 www 6000 taxas.txt`. Taxas: 127.0.0.1 = 2000, 127.0.0.2 = 3000, 127.0.0.3 = 1500 kbps e 127.0.0.4 fora do arquivo (padrão de 1000 kbps).
- Clientes: `curl --interface IP` pedindo `/` e depois a imagem de 12.582.966 bytes **na mesma conexão**.
- Captura: `dumpcap` (Wireshark), 128 bytes por pacote, filtro `tcp port 8095`. Nenhum pacote descartado (`dumpcap.txt`).
- IPTraf-ng: monitor de conexões TCP em `lo` durante o cenário A (`iptraf-lo.png`).
- Para repetir, na pasta `V2`: `bash ../evidencias/ferramentas-v2/experimento-v2.sh "$PWD" SAIDA` e depois `python3 ../evidencias/ferramentas-v2/analisa_pcap.py SAIDA/experimento-v2.pcap SAIDA`. O usuário precisa estar no grupo `wireshark`.

## Cenários

| Cenário | O que acontece |
|---|---|
| A | 127.0.0.1, .3 e .4 baixam `imagem1.bmp` ao mesmo tempo |
| B | aos 3 s, 127.0.0.2 (3000 kbps) tenta entrar com 4500 de 6000 kbps já reservados |
| C | duas conexões simultâneas de 127.0.0.1 baixam `imagem2.bmp` |
| D | 127.0.0.2 tenta de novo com a reserva livre |

## Resultados

| Cenário | IP | Taxa configurada (kbps) | Vazão na captura (kbps) | Vazão no curl (kbps) | Tempo (s) | HTTP |
|---|---|---|---|---|---|---|
| A | 127.0.0.1 | 2000 | 1988,3 | 1987,6 | 50,65 | 200 |
| A | 127.0.0.3 | 1500 | 1493,0 | 1492,6 | 67,44 | 200 |
| A | 127.0.0.4 (padrão) | 1000 | 996,4 | 996,2 | 101,05 | 200 |
| B | 127.0.0.2 | 3000 | – | – | 0,0004 | 503 |
| C | 127.0.0.1, conexão 1 | 2000 dividido por 2 | 994,4 | 994,3 | 101,24 | 200 |
| C | 127.0.0.1, conexão 2 | 2000 dividido por 2 | 994,4 | 994,3 | 101,24 | 200 |
| D | 127.0.0.2 | 3000 | – | – | 0,0008 | 200 |

A vazão na captura é a soma do payload TCP enviado pela porta 8095 em cada conexão, do GET da imagem até o último segmento, × 8 / duração / 1000 (`analise-pcap.json`). A do curl é `speed_download` × 8 / 1000 (`curl.csv`).

Outros resultados da captura (`analise-pcap.json`, `capinfos.txt`):
- 15.465 pacotes em 202,3 s; 7 conexões TCP, todas com handshake completo.
- 12 GET, 11 respostas 200 e 1 resposta 503. Só a conexão recusada (cenário B) termina com RST.
- Nenhum segmento de dados retransmitido.
- Persistência: em cada conexão, o GET da imagem chega no mesmo fluxo TCP, logo após a resposta ao GET `/`.
- Todas as imagens chegaram completas: 12.582.966 bytes cada (`curl.csv`).

O gráfico `vazao-por-ip.png` (gerado de `vazao-1s.csv` com `grafico-vazao.tex`) mostra a vazão a cada 1 s por IP e, no cenário C, cada conexão separada.

## IPTraf: cuidado ao ler

- **No loopback, o IPTraf conta cada pacote duas vezes**, na saída e na entrada. Na tela, o fluxo 127.0.0.1:8095 → 127.0.0.3:46050 aparece com 2965,4 kbps, o dobro dos ~1483 kbps reais (1500 configurados). Em Ethernet ou Wi-Fi isso não acontece.
- Na mesma tela, os bytes para 127.0.0.3 (5.820.264) e para 127.0.0.4 (3.882.924) estão na razão 1,50, a mesma de 1500/1000 kbps.
- As linhas UDP da tela são consultas DNS locais, que não fazem parte do experimento.

## Limitações

- O loopback não é Ethernet nem Wi-Fi, e os vários IPs 127.0.0.x não são hosts diferentes.
- RTT: o intervalo entre a resposta do HTML e o GET da imagem foi de ~0,2 ms (`analise-pcap.json`). O painel mostra 1,0 ms porque arredonda para o mínimo de 1 ms. Pela mesma razão, a coluna BANDA (532 bytes × 8 / 1 ms = 4256 kbps) não mede o cliente.
- Não foi emulado atraso. Para isso: `sudo tc qdisc add dev lo root netem delay 20ms`.
- Para ver no Wireshark: abra `experimento-v2.pcap`, use Statistics → Conversations, Statistics → I/O Graphs com o filtro `tcp.srcport==8095 && ip.dst==127.0.0.3`, e Follow TCP Stream.
