#define _GNU_SOURCE
#include <arpa/inet.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <poll.h>
#include <pthread.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define HEADER_MAX 16384
#define PATH_MAX_LOCAL 4096
#define CONNECTION_MAX 128
#define REQUEST_MAX 100
#define TIMEOUT_MS 10000
static volatile sig_atomic_t stopping = 0;
static int root_fd;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t empty = PTHREAD_COND_INITIALIZER;
static int clients[CONNECTION_MAX];
static int active = 0;
typedef struct { int fd, slot; char ip[INET_ADDRSTRLEN]; } Client;
typedef struct { char method[16], target[PATH_MAX_LOCAL]; int close, head; } Request;

static void stop_signal(int sig) { (void)sig; stopping = 1; }
static int64_t now_ms(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return (int64_t)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}
static int send_all(int fd, const void *data, size_t size) {
    const char *p = data;
    while (size) {
        ssize_t n = send(fd, p, size, MSG_NOSIGNAL);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return -1;
        p += n; size -= (size_t)n;
    }
    return 0;
}
static const char *reason(int status) {
    switch (status) {
        case 200: return "OK"; case 400: return "Bad Request";
        case 403: return "Forbidden"; case 404: return "Not Found";
        case 405: return "Method Not Allowed"; case 408: return "Request Timeout";
        case 414: return "URI Too Long"; case 417: return "Expectation Failed";
        case 431: return "Request Header Fields Too Large";
        case 500: return "Internal Server Error"; case 501: return "Not Implemented";
        case 503: return "Service Unavailable"; case 505: return "HTTP Version Not Supported";
        default: return "Error";
    }
}
static int header(int fd, int status, const char *mime, uint64_t size, int close_it) {
    char buf[1024], date[80]; time_t t = time(NULL); struct tm tm;
    gmtime_r(&t, &tm); strftime(date, sizeof date, "%a, %d %b %Y %H:%M:%S GMT", &tm);
    int n = snprintf(buf, sizeof buf,
        "HTTP/1.1 %d %s\r\nDate: %s\r\nServer: Redes-MVP1\r\n"
        "Content-Type: %s\r\nContent-Length: %llu\r\nConnection: %s\r\n%s\r\n",
        status, reason(status), date, mime, (unsigned long long)size,
        close_it ? "close" : "keep-alive", status == 405 ? "Allow: GET, HEAD\r\n" : "");
    return send_all(fd, buf, (size_t)n);
}
static void error_response(int fd, int status, int close_it, int head) {
    char body[160]; int n = snprintf(body, sizeof body, "%d %s\n", status, reason(status));
    if (header(fd, status, "text/plain; charset=utf-8", (uint64_t)n, close_it) == 0 && !head)
        (void)send_all(fd, body, (size_t)n);
}
/* Lê apenas o cabecalho; preserva bytes da proxima requisicao em buffer. */
static int read_header(int fd, char *buf, size_t *used, size_t *length) {
    int64_t deadline = now_ms() + TIMEOUT_MS;
    for (;;) {
        for (size_t i = 0; i + 3 < *used; i++) {
            if (memcmp(buf + i, "\r\n\r\n", 4) == 0) { *length = i + 4; return 200; }
        }
        if (*used == HEADER_MAX) return 431;
        int64_t remaining = deadline - now_ms();
        if (remaining <= 0) return *used ? 408 : 0;
        struct pollfd p = {fd, POLLIN, 0};
        int ready = poll(&p, 1, (int)remaining);
        if (ready < 0 && errno == EINTR) continue;
        if (ready == 0) return *used ? 408 : 0;
        if (ready < 0) return 0;
        ssize_t n = recv(fd, buf + *used, HEADER_MAX - *used, 0);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return 0;
        *used += (size_t)n;
    }
}
static int token_char(unsigned char c) {
    return isalnum(c) || strchr("!#$%&'*+-.^_`|~", c) != NULL;
}
static int contains_close(char *value) {
    char *save = NULL;
    for (char *p = strtok_r(value, ",", &save); p; p = strtok_r(NULL, ",", &save)) {
        while (*p == ' ' || *p == '\t') p++;
        char *end = p + strlen(p);
        while (end > p && (end[-1] == ' ' || end[-1] == '\t')) *--end = 0;
        if (!strcasecmp(p, "close")) return 1;
    }
    return 0;
}
static int parse_request(char *buf, size_t len, Request *r) {
    memset(r, 0, sizeof *r);
    if (memchr(buf, 0, len)) return 400;
    char *line_end = strstr(buf, "\r\n");
    if (!line_end) return 400;
    *line_end = 0;
    char *space = strchr(buf, ' ');
    if (!space) return 400;
    *space++ = 0;
    char *version = strchr(space, ' ');
    if (!version) return 400;
    *version++ = 0;
    if (strchr(version, ' ') || strchr(version, '\t')) return 400;
    if (strcmp(version, "HTTP/1.1")) return 505;
    size_t method_len = strlen(buf), target_len = strlen(space);
    if (!method_len || method_len >= sizeof r->method) return 400;
    for (size_t i = 0; i < method_len; i++) if (!token_char((unsigned char)buf[i])) return 400;
    if (target_len >= sizeof r->target) return 414;
    if (!target_len || space[0] != '/') return 400;
    for (size_t i = 0; i < target_len; i++)
        if ((unsigned char)space[i] <= 32 || (unsigned char)space[i] == 127) return 400;
    strcpy(r->method, buf); strcpy(r->target, space);
    r->head = !strcmp(r->method, "HEAD");
    int hosts = 0, lengths = 0, te = 0, expect = 0, body = 0;
    char *p = line_end + 2;
    while (*p) {
        char *end = strstr(p, "\r\n"); if (!end) return 400;
        *end = 0; if (!*p) break;
        char *colon = strchr(p, ':'); if (!colon || colon == p) return 400;
        for (char *q = p; q < colon; q++) if (!token_char((unsigned char)*q)) return 400;
        *colon++ = 0;
        while (*colon == ' ' || *colon == '\t') colon++;
        char *tail = colon + strlen(colon);
        while (tail > colon && (tail[-1] == ' ' || tail[-1] == '\t')) *--tail = 0;
        for (char *q = colon; *q; q++)
            if (((unsigned char)*q < 32 && *q != '\t') || (unsigned char)*q == 127) return 400;
        if (!strcasecmp(p, "Host")) { hosts++; if (!*colon || strpbrk(colon, " \t,/")) return 400; }
        if (!strcasecmp(p, "Connection")) r->close |= contains_close(colon);
        if (!strcasecmp(p, "Transfer-Encoding")) te = 1;
        if (!strcasecmp(p, "Expect")) expect = 1;
        if (!strcasecmp(p, "Content-Length")) {
            lengths++; if (!*colon) return 400;
            for (char *q = colon; *q; q++) { if (!isdigit((unsigned char)*q)) return 400; if (*q != '0') body = 1; }
        }
        p = end + 2;
    }
    if (hosts != 1 || lengths > 1 || (te && lengths)) return 400;
    if (te) return 501;
    if (expect) return 417;
    if (strcmp(r->method, "GET") && !r->head) return 405;
    /* Nao aceitar corpos evita interpretar payload como proxima requisicao. */
    if (body) return 400;
    return 200;
}
static int hex(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
/* Percorre componentes com openat + O_NOFOLLOW; nao sai da raiz nem segue symlinks. */
static int open_resource(const char *target, int *status, char *path) {
    size_t j = 0;
    for (size_t i = 1; target[i] && target[i] != '?'; i++) {
        unsigned char c = (unsigned char)target[i];
        if (c == '%') {
            if (!target[i+1] || !target[i+2]) { *status = 400; return -1; }
            int a = hex(target[i+1]), b = hex(target[i+2]);
            if (a < 0 || b < 0) { *status = 400; return -1; }
            c = (unsigned char)(16*a+b); i += 2;
        }
        if (c <= 32 || c == 127 || c == '\\' || c == '#') { *status = 400; return -1; }
        if (j + 12 >= PATH_MAX_LOCAL) { *status = 414; return -1; }
        path[j++] = (char)c;
    }
    if (j == 0 || path[j-1] == '/') { memcpy(path+j, "index.html", 10); j += 10; }
    path[j] = 0;
    char copy[PATH_MAX_LOCAL]; strcpy(copy, path);
    char *save = NULL, *part = strtok_r(copy, "/", &save);
    int fd = dup(root_fd);
    if (fd < 0) { *status = 500; return -1; }
    while (part) {
        if (!strcmp(part, "..") || !strcmp(part, ".")) { close(fd); *status = 403; return -1; }
        char *next = strtok_r(NULL, "/", &save);
        int nfd = openat(fd, part, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK | (next ? O_DIRECTORY : 0));
        int err = errno; close(fd);
        if (nfd < 0) { *status = (err == ENOENT ? 404 : err == EMFILE || err == ENFILE ? 500 : 403); return -1; }
        fd = nfd; part = next;
    }
    struct stat st;
    if (fstat(fd, &st) || !S_ISREG(st.st_mode)) { close(fd); *status = 403; return -1; }
    return fd;
}
static const char *mime(const char *path) {
    const char *ext = strrchr(path, '.'); if (!ext) return "application/octet-stream";
    if (!strcasecmp(ext, ".html")) return "text/html; charset=utf-8";
    if (!strcasecmp(ext, ".css")) return "text/css; charset=utf-8";
    if (!strcasecmp(ext, ".js")) return "text/javascript; charset=utf-8";
    if (!strcasecmp(ext, ".txt")) return "text/plain; charset=utf-8";
    if (!strcasecmp(ext, ".png")) return "image/png";
    if (!strcasecmp(ext, ".jpg") || !strcasecmp(ext, ".jpeg")) return "image/jpeg";
    if (!strcasecmp(ext, ".bmp")) return "image/bmp";
    return "application/octet-stream";
}
static void *serve(void *arg) {
    Client *c = arg; char buffer[HEADER_MAX + 1]; size_t used = 0;
    for (int count = 1; count <= REQUEST_MAX && !stopping; count++) {
        size_t len = 0; int status = read_header(c->fd, buffer, &used, &len);
        if (status == 0) break;
        if (status != 200) { error_response(c->fd, status, 1, 0); break; }
        char request_buf[HEADER_MAX + 1]; memcpy(request_buf, buffer, len); request_buf[len] = 0;
        memmove(buffer, buffer+len, used-len); used -= len;
        Request r; status = parse_request(request_buf, len, &r);
        if (status != 200) { error_response(c->fd, status, 1, r.head); break; }
        int close_it = r.close || count == REQUEST_MAX;
        char path[PATH_MAX_LOCAL]; int file = open_resource(r.target, &status, path);
        uint64_t bytes = 0; int result = 0;
        if (file < 0) error_response(c->fd, status, close_it, r.head);
        else {
            struct stat st;
            if (fstat(file, &st)) { status = 500; error_response(c->fd, status, 1, r.head); close_it = 1; }
            else {
                result = header(c->fd, 200, mime(path), (uint64_t)st.st_size, close_it);
                char chunk[65536]; uint64_t left = (uint64_t)st.st_size;
                while (!r.head && result == 0 && left) {
                    size_t amount = left < sizeof chunk ? (size_t)left : sizeof chunk;
                    ssize_t n = read(file, chunk, amount);
                    if (n < 0 && errno == EINTR) continue;
                    if (n <= 0) { result = -1; break; }
                    result = send_all(c->fd, chunk, (size_t)n);
                    if (!result) { bytes += (uint64_t)n; left -= (uint64_t)n; }
                }
            }
            close(file);
        }
        pthread_mutex_lock(&lock);
        fprintf(stdout, "ip=%s socket=%d request=%d method=%s target=%s status=%d bytes=%llu connection=%s active=%d\n",
            c->ip, c->fd, count, r.method, r.target, status, (unsigned long long)bytes,
            close_it ? "close" : "keep-alive", active); fflush(stdout);
        pthread_mutex_unlock(&lock);
        if (close_it || result < 0) break;
    }
    pthread_mutex_lock(&lock);
    close(c->fd); clients[c->slot] = -1; active--;
    if (active == 0) pthread_cond_signal(&empty);
    pthread_mutex_unlock(&lock); free(c); return NULL;
}
int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "Uso: %s PORTA DIRETORIO_WEB\n", argv[0]); return 1; }
    char *end; errno = 0; long port = strtol(argv[1], &end, 10);
    if (errno || !*argv[1] || *end || port < 1 || port > 65535) { fprintf(stderr, "Porta invalida\n"); return 1; }
    root_fd = open(argv[2], O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (root_fd < 0) { perror("diretorio web"); return 1; }
    for (int i = 0; i < CONNECTION_MAX; i++) clients[i] = -1;
    struct sigaction sa = {0}; sa.sa_handler = stop_signal; sigemptyset(&sa.sa_mask);
    sigaction(SIGINT, &sa, NULL); sigaction(SIGTERM, &sa, NULL); signal(SIGPIPE, SIG_IGN);
    int listener = socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (listener < 0) { perror("socket"); close(root_fd); return 1; }
    int yes = 1; setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in address = {.sin_family = AF_INET, .sin_port = htons((uint16_t)port), .sin_addr.s_addr = htonl(INADDR_ANY)};
    if (bind(listener, (struct sockaddr *)&address, sizeof address) || listen(listener, 128)) {
        perror("bind/listen"); close(listener); close(root_fd); return 1;
    }
    printf("MVP1 HTTP/1.1 porta=%ld raiz=%s limite_tecnico=%d\n", port, argv[2], CONNECTION_MAX); fflush(stdout);
    while (!stopping) {
        struct pollfd p = {listener, POLLIN, 0}; int ready = poll(&p, 1, 500);
        if (ready <= 0) { if (ready < 0 && errno != EINTR) break; continue; }
        struct sockaddr_in peer; socklen_t size = sizeof peer;
        int fd = accept4(listener, (struct sockaddr *)&peer, &size, SOCK_CLOEXEC);
        if (fd < 0) { if (errno == EINTR) continue; perror("accept"); break; }
        struct timeval timeout = {.tv_sec = TIMEOUT_MS / 1000};
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof timeout);
        pthread_mutex_lock(&lock);
        int slot = -1;
        for (int i = 0; i < CONNECTION_MAX; i++) if (clients[i] == -1) { slot = i; break; }
        if (slot >= 0) { clients[slot] = fd; active++; }
        pthread_mutex_unlock(&lock);
        if (slot < 0) { error_response(fd, 503, 1, 0); close(fd); continue; }
        Client *c = malloc(sizeof *c);
        if (c) { c->fd = fd; c->slot = slot; inet_ntop(AF_INET, &peer.sin_addr, c->ip, sizeof c->ip); }
        pthread_t thread; int rc = c ? pthread_create(&thread, NULL, serve, c) : ENOMEM;
        if (rc) {
            error_response(fd, 503, 1, 0);
            pthread_mutex_lock(&lock); close(fd); clients[slot] = -1; active--; pthread_mutex_unlock(&lock); free(c);
        } else pthread_detach(thread);
    }
    close(listener);
    pthread_mutex_lock(&lock);
    for (int i = 0; i < CONNECTION_MAX; i++) if (clients[i] >= 0) shutdown(clients[i], SHUT_RDWR);
    while (active) pthread_cond_wait(&empty, &lock);
    pthread_mutex_unlock(&lock); close(root_fd); return 0;
}
