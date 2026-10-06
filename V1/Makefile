CC = gcc
CFLAGS = -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror
LDLIBS = -pthread
.PHONY: all run test fixtures clean
all: server
server: src/server.c
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)
fixtures:
	python3 tools/generate_images.py
run: server fixtures
	./server 8080 www
test: server fixtures
	python3 tests/test_server.py
clean:
	rm -f server
