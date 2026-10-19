# Terceira entrega

- Código atual: V2/src/server.c.
- Relatório final: [PDF](documentos/relatorio-terceira-entrega-final.pdf).
- Testes publicados: evidencias/revisao-v2/resultados.json (17 aprovados).
- PCAP e resultados originais: evidencias/v2.
- Avaliação complementar: V2/COMO-VALIDAR.md.

```bash
cd V2
make
make check
make fixtures
./server 8080 www 5000 taxas.txt
```

A pasta documentos contém apenas o relatório final em PDF; não há templates SBC,
fontes LaTeX ou relatórios intermediários. A V1 foi preservada na raiz.
Wireshark/IPTraf e ensaios com hosts físicos continuam pendentes.
Consulte o README principal para dependências e limitações.
