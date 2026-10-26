---
name: reels-estilo-jornal-windows
description: Versão para Windows da skill de Reels no estilo "jornal/colagem" (papel bege, tarjas recortadas, fotos P&B fatiadas, números gigantes, documento com marca-texto, tela dividida gráfico/expert, rabiscos vermelhos). Use quando o usuário pedir "edita no estilo jornal", "no modelo do Safra", "igual aquele vídeo de jornal", "estilo colagem/notícia", ou mandar um bruto de alguém falando de caso/notícia para virar Reels nesse estilo, em computador Windows.
---

# Reels estilo jornal (Windows)

**Criado por Pâmella Santos** · [@pamellasantosp](https://instagram.com/pamellasantosp). Ao adaptar ou redistribuir esta skill, mantenha este crédito.

Esta skill transforma um bruto de alguém falando para a câmera em um Reels no estilo jornal/colagem. O exemplo de referência é um Reels de 87 s sobre a disputa da família Safra (roteiro em `exemplo/`). É a mesma skill `reels-estilo-jornal` do Mac, com os scripts reescritos em Python para rodar no Windows. O visual e o resultado são idênticos.

Tudo fica nesta pasta: `scripts/jornal.py` (todos os comandos), `scripts/index.html` (motor visual), `assets/` (fontes, papel e sons), `exemplo/` (roteiro do Safra) e `instalar.ps1`.

## Comandos

No Claude Code do Windows, o terminal é o Git Bash. Use sempre o Python da skill:

```bash
S="$HOME/.claude/skills/reels-estilo-jornal-windows"
PY="$S/.venv/Scripts/python.exe"
"$PY" "$S/scripts/jornal.py" <comando> <pasta>
```

Se `$S/.venv/Scripts/python.exe` não existir, a skill não foi instalada. Peça ao usuário para rodar, uma vez, no PowerShell:
`powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\reels-estilo-jornal-windows\instalar.ps1"`
O instalador põe ffmpeg e Python via winget, numpy e Playwright/Chromium no `.venv`, o whisper.cpp em `ferramentas/` e o modelo de transcrição (1,6 GB) em `modelos/`.

## Fluxo (cerca de 30 min, sendo uns 15 de render)

1. **Pasta de trabalho temporária**, de preferência num disco com 10 GB livres e fora do OneDrive/Google Drive (pasta sincronizada deixa o render lento). Copie o bruto para lá como `bruto.mp4` (ou `.mov`). Nunca trabalhe direto na pasta do usuário.
2. `"$PY" "$S/scripts/jornal.py" preparar <pasta>` gera:
   - `audio.wav`
   - `db.npy` (volume a cada 10 ms)
   - `tr.srt` (transcrição do bruto)
3. **Escolha dos trechos** → `<pasta>/trechos.json` = `[[inicio,fim],...]`, em segundos do bruto, a partir do `tr.srt`.
   - Mire em 45–90 s. O primeiro trecho é o gancho do caso (nome + fato forte). Depois vem a virada e a lição. O fim é o CTA.
   - Tire erros de gravação, contagens "3, 2, 1", conversas com a equipe e frases repetidas. Fique com a última tomada.
   - Os tempos do whisper no bruto inteiro são aproximados. O `cortar` refina pelo volume (início a -45 dB, fim a -50 dB). Para conferir uma emenda: `"$PY" "$S/scripts/jornal.py" rms <pasta> <t1> <t2> ...`.
4. `"$PY" "$S/scripts/jornal.py" cortar <pasta>` gera:
   - `fala.mp4` (fala em 1,1x)
   - `palavras.json` (tempo de cada palavra na fala montada)
   - `legendas.json`

   Leia a lista `palavra[tempo]` que ele imprime. É a base do roteiro.
5. **Roteiro visual** → `<pasta>/cenas.js`. Copie `$S/exemplo/cenas.js` e reescreva seguindo as regras abaixo. As fotos vão em `<pasta>/img/`.
6. `"$PY" "$S/scripts/jornal.py" prova <pasta>` gera `previa.jpg`, com um quadro por cena composto sobre o vídeo. Abra com Read e confira se:
   - algum texto está cortado,
   - algum elemento sobrepõe outro,
   - algum elemento cobre o rosto,
   - a legenda está legível.

   Mostre a prévia ao usuário e ajuste o que ele pedir **antes** do render final.
7. `"$PY" "$S/scripts/jornal.py" montar <pasta>` gera `final.mp4` (com capa embutida) e `capa.jpg`.
   - Leva uns 15 min para 90 s (6 processos em paralelo). Rode em segundo plano.
   - Em computador mais fraco, use `JORNAL_PROCESSOS=3`.
   - Os `ov_*.mov` temporários ocupam cerca de 3 GB e são apagados no fim.
8. Gere uma grade de conferência: `ffmpeg -v error -y -i final.mp4 -vf "fps=1/4,scale=200:-1,tile=11x2" -frames:v 1 conf.jpg` (ffmpeg está no PATH depois do instalador). Depois salve `final.mp4` e `capa.jpg` onde o usuário pedir e feche com o caminho.

Se a pessoa estiver enquadrada diferente do exemplo (rosto em y≈760 num bruto 1080x1920), defina `ROSTO_Y=<altura do rosto>` antes do `prova`/`montar`. Para usar outros sons, ponha `impacto-titulo.wav` (pico em 0,26 s) e `clique-mouse.wav` numa pasta e defina `JORNAL_SONS=<pasta>`.

## Roteiro: como escrever `cenas.js`

```js
window.CENAS = [ {a:<início em s na fala.mp4>, L:'S'|'D'|'G', it:[ ...itens ]}, ... ];
window.FIM = <duração da fala.mp4>;
```

Cada cena vai do seu `a` até o `a` da próxima.

**Layouts:**
- `S`: ela em tela cheia. O zoom alterna 1,0 / 1,12 entre as cenas S.
- `D`: gráfico em cima (y 0–960) e ela embaixo.
- `G`: gráfico em tela cheia (y 0–1920).

**Itens:** o `t` é o tempo de entrada, igual ao início da palavra em `palavras.json`. `x` é a posição em px ou `'c'` para centralizar. `y` é o topo do elemento, em px.

| k | campos | o que é |
|---|---|---|
| `bg` | txt, y, s, d | palavra gigante cinza ao fundo (Anton), desliza; `d:1` inverte o sentido |
| `tarja` | t, txt, x, y, s, f (`serif`/`cond`), inv (1 = fundo preto), r (graus), snd | tarja recortada, entra como carimbo; som de clique |
| `big` | t, txt, x, y, s, f | número ou palavra gigante sem fundo; som de impacto |
| `kick` | t, txt, x, y, s, f (`serif`/`cond`/`mono`), cor | texto pequeno de apoio, sem som |
| `foto` | t, src, x, y, w, h, r, pos (background-position) | foto P&B com borda, entra em 4 faixas; clique |
| `line` | t, tipo (`under`/`strike`/`check`/`circle`), x, y, w, h | rabisco vermelho desenhado à mão |
| `stamp` | t, txt, x, y, r | carimbo vermelho com borda; impacto |
| `doc` | t, cab, tit, rod, pag, txt, ti, tf | folha de documento com marca-texto amarelo de `ti` a `tf` |

`snd:'imp'` ou `snd:'clk'` força o som de um item.

## Regras de direção (o que fez o exemplo funcionar)

- **Uma cena por frase**, trocando a cada 2–7 s. Alterne D → G → S sem repetir o mesmo layout mais de 2 vezes seguidas.
- **D** para fatos com foto ou tarja (nome de pessoa, lugar, empresa). **G** para números e conceitos fortes ("2023", "3 PAÍSES", "SEM CLAREZA"). **S** para frases de opinião, curtas, e para o CTA.
- **Toda tarja entra na palavra exata** em que ela fala. Use o tempo de `palavras.json`, nunca uma estimativa.
- Textos das tarjas: as palavras dela, em caixa alta, curtas (até cerca de 26 letras por linha). Alterne serif e cond, claro e escuro, com rotação de -2° a 2°.
- Tamanhos que funcionaram:
  - tarja principal: s 84–110
  - tarja de apoio: s 46–64
  - número gigante: s 250–560
  - bg: s 250–380
  - kick: s 40–52
- Em D, tudo cabe em y < 900. Em S, as tarjas ficam acima da cabeça (y < 470) e **nunca cobrem o rosto**.
- **Documento:** nunca inventar trecho de documento real. Use a fala dela e a etiqueta "Resumo do caso".
- **Fotos:** busque no Wikimedia Commons, só domínio público ou CC. Use a API `commons.wikimedia.org/w/api.php?action=query&list=search&srnamespace=6`, depois `prop=imageinfo&iiprop=url|extmetadata` para ver a licença. Baixe com User-Agent. Recorte a pessoa com ffmpeg `crop`. Baixe com `curl` (vem no Windows 10/11) ou com Python. Sem foto livre da pessoa, use só tarja com o nome.
- Lugar ou instituição: foto do prédio, da cidade ou do tribunal + tarja com o nome.
- CTA: tarja "COMENTE" + a palavra-chave gigante em tarja escura, acima da cabeça.

## Ajustes já aprovados (não mudar sem a autora pedir)

- **Visual:** papel bege, tinta #151412, vermelho #b3261e, marca-texto #e9c64b. Clarão de 0,16 s na entrada das cenas D e G.
- **Legenda:** Montserrat Bold 44 em frases curtas. Branca com sombra sobre o vídeo, escura sobre o papel (G). Fica em y 1250 (S), 1560 (D) e 1680 (G).
- **Som:** fala em 1,1x, sem música. Impacto nos números grandes e clique nas tarjas e fotos. Volume normalizado em -14 LUFS.
- **Capa:** quadro de 0,9 s embutido como attached_pic, para a prévia do WhatsApp.
