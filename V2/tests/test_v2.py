"""Testes da revisao V2. Apoio: OpenAI ChatGPT, 19/10/2026."""
from pathlib import Path
import subprocess, tempfile, socket, time, http.client, concurrent.futures, hashlib, json, re, os
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'evidencias'/'revisao-v2';OUT.mkdir(parents=True,exist_ok=True)
results=[]
def check(name,fun):
    start=time.monotonic()
    try: detail=fun(); ok=True
    except Exception as ex: detail=repr(ex);ok=False
    results.append(dict(teste=name,aprovado=ok,duracao_s=round(time.monotonic()-start,4),detalhe=detail))
    print(('PASS ' if ok else 'FAIL ')+name,flush=True)
def require(v):
    assert v
class Server:
 def __init__(self,rates,cap=500000):
    self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'taxas.txt';self.path.write_text(rates)
    s=socket.socket();s.bind(('127.0.0.1',0));self.port=s.getsockname()[1];s.close()
    self.log=tempfile.TemporaryFile();self.err=tempfile.TemporaryFile()
    self.p=subprocess.Popen([str(ROOT/'server'),str(self.port),str(ROOT/'www'),str(cap),str(self.path)],stdout=self.log,stderr=self.err)
    time.sleep(1.15)
    assert self.p.poll() is None
 def close(self):
    self.p.terminate();self.p.wait(timeout=5);self.log.seek(0);self.panel=self.log.read().decode();self.err.seek(0);self.errors=self.err.read().decode();self.log.close();self.err.close();self.tmp.cleanup()
 def client(self,ip='127.0.0.1'):return http.client.HTTPConnection('127.0.0.1',self.port,timeout=30,source_address=(ip,0))
def config(text,cap='5000'):
 with tempfile.NamedTemporaryFile(mode='w') as f:
    f.write(text);f.flush()
    p=subprocess.run([str(ROOT/'server'),'8089',str(ROOT/'www'),cap,f.name],capture_output=True,timeout=2)
    require(p.returncode!=0);return p.stderr.decode().strip()
for name,text in [('taxa zero','127.0.0.1 0\n'),('taxa negativa','127.0.0.1 -1000\n'),('IP invalido','999.1.1.1 1000\n'),('taxa nao numerica','127.0.0.1 abc\n'),('taxa fracionaria no arquivo','127.0.0.1 1.5\n'),('IP duplicado','127.0.0.1 1000\n127.0.0.1 2000\n'),('campo extra','127.0.0.1 1000 lixo\n'),('overflow numerico','127.0.0.1 99999999999999999999999999\n')]:
 check('rejeita '+name,lambda text=text:config(text))
for cap in ['0','-1','5000abc','99999999999999999999999']:
 check('rejeita capacidade '+cap,lambda cap=cap:config('',cap))
def valid():
 s=Server('# comentario\n\n127.0.0.1 2000 # taxa\n');s.close();return 'Servidor iniciou e encerrou normalmente.'
check('aceita comentarios e linhas vazias',valid)
subprocess.run(['python3',str(ROOT/'tools/generate_images.py')],cwd=ROOT,check=True)
def images():
 s=Server('127.0.0.1 128000\n',128000)
 expected={n:hashlib.sha256((ROOT/'www'/n).read_bytes()).hexdigest() for n in ['imagem1.bmp','imagem2.bmp']}
 def client():
  c=s.client();start=time.monotonic();total=0;c.request('GET','/');r=c.getresponse();require(r.status==200);html=r.read();sock=c.sock
  for name,digest in expected.items():
   require(name.encode() in html);c.request('GET','/'+name);r=c.getresponse();require(r.status==200);b=r.read();require(hashlib.sha256(b).hexdigest()==digest);require(c.sock is sock);total+=len(b)
  c.close();return dict(bytes=total,tempo_s=round(time.monotonic()-start,4))
 try:
  start=time.monotonic()
  with concurrent.futures.ThreadPoolExecutor(2) as pool: values=list(pool.map(lambda _:client(),range(2)))
  wall=time.monotonic()-start;return dict(clientes=values,bytes_total=sum(x['bytes'] for x in values),tempo_lote_s=round(wall,4),vazao_util_kbps=round(sum(x['bytes'] for x in values)*8/wall/1000,2),persistencia=True,sha256=True)
 finally:s.close();(OUT/'painel-imagens.txt').write_text(s.panel);(OUT/'server-imagens.log').write_text(s.errors)
check('dois clientes: HTML e duas imagens grandes, persistencia e SHA256',images)
def admissao():
 s=Server('127.0.0.1 2000\n127.0.0.2 3000\n',4000)
 try:
  a=s.client();a.request('GET','/');r=a.getresponse();require(r.status==200);r.read()
  b=s.client('127.0.0.2');b.request('GET','/');r=b.getresponse();require(r.status==503);r.read();b.close()
  a.close();time.sleep(.2)
  b=s.client('127.0.0.2');b.request('GET','/');r=b.getresponse();require(r.status==200);r.read();b.close()
  return '503 quando nao cabe; 200 depois de liberar a reserva.'
 finally:s.close()
check('admissao e liberacao da reserva',admissao)
(ROOT/'www'/'teste-revisao.bin').write_bytes(b'A'*1048576)
def taxas():
 s=Server('127.0.0.1 2000\n',10000)
 def download(ip):
  c=s.client(ip);start=time.monotonic();c.request('GET','/teste-revisao.bin');r=c.getresponse();data=r.read();c.close();require(r.status==200);require(len(data)==1048576);return len(data)*8/(time.monotonic()-start)/1000
 try:
  default=download('127.0.0.4');require(750<default<1150)
  with concurrent.futures.ThreadPoolExecutor(2) as pool:v=list(pool.map(download,['127.0.0.1']*2))
  require(all(700<x<1200 for x in v));return dict(padrao_kbps=round(default,1),mesmo_ip_kbps=[round(x,1) for x in v])
 finally:s.close();(OUT/'painel-taxas.txt').write_text(s.panel)
check('taxa padrao e divisao entre duas conexoes',taxas)
def painel():
 s=Server('127.0.0.1 2000\n',4000)
 def dl():
  c=s.client();c.request('GET','/teste-revisao.bin');r=c.getresponse();r.read();c.close()
 try:
  with concurrent.futures.ThreadPoolExecutor(2) as pool:list(pool.map(lambda _:dl(),range(2)))
 finally:s.close()
 (OUT/'painel-agregado.txt').write_text(s.panel)
 vals=[]
 for line in s.panel.splitlines():
  fields=line.split()
  if len(fields)==9 and fields[0]=='127.0.0.1' and fields[1]=='2':vals.append(float(fields[7]))
 require(any(1500<x<2600 for x in vals));return dict(amostras_real_ip_kbps=vals,alvo_agregado_kbps=2000)
check('painel soma bytes das duas conexoes do IP',painel)
(ROOT/'www'/'teste-revisao.bin').unlink(missing_ok=True)
(OUT/'resultados.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(f'{sum(x["aprovado"] for x in results)}/{len(results)} testes aprovados')
raise SystemExit(any(not x['aprovado'] for x in results))
