# Terceira entrega: versão corrigida

Código revisado: V2/src/server.c. V1 foi preservada.

## Executar

```bash
cd V2
make
make check
make fixtures
./server 8080 www 5000 taxas.txt
```

Relatório a usar: documentos/terceira-entrega-revisada/relatorio.pdf.
O LaTeX e o estilo SBC acompanham o PDF. Os relatórios anteriores foram mantidos
como histórico; não são o documento recomendado para esta revisão.

Os 17 testes passaram. Evidências novas: evidencias/revisao-v2.
Evidências originais: evidencias/v2 (não substituídas).

O ensaio com duas imagens grandes passou com SHA-256 e conexão persistente.
A avaliação com Wireshark/IPTraf continua pendente: consulte V2/COMO-VALIDAR.md.
Não há novas capturas dessas ferramentas nesta revisão.

As imagens e o executável não integram o ZIP; make fixtures e make os geram.
O repositório GitHub não foi alterado automaticamente. Copie os arquivos revisados,
revise o diff, faça commit e push no seu repositório.

Revisão com apoio de OpenAI ChatGPT em 19/10/2026; V2 original declara Claude.
