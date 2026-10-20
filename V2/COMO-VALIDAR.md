# Validação complementar com Wireshark e IPTraf

Os resultados da captura de 19/10 estão em `../evidencias/ferramentas-v2`.
Este guia descreve como repetir a captura em outra máquina.

No Ubuntu/Zorin, instale no computador da equipe:

```bash
sudo apt update
sudo apt install wireshark tcpdump iptraf-ng
```

1. Terminal 1: `cd V2` e `bash avaliar-ferramentas.sh lo`.
2. Terminal 2: `sudo iptraf-ng`; selecione a interface `lo` e registre taxas,
   unidades, duração e tráfego de fundo. O painel do IPTraf pode incluir cabeçalhos
   e outros fluxos; a vazão útil do curl inclui apenas o conteúdo recebido.
3. Abra `evidencias/ferramentas-equipe/imagens.pcap` no Wireshark.
4. Filtro `tcp.port == 8095`; se necessário, Decode As → HTTP.
5. Use Follow → TCP Stream. Cada cliente deve apresentar HTML e duas imagens no
   mesmo fluxo. Registre handshake e encerramento e eventuais retransmissões.
6. Filtro para retransmissões:
   `tcp.port == 8095 && tcp.analysis.retransmission`.
7. Guarde capturas de tela reais e preencha a tabela abaixo. Faça ao menos três
   repetições se possível. Não preencha com números estimados.

| Repetição | Interface | Clientes | Bytes úteis totais | Tempo do lote (s) | Vazão útil (Mbps) | Taxa IPTraf e unidade | Retransmissões |
|---|---|---|---|---|---|---|---|
| 1 | preencher | 2 | medir | medir | calcular | medir | contar |
| 2 | preencher | 2 | medir | medir | calcular | medir | contar |
| 3 | preencher | 2 | medir | medir | calcular | medir | contar |

Vazão útil agregada (Mbps) = 8 × bytes totais / tempo do lote / 1.000.000.
As durações individuais do curl não substituem a cronometragem do lote inteiro.

Em Ethernet ou Wi-Fi, identifique a interface com `ip -br address`. Execute o
servidor na máquina que está sendo capturada e os curls nos outros hosts; use o
IP real do servidor nas URLs. Cadastre os IPs reais dos clientes em taxas.txt.
O script fornecido inicia clientes locais e não cria hosts remotos.

O script verifica se tcpdump existe e se permaneceu em execução. Os testes
Python não precisam de privilégios administrativos: `python3 tests/test_v2.py`.
