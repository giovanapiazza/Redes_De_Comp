#!/usr/bin/env python3
# Escrito com apoio de IA (Anthropic Claude). Le o pcap direto, sem tshark.
"""Analisa a captura da V2 (pcap, Ethernet/loopback) sem tshark.
Uso: analisa_pcap.py experimento-v2.pcap DIR_SAIDA"""
import struct, sys, json, collections, os
pcap, out = sys.argv[1], sys.argv[2]
PORTA = 8095
f = open(pcap, 'rb')
gh = f.read(24)
magic = struct.unpack('<I', gh[:4])[0]
nano = magic == 0xa1b23c4d
assert magic in (0xa1b2c3d4, 0xa1b23c4d)
link = struct.unpack('<I', gh[20:24])[0]
assert link == 1, link
pk = []
while True:
    h = f.read(16)
    if len(h) < 16: break
    s, frac, incl, orig = struct.unpack('<IIII', h)
    d = f.read(incl)
    t = s + frac / (1e9 if nano else 1e6)
    if struct.unpack('!H', d[12:14])[0] != 0x0800: continue
    ip = d[14:]
    ihl = (ip[0] & 15) * 4
    tot = struct.unpack('!H', ip[2:4])[0]
    if ip[9] != 6: continue
    src = '.'.join(map(str, ip[12:16])); dst = '.'.join(map(str, ip[16:20]))
    tcp = ip[ihl:]
    sp, dp, seq = struct.unpack('!HHI', tcp[:8])
    off = (tcp[12] >> 4) * 4
    flags = tcp[13]
    plen = tot - ihl - off          # tamanho real do payload (captura truncada em 128 B)
    data = tcp[off:]
    pk.append(dict(t=t, src=src, dst=dst, sp=sp, dp=dp, seq=seq, flags=flags, plen=plen, data=data))
t0 = pk[0]['t']; dur = pk[-1]['t'] - t0
# conexoes: chave = (ip cliente, porta cliente)
con = collections.OrderedDict()
for p in pk:
    k = (p['dst'], p['dp']) if p['sp'] == PORTA else (p['src'], p['sp'])
    c = con.setdefault(k, dict(syn=0, synack=0, ack3=False, fin=0, rst=0, first=p['t'], last=p['t'],
                               reqs=[], resps=[], bytes_srv=0, maxseq=None, retx=0, data_t=[]))
    c['last'] = p['t']
    fl = p['flags']
    if fl & 2 and not fl & 16: c['syn'] += 1
    if fl & 2 and fl & 16: c['synack'] += 1
    if fl & 1: c['fin'] += 1
    if fl & 4: c['rst'] += 1
    if p['sp'] == PORTA:
        if p['plen'] > 0:
            end = (p['seq'] + p['plen']) & 0xffffffff
            if c['maxseq'] is not None and ((end - c['maxseq']) & 0xffffffff) > 0x7fffffff or (c['maxseq'] is not None and end == c['maxseq']):
                c['retx'] += 1
            else:
                c['maxseq'] = end
            c['bytes_srv'] += p['plen']
            c['data_t'].append((p['t'], p['plen']))
            if p['data'].startswith(b'HTTP/1.1 '):
                c['resps'].append((round(p['t'] - t0, 6), p['data'][9:12].decode()))
    else:
        if p['plen'] > 0 and p['data'][:4] in (b'GET ', b'HEAD'):
            line = p['data'].split(b'\r\n')[0].decode(errors='replace')
            c['reqs'].append((round(p['t'] - t0, 6), line.split(' ')[1]))
os.makedirs(out, exist_ok=True)
res = dict(pacotes=len(pk), duracao_s=round(dur, 3), conexoes=[])
gets = sum(len(c['reqs']) for c in con.values())
codes = collections.Counter(code for c in con.values() for _, code in c['resps'])
res.update(requisicoes_get=gets, respostas=dict(codes), retransmissoes=sum(c['retx'] for c in con.values()))
for (ip, port), c in con.items():
    # vazao da imagem: bytes do servidor apos o GET do objeto nao HTML
    img = [r for r in c['reqs'] if not r[1].endswith('/') and not r[1].endswith('.html')]
    vaz = None
    if img:
        ti = img[0][0] + t0
        dd = [(t, n) for t, n in c['data_t'] if t > ti]
        if len(dd) > 1:
            b = sum(n for _, n in dd); span = dd[-1][0] - ti
            vaz = round(b * 8 / span / 1000, 1)
    hs = c['syn'] >= 1 and c['synack'] >= 1
    res['conexoes'].append(dict(cliente=f'{ip}:{port}', inicio_s=round(c['first'] - t0, 3), fim_s=round(c['last'] - t0, 3),
                                handshake=hs, fin=c['fin'], rst=c['rst'], requisicoes=c['reqs'], respostas=c['resps'],
                                bytes_servidor=c['bytes_srv'], vazao_objeto_kbps=vaz, retransmissoes=c['retx']))
json.dump(res, open(f'{out}/analise-pcap.json', 'w'), indent=1, ensure_ascii=False)
# serie por segundo: por IP e por conexao
nsec = int(dur) + 1
ips = sorted({k[0] for k in con})
series = collections.OrderedDict()
for ip in ips: series[ip] = [0] * nsec
conn_keys = list(con.keys())
cs = {k: [0] * nsec for k in conn_keys}
for k, c in con.items():
    for t, n in c['data_t']:
        i = int(t - t0); series[k[0]][i] += n; cs[k][i] += n
with open(f'{out}/vazao-1s.csv', 'w') as w:
    w.write('t_s,' + ','.join(f'ip_{ip}' for ip in ips) + ',' + ','.join(f'con_{k[0]}_{k[1]}' for k in conn_keys) + '\n')
    for i in range(nsec):
        w.write(f'{i},' + ','.join(f'{series[ip][i]*8/1000:.1f}' for ip in ips) + ',' + ','.join(f'{cs[k][i]*8/1000:.1f}' for k in conn_keys) + '\n')
print(json.dumps({k: v for k, v in res.items() if k != 'conexoes'}, ensure_ascii=False))
for c in res['conexoes']:
    print(c['cliente'], c['inicio_s'], c['fim_s'], 'hs' if c['handshake'] else 'SEM-HS', 'rst', c['rst'], c['requisicoes'], c['respostas'], c['vazao_objeto_kbps'], 'retx', c['retransmissoes'])
