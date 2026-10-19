# Primeira versão — servidor HTTP/1.1 concorrente

Equipe: Giovana Piazza, Luis Felipe Maccalli e Vitor Moreira.

Servidor em C para Linux com sockets TCP IPv4 e Pthreads. Implementa GET, HEAD,
conteúdo estático, conexões persistentes e atendimento concorrente.
QoS foi acrescentado na [V2](../V2/README.md).

## Compilar e executar

Na raiz do repositório:

```bash
cd V1
make
make fixtures
./server 8080 www
```

Dependências: GCC, Make e Python 3. Para executar os testes:

```bash
make test
```

A suíte inicia seu próprio servidor. Não é necessário mantê-lo aberto.
A geração das imagens deve ser feita antes dos testes. Os arquivos BMP e o
executável são gerados localmente e não precisam ser versionados.

## Limitações e referências

Subconjunto didático de HTTP/1.1, sem TLS ou conformidade integral com as RFCs.
Limites: 128 conexões, 100 requisições por conexão e cabeçalhos de até 16 KiB.
O limite de conexões da V1 protege recursos e não é admissão por vazão.

A implementação original teve apoio de OpenAI ChatGPT, conforme os comentários
no código e o registro original da primeira entrega.
Referências: especificação da disciplina 2026/2, Forouzan e Mosharraf,
RFC 9110 (https://www.rfc-editor.org/rfc/rfc9110) e
RFC 9112 (https://www.rfc-editor.org/rfc/rfc9112).
