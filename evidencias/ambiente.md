# Execução de referência em 05/10/2026

- Linux x86_64, kernel 6.18.44, glibc 2.39.
- GCC 13.3.0 (Ubuntu 13.3.0-6ubuntu2~24.04).
- Python 3.12.14.
- TCP IPv4 em loopback (127.0.0.1), porta efêmera.
- Compilação padrão: C11, O2, Wall, Wextra, Wpedantic, Werror e pthread.
- Resultado padrão: 26/26 testes aprovados; servidor terminou com status 0.
- ASAN_OPTIONS=detect_leaks=0: 26/26 testes aprovados; status 0; sem diagnósticos ASan/UBSan.

Os valores numéricos do relatório usam a execução padrão em resumo.json.
Os tempos são pontuais; não constituem estimativas estatísticas de desempenho.
