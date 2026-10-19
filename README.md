# Servidor HTTP/1.1 com QoS — Redes de Computadores

Equipe: Giovana Piazza, Luis Felipe Maccalli e Vitor Moreira.
Universidade Federal do Pampa (Unipampa), 2026/2.

Servidor didático em C para Linux, com sockets TCP e Pthreads.

## Versões e arquivos

- [V1](V1/README.md): primeira versão, concorrência e conexões persistentes.
- [V2](V2/README.md): segunda versão, apresentada na terceira entrega, com QoS.
- [Relatório final da terceira entrega](documentos/relatorio-terceira-entrega-final.pdf).
- [Evidências da revisão da V2](evidencias/revisao-v2/resultados.json).
- [Guia de Wireshark e IPTraf](V2/COMO-VALIDAR.md).

A pasta documentos contém somente o PDF final. Templates SBC, fontes LaTeX e
relatórios intermediários foram retirados da versão atual do repositório.
V1, V2 e evidências ficam na raiz, sem uma cópia duplicada em terceira-entrega.

## Dependências

Linux, GCC, Make, Python 3 e curl. Para a avaliação complementar: tcpdump,
Wireshark e IPTraf-ng.

## Executar a V2

Na raiz do repositório:

```bash
cd V2
make
make fixtures
./server 8080 www 5000 taxas.txt 2> server.log
```

Abra http://localhost:8080/ . O parâmetro 5000 é a capacidade de admissão,
em kbps. O arquivo taxas.txt usa IPv4 e taxa inteira positiva em kbps.
IPs não cadastrados usam 1000 kbps quando houver capacidade disponível.
As duas imagens de aproximadamente 12 MiB são geradas por make fixtures.

## Testar

```bash
cd V2
make check
```

A suíte cria e encerra seu próprio servidor. Não exige servidor aberto nem root.
Os resultados são gravados em evidencias/revisao-v2 e substituem os arquivos dessa
execução local. O registro publicado da revisão contém 17 testes aprovados.

## Funcionalidades e limites

A V2 acrescenta taxa por IP, divisão entre conexões, controle de admissão e
painel com vazão agregada por IP. HTML não entra no limitador dos objetos.
O intervalo HTML–objeto e as estimativas derivadas são didáticos; não medem
diretamente RTT TCP, atraso unidirecional ou capacidade do enlace.
O servidor implementa um subconjunto de HTTP/1.1.

## Situação da avaliação

O PCAP e os resultados originais estão em evidencias/v2. A revisão usou testes
automatizados e inspeção programática do PCAP. A avaliação complementar com
Wireshark/IPTraf continua pendente; não há novas medições dessas ferramentas.
Ensaios em Ethernet/Wi-Fi com hosts distintos também permanecem pendentes.

## Apoio de IA e referências

A V1 teve apoio de OpenAI ChatGPT; a V2 original declara apoio de Claude
(Anthropic). A revisão de validação, painel, testes e documentação teve apoio de
OpenAI ChatGPT em 19/10/2026. A equipe deve revisar e compreender o código.

Referências: especificação da disciplina 2026/2; Forouzan e Mosharraf,
Redes de computadores: uma abordagem top-down; RFC 9110 e RFC 9112.
