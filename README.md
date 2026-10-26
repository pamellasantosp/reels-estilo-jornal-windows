# reels-estilo-jornal-windows

**Criado por Pâmella Santos** · [@pamellasantosp](https://instagram.com/pamellasantosp)

Versão para **Windows** da skill do Claude Code que edita Reels no estilo jornal/colagem: papel bege, tarjas recortadas, fotos P&B em faixas, números gigantes, documento com marca-texto, tela dividida e rabiscos vermelhos. O resultado é idêntico ao da versão do Mac.

## O que você precisa
- Windows 10 ou 11, com uns 10 GB livres
- Claude Code instalado (plano Claude Pro ou Max), usando o modelo Opus (`/model`)
- winget (já vem no Windows 11; no 10, instale o "App Installer" da Microsoft Store)
- Git for Windows (o Claude Code no Windows já pede para instalar)

## Instalar (uma vez)
No PowerShell:

```powershell
git clone https://github.com/pamellasantosp/reels-estilo-jornal-windows "$HOME\.claude\skills\reels-estilo-jornal-windows"
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\reels-estilo-jornal-windows\instalar.ps1"
```

Leva uns 10 a 15 minutos: instala ffmpeg, Python, o navegador do render e o programa de transcrição, e baixa o modelo (1,6 GB). Depois, feche e abra o Claude Code.

## Usar
No Claude Code, mande o vídeo e peça **"edita esse vídeo no estilo jornal"**, dizendo a duração (ex.: 60 a 90 s), a palavra do CTA e onde salvar. Confira a prévia antes do render final (uns 15 minutos).

O passo a passo completo e as regras de direção de arte estão em `SKILL.md`. O exemplo de referência (caso Safra) está em `exemplo/`.

---

**Criado por Pâmella Santos** · [@pamellasantosp](https://instagram.com/pamellasantosp). Se usar ou adaptar esta skill, mantenha este crédito.
