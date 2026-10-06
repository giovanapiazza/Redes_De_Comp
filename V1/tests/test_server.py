from pathlib import Path
import concurrent.futures as futures
import csv
import hashlib
import http.client
import json
import os
import platform
import signal
import socket
import struct
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('RESULTS_DIR', ROOT / 'results'))
OUT.mkdir(parents=True, exist_ok=True)
rows = []
port_socket = socket.socket()
port_socket.bind(('127.0.0.1', 0))
PORT = port_socket.getsockname()[1]
port_socket.close()
log = (OUT / 'server.log').open('w')
server = subprocess.Popen([str(ROOT / 'server'), str(PORT), str(ROOT / 'www')], stdout=log, stderr=log)


def connect():
    return socket.create_connection(('127.0.0.1', PORT), timeout=15)


def request_bytes(path='/', method='GET', extra='', version='HTTP/1.1'):
    return f'{method} {path} {version}\r\nHost: localhost\r\n{extra}\r\n'.encode()


def read_response(stream, head=False):
    line = stream.readline()
    assert line.startswith(b'HTTP/1.1 '), line
    status = int(line.split()[1])
    headers = {}
    while True:
        line = stream.readline()
        if line == b'\r\n':
            break
        assert line, 'EOF dentro dos cabecalhos'
        key, value = line.decode().split(':', 1)
        headers[key.lower()] = value.strip()
    length = int(headers['content-length'])
    body = b'' if head else stream.read(length)
    assert head or len(body) == length
    return status, headers, body


def raw(data, head=False):
    with connect() as s:
        s.sendall(data)
        return read_response(s.makefile('rb'), head)


def check(name, fn):
    start = time.perf_counter()
    try:
        detail = fn()
        rows.append({'teste': name, 'resultado': 'PASS', 'duracao_s': round(time.perf_counter()-start, 6), 'detalhe': detail or ''})
        print(f'PASS {name}', flush=True)
    except Exception as e:
        rows.append({'teste': name, 'resultado': 'FAIL', 'duracao_s': round(time.perf_counter()-start, 6), 'detalhe': repr(e)})
        print(f'FAIL {name}: {e}', flush=True)


def equals(actual, expected):
    assert actual == expected, (actual, expected)


class Capture:
    """Captura opcional apenas da porta do teste, durante persistencia.
    AF_PACKET no loopback; nao depende de tcpdump. Nao captura outras portas.
    """
    def __init__(self):
        self.stop = threading.Event()
        self.error = None
        self.packets = 0
        try:
            self.s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
            self.s.bind(('lo', 0))
            self.s.settimeout(.05)
            self.f = (OUT / 'persistencia.pcap').open('wb')
            self.f.write(struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1))
            self.thread = threading.Thread(target=self.run)
            self.thread.start()
        except OSError as e:
            self.error = str(e)
    def run(self):
        while not self.stop.is_set():
            try:
                packet, addr = self.s.recvfrom(65535)
            except socket.timeout:
                continue
            # O loopback entrega copia de saida e de entrada: manter so saida.
            if addr[2] != socket.PACKET_OUTGOING or len(packet) < 54 or packet[12:14] != b'\x08\x00':
                continue
            ip = 14
            if packet[ip+9] != 6:
                continue
            tcp = ip + (packet[ip] & 15) * 4
            ports = struct.unpack('!HH', packet[tcp:tcp+4])
            if PORT not in ports:
                continue
            timestamp = time.time()
            self.f.write(struct.pack('<IIII', int(timestamp), int(timestamp % 1 * 1e6), len(packet), len(packet)))
            self.f.write(packet)
            self.packets += 1
    def finish(self):
        if self.error:
            return
        self.stop.set()
        self.thread.join()
        self.s.close()
        self.f.close()


def persistence():
    with connect() as s:
        stream = s.makefile('rb')
        for path, method in [('/', 'GET'), ('/index.html', 'HEAD'), ('/index.html', 'GET')]:
            s.sendall(request_bytes(path, method))
            status, h, body = read_response(stream, method == 'HEAD')
            equals(status, 200)
            equals(h['connection'], 'keep-alive')
        s.sendall(request_bytes('/', extra='Connection: close\r\n'))
        equals(read_response(stream)[1]['connection'], 'close')
        equals(stream.read(1), b'')
    return '4 requisicoes e respostas no mesmo socket TCP; EOF apos Connection: close'


def pipeline():
    with connect() as s:
        s.sendall(request_bytes('/') + request_bytes('/nao-existe') + request_bytes('/', extra='Connection: close\r\n'))
        stream = s.makefile('rb')
        equals([read_response(stream)[0] for _ in range(3)], [200, 404, 200])
    return '3 requisicoes concatenadas; respostas em ordem 200,404,200'


def fragmentation():
    with connect() as s:
        msg = request_bytes('/')
        for part in (msg[:7], msg[7:19], msg[19:]):
            s.sendall(part)
            time.sleep(.015)
        equals(read_response(s.makefile('rb'))[0], 200)


def binary_file():
    status, h, data = raw(request_bytes('/imagem1.bmp'))
    expected = (ROOT / 'www/imagem1.bmp').read_bytes()
    equals(status, 200)
    equals(hashlib.sha256(data).hexdigest(), hashlib.sha256(expected).hexdigest())
    equals(h['content-type'], 'image/bmp')
    return f'{len(data)} bytes; SHA-256 identico ao original'


def head_test():
    with connect() as s:
        stream = s.makefile('rb')
        s.sendall(request_bytes('/imagem1.bmp', 'HEAD'))
        status, h, _ = read_response(stream, True)
        equals(status, 200)
        equals(int(h['content-length']), (ROOT / 'www/imagem1.bmp').stat().st_size)
        s.sendall(request_bytes('/'))
        equals(read_response(stream)[0], 200)
    return 'HEAD sem corpo; proxima resposta recebida sem bytes residuais'


