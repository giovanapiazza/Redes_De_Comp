# Execução de referência em 05/10/2026

- Linux x86_64, kernel 6.18.44, glibc 2.39.
- GCC 13.3.0 (Ubuntu 13.3.0-6ubuntu2~24.04).
- Python 3.12.14.
- TCP IPv4 em loopback (127.0.0.1), porta efêmera.
- Compilação padrão: C11, O2, Wall, Wextra, Wpedantic, Werror e pthread.
- Resultado padrão: 26/26 testes aprovados; servidor terminou com status 0.
- Verificação adicional: address,undefined; O1, g, fno-omit-frame-pointer.
- ASAN_OPTIONS=detect_leaks=0: 26/26 testes aprovados; status 0; sem diagnósticos ASan/UBSan.
- LeakSanitizer não pôde verificar vazamentos: restrição de acesso a /proc/processos.
- Não há alegação de ausência de vazamentos nem verificação por ThreadSanitizer.
- Wireshark, tcpdump e IPTraf-ng indisponíveis.
- Captura AF_PACKET tentou abrir socket, mas retornou Operation not permitted.
- Não há PCAP ou medição de Ethernet/Wi-Fi. Completar o plano experimental.

Os valores numéricos do relatório usam a execução padrão em resumo.json.
Os tempos são pontuais; não constituem estimativas estatísticas de desempenho.
