"""Reels estilo jornal: versão em Python (Windows, também roda no Mac e no Linux).

Uso (sempre com o Python da skill):
  python jornal.py preparar <pasta>          transcreve o bruto (tr.srt) e mede o volume
  python jornal.py rms <pasta> <t1> <t2> ... mostra o volume em volta de cada tempo do bruto
  python jornal.py cortar <pasta>            monta fala.mp4 (1,1x) a partir de trechos.json
  python jornal.py prova <pasta>             gera previa.jpg (um quadro por cena)
  python jornal.py montar <pasta>            gera final.mp4 + capa.jpg

Criado por Pâmella Santos · @pamellasantosp
"""
import sys, os, json, re, glob, shutil, subprocess, asyncio, wave
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / 'scripts'
FPS = 30
VEL = 1.1
PROCESSOS = int(os.environ.get('JORNAL_PROCESSOS', 6))


# ---------- ferramentas ----------

def ferramenta(*nomes):
    """Acha um executável no PATH ou na pasta ferramentas/ da skill (instalada pelo instalar.ps1)."""
    for n in nomes:
        p = shutil.which(n)
        if p:
            return p
        for achado in SKILL.glob(f'ferramentas/**/{n}*'):
            if achado.is_file() and (achado.suffix.lower() in ('.exe', '') ):
                return str(achado)
    sys.exit(f'Não achei {nomes[0]}. Rode o instalador da skill (instalar.ps1 no Windows).')

FFMPEG = lambda: ferramenta('ffmpeg')
WHISPER = lambda: ferramenta('whisper-cli', 'main')

def modelo_whisper():
    for p in [os.environ.get('WHISPER_MODELO'), SKILL / 'modelos' / 'ggml-large-v3-turbo.bin',
              Path.home() / 'transcrever' / 'modelos' / 'ggml-large-v3-turbo.bin']:
        if p and Path(p).exists():
            return str(p)
    sys.exit('Modelo de transcrição não encontrado. Rode o instalador da skill.')

def rodar(args, **kw):
    return subprocess.run([str(a) for a in args], check=True, **kw)

def ff(*args):
    subprocess.run([FFMPEG(), '-v', 'error', '-y', *map(str, args)], check=True)

