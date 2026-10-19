import json
from pathlib import Path
import struct
import sys
p = Path(sys.argv[1])
f = p.open('rb')
header = f.read(24)
assert struct.unpack('<I', header[:4])[0] == 0xa1b2c3d4
count = syn = syn_ack = 0
payloads = []
flows = set()
while True:
    h = f.read(16)
    if not h:
        break
    _, _, size, _ = struct.unpack('<IIII', h)
    data = f.read(size)
    assert len(data) == size
    ip = 14
    tcp = ip + (data[ip] & 15) * 4
    source, dest = struct.unpack('!HH', data[tcp:tcp+4])
    flows.add(tuple(sorted((source, dest))))
    flags = data[tcp+13]
    syn += bool(flags & 2 and not flags & 16)
    syn_ack += bool(flags & 2 and flags & 16)
    count += 1
    offset = tcp + (data[tcp+12] >> 4) * 4
    payloads.append(data[offset:])
payload = b''.join(payloads)
print(json.dumps({'pacotes': count, 'fluxos_tcp': len(flows), 'syn': syn,
                  'syn_ack': syn_ack, 'requisicoes_get': payload.count(b'GET '),
                  'requisicoes_head': payload.count(b'HEAD '),
                  'respostas_200': payload.count(b'HTTP/1.1 200 OK')}, indent=2))
