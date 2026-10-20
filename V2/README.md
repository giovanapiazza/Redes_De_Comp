# Segunda versão — servidor HTTP/1.1 com QoS

- Giovana Piazza
- Luis Felipe Maccalli
- Vitor Moreira

## O que tem de novo na V2

A base é a mesma da V1 (threads, GET/HEAD, conexão persistente). Foi adicionado:

- **taxa por IP**: lida do arquivo `taxas.txt` (formato `IP KBPS`, uma por linha).
  Se o IP não estiver no arquivo usa 1000 kbps;
- **controle de taxa**: só pros objetos que não são html (as imagens). O envio é
  feito em blocos de 8 KB e depois de cada bloco a thread dorme (`nanosleep`) o tempo
  que o bloco deveria levar na taxa do cliente;
- **divisão da taxa**: conexões do mesmo IP dividem a taxa dele (taxa / nº de conexões);
- **controle de admissão**: a vazão máxima do servidor é passada na linha de comando.
  Um IP novo só é aceito se a taxa dele couber no que sobra, senão recebe 503;
- **painel em tempo real** no terminal (atualiza a cada 1 s) com os clientes, a taxa,
  o RTT estimado (tempo entre pedir o html e o primeiro objeto), atraso ≈ RTT/2 e
  banda estimada ≈ tamanho do html / RTT.

Os logs de cada requisição agora vão pro **stderr** (o stdout é do painel).

## Compilar e executar

```bash
make
make fixtures                       # gera as imagens de 12 MB
./server 8080 www 5000 taxas.txt 2> server.log
```

Parâmetros: `PORTA DIRETORIO_WEB VAZAO_MAX_KBPS [ARQUIVO_TAXAS]` (padrão `taxas.txt`).

Teste com curl (html e imagem na mesma conexão, aparece o RTT no painel):

```bash
curl -o /dev/null http://localhost:8080/ -o /dev/null http://localhost:8080/imagem1.bmp
```

## Teste

```bash
make teste
```

`make teste` e `make check` executam a suíte `tests/test_v2.py`, com 17 verificações.
Ela inicia servidores em portas livres e verifica configuração, persistência,
imagens completas, admissão, taxa padrão, divisão por IP e painel agregado.
O arquivo `teste.sh` é um roteiro manual legado, separado dessa suíte.

## Revisão de 19/10/2026

- Taxas e capacidade: inteiros entre 1 e 1.000.000.000 kbps; rejeita zero,
  negativos, lixo numérico, overflow, IPv4 inválido e IP duplicado.
- Arquivo de taxas aceita linhas vazias e comentários com `#`. Um arquivo
  explicitamente informado que não existe causa erro de inicialização.
- A coluna REAL é a vazão agregada por IP na janela entre atualizações do painel.
  ENVIADO soma bytes de objetos não HTML na sessão de atendimento do IP.
- A divisão por conexão usa ponto flutuante e preserva taxas abaixo de 1 kbps.
- As esperas usam nanosleep em fatias curtas para permitir encerramento.
- `make check`: validação, persistência, imagens completas com SHA-256,
  admissão, taxa padrão, divisão por IP e painel agregado.
- `bash avaliar-ferramentas.sh lo`: procedimento de captura com duas imagens
  grandes. Consulte COMO-VALIDAR.md para Wireshark/IPTraf e hosts distintos.
  Os resultados da captura de 19/10 estão em ../evidencias/ferramentas-v2.

## Limitações conhecidas

O intervalo HTML–objeto inclui processamento e transmissão; não é RTT TCP direto.
RTT/2 e tamanho do HTML/intervalo são estimativas didáticas, não medições de
atraso unidirecional ou da capacidade do enlace. A resolução continua em ms.
O controle envia um bloco antes da espera; admite rajadas de 8 KiB e pode
produzir média ligeiramente superior em arquivos curtos. O tempo de envio não é
descontado da espera. A soma reservada limita taxas dos IPs admitidos; HTML,
cabeçalhos e respostas de erro não entram no limitador de objetos. Conexões
ociosas também participam da divisão. A associação HTML/objeto é feita por IP e
pode misturar navegações simultâneas do mesmo endereço.

## Autoria e referências

Este projeto foi desenvolvido integralmente pela equipe, sem ajuda não
autorizada de alunos não membros do projeto no processo de codificação.

Tivemos auxílio de IA (OpenAI ChatGPT e Anthropic Claude) no relatório e na
correção dos códigos, principalmente dos testes automáticos.

Referências: especificação 2026/2, Forouzan, RFC 9110/9112; OpenAI ChatGPT,
https://chatgpt.com/; Anthropic Claude, https://claude.ai/.