def duracao(arq):
    probe = ferramenta('ffprobe')
    r = subprocess.run([probe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(arq)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())

def ler_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def gravar_json(p, dado):
    Path(p).write_text(json.dumps(dado, ensure_ascii=False), encoding='utf-8')

def bruto():
    achados = sorted(glob.glob('bruto.*'))
    if not achados:
        sys.exit('A pasta precisa ter o vídeo com o nome bruto.mov ou bruto.mp4.')
    return achados[0]


# ---------- preparar / rms ----------

def medir_volume():
    import numpy as np
    w = wave.open('audio.wav')
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    hop = 160; n = len(a) // hop
    e = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    np.save('db.npy', 20 * np.log10(e))

def preparar():
    # fontes e papel são copiados (no Windows, atalho de pasta exige permissão de administrador)
    if not Path('fontes').exists():
        shutil.copytree(SKILL / 'assets' / 'fontes', 'fontes')
    Path('img').mkdir(exist_ok=True)
    if not Path('img/papel.jpg').exists():
        shutil.copy(SKILL / 'assets' / 'img' / 'papel.jpg', 'img/papel.jpg')
    ff('-i', bruto(), '-ar', 16000, '-ac', 1, 'audio.wav')
    medir_volume()
    rodar([WHISPER(), '-m', modelo_whisper(), '-l', 'pt', '-f', 'audio.wav', '-osrt', '-of', 'tr', '-t', 8], capture_output=True)
    print('Pronto: tr.srt (transcrição do bruto). Agora escreva trechos.json e rode: jornal.py cortar')

def rms(tempos):
    import numpy as np
    db = np.load('db.npy')
    for t in map(float, tempos):
        i0 = int((t - 0.8) * 100); row = db[max(i0, 0):i0 + 160]
        print(f"{t:7.2f}: " + ''.join('#' if v > -35 else ('+' if v > -45 else ('.' if v > -55 else ' ')) for v in row))


# ---------- cortar ----------

def cortar():
    import numpy as np
    db = np.load('db.npy'); B = bruto()
    SEG = ler_json('trechos.json')

    def onset(s):
        for i in range(max(int((s - 0.35) * 100), 0), int((s + 0.7) * 100)):
            if (db[i:i + 5] > -45).all() and (i < 20 or db[max(i - 20, 0):i].max() < -44):
                return max(i / 100 - 0.07, 0)
        return s

    def fim(e):
        for j in range(int((e - 0.3) * 100), int((e + 0.8) * 100)):
            if (db[j:j + 15] < -50).all():
                return j / 100 + 0.10
        return e + 0.1

    partes = []
    for k, (s, e) in enumerate(SEG):
        a, b = onset(s), fim(e); print(f"{s:7.2f}-{e:7.2f} -> {a:7.2f}-{b:7.2f}")
        f = f'seg{k:02d}.mp4'; partes.append(f)
        ff('-ss', a, '-to', b, '-i', B, '-vf', f'setpts=(PTS-STARTPTS)/{VEL},fps={FPS}',
           '-af', f'atempo={VEL},afade=t=in:d=0.02,areverse,afade=t=in:d=0.04,areverse',
           '-c:v', 'libx264', '-crf', 16, '-preset', 'fast', '-c:a', 'aac', '-ar', 48000, '-b:a', '256k', f)
    Path('lista.txt').write_text(''.join(f"file '{p}'\n" for p in partes), encoding='utf-8')
    ff('-f', 'concat', '-safe', 0, '-i', 'lista.txt', '-c', 'copy', 'fala.mp4')
    ff('-i', 'fala.mp4', '-ar', 16000, '-ac', 1, 'fala.wav')
    rodar([WHISPER(), '-m', modelo_whisper(), '-l', 'pt', '-f', 'fala.wav', '-ml', 1, '-sow', '-osrt',
           '-of', 'palavras', '-t', 8], capture_output=True)

    def seg(x):
        return int(x[:2]) * 3600 + int(x[3:5]) * 60 + float(x[6:].replace(',', '.'))
    srt = Path('palavras.srt').read_text(encoding='utf-8') + '\n'
    ws = [(seg(a), seg(c), w.strip()) for a, c, w in re.findall(r'\d+\n(\S+) --> (\S+)\n(.*?)\n(?:\n|$)', srt) if w.strip()]
    gravar_json('palavras.json', ws)

    # legenda em frases curtas (quebra em ponto/interrogação, vírgula com 12+ letras, ou 24+ letras)
    rep = {'black': 'BLACK'}; ch = []; cur = []
    for i, w in enumerate(ws):
        w = [w[0], w[1], rep.get(w[2], w[2])]; cur.append(w)
        txt = ' '.join(x[2] for x in cur); nxt = ws[i + 1] if i + 1 < len(ws) else None
        if w[2][-1] in '.?' or (w[2][-1] == ',' and len(txt) >= 12) or len(txt) >= 24 or nxt is None or nxt[0] - w[1] > 0.5:
            ch.append([cur[0][0], cur[-1][1], txt]); cur = []
    for k in range(len(ch)):
        ch[k][1] = min(ch[k + 1][0] if k + 1 < len(ch) else ch[k][1] + 0.6, ch[k][1] + 0.5)
    gravar_json('legendas.json', ch)
    print('duração:', duracao('fala.mp4'))
    print(' '.join(f"{w}[{a:.1f}]" for a, b, w in ws))


# ---------- render da camada gráfica (Playwright) ----------

async def _pagina(pw):
    b = await pw.chromium.launch()
    pg = await b.new_page(viewport={'width': 1080, 'height': 1920})
    await pg.goto(Path('index.html').resolve().as_uri())
    await pg.evaluate('document.fonts.ready')
    await pg.evaluate(f'LEGS={json.dumps(ler_json("legendas.json"))}')
    await pg.wait_for_timeout(400)
    return b, pg

async def _stills(ts):
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        b, pg = await _pagina(pw)
        gravar_json('info.json', await pg.evaluate('info()'))
        for t in ts:
            await pg.evaluate(f'render({float(t)})')
            await pg.screenshot(path=f'st_{t}.png', omit_background=True)
        await b.close()

async def _faixa(k, f0, f1):
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        b, pg = await _pagina(pw)
        p = subprocess.Popen([FFMPEG(), '-v', 'error', '-y', '-f', 'image2pipe', '-framerate', str(FPS), '-c:v', 'png',
                              '-i', '-', '-c:v', 'png', '-pix_fmt', 'rgba', f'ov_{k}.mov'], stdin=subprocess.PIPE)
        for f in range(f0, f1):
            await pg.evaluate(f'render({f / FPS})')
            p.stdin.write(await pg.screenshot(omit_background=True))
        p.stdin.close(); p.wait(); await b.close()

def stills(ts):
    asyncio.run(_stills(ts))


# ---------- vídeo de base, sons, prova e montagem ----------

def base():
    ry = int(os.environ.get('ROSTO_Y', 760))  # altura do rosto no bruto 1080x1920
    I = ler_json('info.json'); z = []; d = []; n = 0
    for a, b, L in I['cenas']:
        if L == 'S':
            if n % 2: z.append((a, b))
            n += 1
        if L == 'D': d.append((a, b))
    ex = lambda r: '+'.join(f'between(t,{a},{b - 0.001})' for a, b in r) or '0'
    fc = (f"[0:v]split=3[a][b][c];[b]scale=1210:2150,crop=1080:1920:65:{round(ry * 0.12)}[z];"
          f"[c]crop=1080:960:0:{min(max(ry - 380, 0), 960)},pad=1080:1920:0:960[d];"
          f"[a][z]overlay=enable='{ex(z)}'[az];[az][d]overlay=enable='{ex(d)}',format=yuv420p[v]")
    ff('-i', 'fala.mp4', '-filter_complex', fc, '-map', '[v]', '-an', '-c:v', 'libx264', '-crf', 15, '-preset', 'fast', 'base.mp4')

def sons():
    E = Path(os.environ.get('JORNAL_SONS') or SKILL / 'assets' / 'sons')
    s = ler_json('info.json')['sons']; ni = sum(1 for t, k in s if k == 'imp'); nc = len(s) - ni
    fc = ''
    if ni: fc += f"[1:a]volume=0.55,asplit={ni}" + ''.join(f'[i{j}]' for j in range(ni)) + ';'
    else: fc += '[1:a]anullsink;'
    if nc: fc += f"[2:a]volume=0.35,asplit={nc}" + ''.join(f'[c{j}]' for j in range(nc)) + ';'
    else: fc += '[2:a]anullsink;'
    mix = []; a = b = 0
    for t, k in s:
        if k == 'imp':
            d = max(int((t - 0.26) * 1000), 0); fc += f"[i{a}]adelay={d}|{d}[x{len(mix)}];"; a += 1
        else:
            d = int(t * 1000); fc += f"[c{b}]adelay={d}|{d}[x{len(mix)}];"; b += 1
        mix.append(f'[x{len(mix)}]')
    fc += "[0:a]" + ''.join(mix) + f"amix=inputs={len(mix) + 1}:normalize=0,alimiter=limit=0.95[a]"
    ff('-i', 'fala.mp4', '-i', E / 'impacto-titulo.wav', '-i', E / 'clique-mouse.wav', '-filter_complex', fc,
       '-map', '[a]', '-c:a', 'pcm_s16le', 'audio_final.wav')

def _copiar_motor():
    shutil.copy(SCRIPTS / 'index.html', 'index.html')
    if not Path('fontes').exists():
        shutil.copytree(SKILL / 'assets' / 'fontes', 'fontes')

def prova():
    _copiar_motor(); stills(['0.5']); base()
    T = [f'{(a + b) / 2 + 0.3:.2f}' for a, b, L in ler_json('info.json')['cenas']]
    stills(T)
    for t in T:
        ff('-ss', t, '-i', 'base.mp4', '-i', f'st_{t}.png', '-filter_complex', '[0][1]overlay,scale=270:480', '-frames:v', 1, f'c_{t}.png')
    if len(T) % 2: T.append(T[-1])
    ent = [x for t in T for x in ('-i', f'c_{t}.png')]
    ff(*ent, '-filter_complex', f'xstack=inputs={len(T)}:grid={len(T) // 2}x2:fill=black', 'previa.jpg')
    for p in glob.glob('st_*.png') + glob.glob('c_*.png'): os.remove(p)
    print('Pronto: previa.jpg')

def montar():
    _copiar_motor(); stills(['0.5']); base()
    N = int(ler_json('info.json')['cenas'][-1][1] * FPS); K = PROCESSOS
    procs = [subprocess.Popen([sys.executable, __file__, '_faixa', str(k), str(N * k // K), str(N * (k + 1) // K)]) for k in range(K)]
    if any(p.wait() for p in procs):
        sys.exit('Falhou o render de alguma parte da camada gráfica.')
    sons()
    Path('ovl.txt').write_text(''.join(f"file 'ov_{k}.mov'\n" for k in range(K)), encoding='utf-8')
    ff('-i', 'base.mp4', '-f', 'concat', '-safe', 0, '-i', 'ovl.txt', '-i', 'audio_final.wav', '-filter_complex',
       '[0:v][1:v]overlay=shortest=0,format=yuv420p[v];[2:a]loudnorm=I=-14:TP=-1.5[a]', '-map', '[v]', '-map', '[a]',
       '-c:v', 'libx264', '-crf', 18, '-preset', 'medium', '-profile:v', 'high', '-c:a', 'aac', '-b:a', '192k', '-ar', 48000,
       '-movflags', '+faststart', '-shortest', 'final_sem_capa.mp4')
    ff('-ss', 0.9, '-i', 'final_sem_capa.mp4', '-frames:v', 1, 'capa.jpg')
    ff('-i', 'final_sem_capa.mp4', '-i', 'capa.jpg', '-map', 0, '-map', 1, '-c', 'copy', '-disposition:v:1', 'attached_pic', 'final.mp4')
    for p in glob.glob('ov_*.mov') + glob.glob('st_*.png') + ['final_sem_capa.mp4']:
        os.remove(p)
    print(f'Pronto: {Path("final.mp4").resolve()} + capa.jpg')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == '_faixa':  # uso interno: um dos processos paralelos do render
        k, f0, f1 = map(int, sys.argv[2:5]); asyncio.run(_faixa(k, f0, f1)); sys.exit()
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    os.chdir(sys.argv[2])
    {'preparar': preparar, 'cortar': cortar, 'prova': prova, 'montar': montar}.get(cmd, lambda: rms(sys.argv[3:]) if cmd == 'rms' else sys.exit(__doc__))()
