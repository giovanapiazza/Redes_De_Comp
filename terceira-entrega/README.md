# Primeira versão — servidor HTTP/1.1 concorrente


- Giovana Piazza 
- Luis Felipe Maccalli
- Vitor Moreira


## Implementação

Servidor em **C para Linux**, com **sockets TCP IPv4 e Pthreads**. Cada conexão
aceita recebe uma thread; a mesma thread atende várias requisições do cliente
no mesmo socket. Implementa um subconjunto de HTTP/1.1 para conteúdo estático:

- GET e HEAD, arquivo padrão `index.html`, Content-Length e tipos MIME;
- persistência por padrão e encerramento com `Connection: close`;
- buffer para cabeçalhos fragmentados e requisições concatenadas (pipelining);
- respostas de erro e rejeição de framing ambíguo;
- bloqueio de `..`, sequências codificadas perigosas e links simbólicos;
- logs por requisição e encerramento por Ctrl+C ou SIGTERM.

Limites técnicos: 128 conexões, 100 requisições por conexão, cabeçalhos de
16 KiB e prazo de 10 s para concluir cada cabeçalho. O envio tem timeout por
operação. O limite de conexões protege recursos; **não é controle de admissão
por vazão/QoS**. É um servidor didático, sem suporte completo ao padrão HTTP.

**A próxima versão** deve acrescentar taxa por IP, taxa padrão de 1000 kbps,
compartilhamento da taxa entre sockets do mesmo IP, controle de admissão
baseado na vazão do servidor e visualização/estimativas exigidas no enunciado.
Esta versão não implementa esses mecanismos.

## Compilar e executar

Dependências: Linux, GCC, Make e Python 3 (somente geração das imagens/testes).
Em Ubuntu/Debian, se necessário:

```bash
sudo apt update
sudo apt install build-essential python3 curl tcpdump wireshark iptraf-ng
```

A partir desta pasta:

```bash
make
make fixtures
./server 8080 www
```

Ou `make run`. Abra `http://localhost:8080/`. Para acesso de outro computador,
use `http://IP_DO_SERVIDOR:8080/` e permita a porta no firewall, se necessário.
O servidor escuta em todas as interfaces IPv4. Não execute como root.
As imagens BMP válidas são geradas localmente: duas imagens de 12.582.966
bytes cada (aproximadamente 12 MiB). Elas não ficam no controle de versão;
execute `make fixtures` depois de baixar o código.

Teste manual de persistência (o curl pode reutilizar a conexão entre as URLs):

```bash
curl --http1.1 -v -o /dev/null http://localhost:8080/ -o /dev/null http://localhost:8080/imagem1.bmp
```

O teste automatizado verifica explicitamente quatro respostas no mesmo socket:

```bash
make test
```

Os testes iniciam e encerram seu próprio servidor em uma porta livre; não é
necessário manter `make run` em execução. Resultados são gravados em `results/`.
Uma captura da etapa de persistência pode ser criada sem tcpdump se o processo
já tiver permissão para usar AF_PACKET; se não tiver, apenas a captura é
omitida. **Não rode a suíte inteira como root apenas para obter a captura.**


## Organização

- `src/server.c`: implementação do servidor;
- `Makefile`: compilação, execução e testes;
- `www/index.html`: página com duas imagens referenciadas;
- `tools/generate_images.py`: gera os objetos maiores;
- `tests/test_server.py`: testes de integração via sockets TCP reais;
- `../evidencias/`: resultados da execução realizada na preparação da entrega;
- `../documentos/`: relatório, fonte LaTeX e plano experimental.


Referências: especificação do trabalho (2026/2); material `HTTP_Aplicado.pdf`;
Forouzan, *Redes de Computadores: uma abordagem top-down* (material fornecido);
RFC 9112 — https://www.rfc-editor.org/rfc/rfc9112;
RFC 9110 — https://www.rfc-editor.org/rfc/rfc9110.
Nenhum trecho de implementação foi copiado desses documentos.
