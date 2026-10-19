CC = gcc
CFLAGS = -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror
LDLIBS = -pthread
.PHONY: all run teste fixtures clean
all: server
server: src/server.c
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)
fixtures:
	python3 tools/generate_images.py
# vazao maxima de 5000 kbps so pra testar
run: server fixtures
	./server 8080 www 5000 taxas.txt 2> server.log
teste: server
	python3 tests/test_v2.py
clean:
	rm -f server server.log www/teste.bin

.PHONY: check
check: server
	python3 tests/test_v2.py