def concurrency():
    clients = 12
    barrier = threading.Barrier(clients)
    expected = hashlib.sha256((ROOT / 'www/imagem1.bmp').read_bytes()).hexdigest()
    def download(_):
        with connect() as s:
            barrier.wait(timeout=10)
            s.sendall(request_bytes('/imagem1.bmp', extra='Connection: close\r\n'))
            status, _, body = read_response(s.makefile('rb'))
            equals(status, 200)
            equals(hashlib.sha256(body).hexdigest(), expected)
            return len(body)
    start = time.perf_counter()
    with futures.ThreadPoolExecutor(max_workers=clients) as pool:
        transferred = sum(pool.map(download, range(clients)))
    duration = time.perf_counter() - start
    return json.dumps({'clientes': clients, 'bytes': transferred, 'duracao_s': round(duration, 6),
                       'vazao_agregada_mbps': round(transferred*8/duration/1e6, 3), 'rede': 'loopback'}, ensure_ascii=False)


def idle_client():
    with connect() as idle:
        idle.sendall(b'GET / HTTP/1.1\r\n')
        equals(raw(request_bytes('/'))[0], 200)
    return 'cliente com cabecalho incompleto nao bloqueou outro cliente'


def limit_requests():
    with connect() as s:
        stream = s.makefile('rb')
        for i in range(100):
            s.sendall(request_bytes('/', 'HEAD'))
            status, h, _ = read_response(stream, True)
            equals(status, 200)
        equals(h['connection'], 'close')
        equals(stream.read(1), b'')
    return '100 requisicoes na conexao; encerramento anunciado na ultima'


def timeout_test():
    with connect() as s:
        s.sendall(b'GET / HTTP/1.1\r\n')
        equals(read_response(s.makefile('rb'))[0], 408)
    return '408 apos prazo de cabecalho de aproximadamente 10 s'


try:
    for _ in range(100):
        if server.poll() is not None:
            raise RuntimeError('Servidor terminou antes dos testes')
        try:
            connect().close()
            break
        except OSError:
            time.sleep(.02)
    else:
        raise RuntimeError('Servidor nao iniciou')
    capture = Capture()
    check('Persistencia HTTP/1.1 e fechamento', persistence)
    time.sleep(.08)
    capture.finish()
    check('Pipelining e continuidade apos 404', pipeline)
    check('Cabecalho fragmentado em TCP', fragmentation)
    check('Integridade de imagem binaria', binary_file)
    check('HEAD sem corpo e persistente', head_test)
    check('Concorrencia com 12 clientes', concurrency)
    check('Isolamento de cliente incompleto', idle_client)
    cases = [
        ('Arquivo inexistente', request_bytes('/inexistente'), 404),
        ('Metodo POST', request_bytes('/', 'POST'), 405),
        ('Host ausente', b'GET / HTTP/1.1\r\n\r\n', 400),
        ('Host duplicado', request_bytes('/', extra='Host: outro\r\n'), 400),
        ('Versao HTTP nao suportada', request_bytes('/', version='HTTP/1.0'), 505),
        ('Traversal literal', request_bytes('/../src/server.c'), 403),
        ('Traversal codificado', request_bytes('/%2e%2e/src/server.c'), 403),
        ('NUL codificado', request_bytes('/%00'), 400),
        ('Percentual invalido', request_bytes('/%GG'), 400),
        ('Corpo de requisicao', request_bytes('/', extra='Content-Length: 2\r\n')+b'ab', 400),
        ('Content-Length duplicado', request_bytes('/', extra='Content-Length: 0\r\nContent-Length: 0\r\n'), 400),
        ('Transfer-Encoding nao implementado', request_bytes('/', extra='Transfer-Encoding: chunked\r\n'), 501),
        ('Framing ambiguo', request_bytes('/', extra='Transfer-Encoding: chunked\r\nContent-Length: 0\r\n'), 400),
        ('Expect nao implementado', request_bytes('/', extra='Expect: 100-continue\r\n'), 417),
        ('Cabecalho excede limite', b'GET / HTTP/1.1\r\nHost: localhost\r\nX: '+b'a'*16400, 431),
        ('Query string', request_bytes('/index.html?teste=1'), 200),
    ]
    for name, data, expected in cases:
        check(name, lambda data=data, expected=expected: equals(raw(data)[0], expected))
    symlink = ROOT / 'www/link-externo-test'
    try:
        symlink.symlink_to('/etc/passwd')
        check('Bloqueio de link simbolico', lambda: equals(raw(request_bytes('/link-externo-test'))[0], 403))
    finally:
        symlink.unlink(missing_ok=True)
    check('Limite de requisicoes por conexao', limit_requests)
    check('Timeout de cabecalho incompleto', timeout_test)
finally:
    server.send_signal(signal.SIGTERM)
    try:
        server.wait(timeout=15)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()
    log.close()
with (OUT / 'testes.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['teste', 'resultado', 'duracao_s', 'detalhe'])
    writer.writeheader()
    writer.writerows(rows)
summary = {'ambiente': platform.platform(), 'python': platform.python_version(),
           'data_execucao_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'aprovados': sum(r['resultado']=='PASS' for r in rows), 'total': len(rows),
           'servidor_exit_code': server.returncode, 'testes': rows,
           'captura': {'pacotes': capture.packets, 'erro': capture.error, 'ferramenta': 'AF_PACKET via Python; nao Wireshark'}}
(OUT / 'resumo.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False))
print(f"{summary['aprovados']}/{summary['total']} testes aprovados; saida servidor={server.returncode}")
raise SystemExit(0 if summary['aprovados']==summary['total'] and server.returncode==0 else 1)
