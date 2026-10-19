# Plano complementar de avaliação — equipe

Estes experimentos estão **planejados**, não executados no ambiente de preparação.
O relatório precisa ser atualizado com as medições da equipe antes da entrega
caso o docente exija a avaliação integral por Wireshark e IPTraf nesta versão.

## Procedimento

1. Registrar CPU/RAM, distribuição/kernel Linux, interface e velocidade nominal,
   endereços dos hosts, versão do compilador e versões das ferramentas.
2. Executar `make fixtures` e `./server 8080 www` no servidor.
3. Capturar apenas o tráfego experimental, substituindo `INTERFACE`:

```bash
sudo tcpdump -i INTERFACE -nn -s 0 tcp port 8080 -w experimento.pcap
```

4. Em outro terminal, abrir `sudo iptraf-ng`, selecionar a interface em uso e
   registrar a vazão durante os downloads. A medição da interface pode incluir
   outros fluxos: isolar o experimento e declarar essa limitação.
5. Em cada host cliente, executar a sequência com persistência:

```bash
curl --http1.1 -v -o /dev/null http://IP_DO_SERVIDOR:8080/ -o /dev/null http://IP_DO_SERVIDOR:8080/imagem1.bmp -o /dev/null http://IP_DO_SERVIDOR:8080/imagem2.bmp
```

6. Para cada download, guardar tempo e velocidade observados pelo cliente:

```bash
curl --http1.1 -sS -o /dev/null -w 'tempo_s=%{time_total} bytes=%{size_download} bytes_s=%{speed_download}\n' http://IP_DO_SERVIDOR:8080/imagem1.bmp
```

7. Repetir com 1, 4 e 12 clientes simultâneos, ao menos três vezes por cenário.
   Clientes no mesmo host são processos concorrentes, não hosts diferentes.
8. Abrir o PCAP no Wireshark, usar filtro `tcp.port == 8080`, seguir o fluxo TCP
   e verificar handshake, múltiplas requisições no mesmo fluxo, respostas,
   encerramento e possíveis retransmissões. Se HTTP não for decodificado
   automaticamente, usar *Decode As → HTTP* para a porta 8080.
9. Guardar o PCAP, capturas de tela e uma tabela com clientes, bytes, tempo,
   vazão, retransmissões e observações; atualizar a seção de avaliação.
10. Repetir em Ethernet e Wi-Fi se disponíveis, mantendo carga/objetos constantes.

## Cálculos

Vazão útil média em Mbps = `bytes recebidos * 8 / tempo em segundos / 1.000.000`.
O tempo de conclusão é uma medida da transferência, não uma medida de atraso
fim-a-fim isolado. RTT TCP e intervalo entre requisições HTML/objeto são medidas
diferentes; não atribuir ao MVP1 uma estimativa de RTT/QoS que ele não calcula.

## Evidências incluídas

Não foi possível gerar PCAP neste ambiente: sockets AF_PACKET retornaram
`Operation not permitted`. A suíte possui captura opcional limitada à etapa
de persistência, caso executada em ambiente com a permissão correspondente.
Não há captura de pacotes incluída neste pacote. `testes.csv`, `resumo.json` e `server.log`
contêm os testes locais executados. Os números são observações pontuais e não
caracterizam a capacidade máxima do servidor.
