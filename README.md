# Winh Ditado

Ditado por voz para Windows e Linux, com o Whisper rodando **dentro do próprio
programa** (sem serviço separado). Aperte o atalho, fale, e o texto entra no
aplicativo em foco enquanto você fala.

## Como funciona

1. `Win+H` abre o microfone. A pílula no canto inferior direito mostra a onda do
   som e o tempo; os botões `❚❚` (pausar/retomar) e `✕` (encerrar) funcionam com
   clique.
2. Cada pausa de ~0,5 s fecha um trecho: ele é transcrito e digitado na janela em
   foco. Não precisa apertar o atalho de novo.
3. Depois de 20 s de silêncio, o ditado se encerra sozinho.

## Configuração

Rode o programa com `--settings` (ou abra de novo com ele já rodando) para
escolher:

- **Processamento:** GPU (placa NVIDIA) ou CPU (qualquer PC).
- **Modelo:** `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo`,
  `distil-large-v3`.
- **Precisão:** `float16`, `int8_float16`, `int8`, `float32`.
- **Idioma, microfone, som, pílula, digitação.**

As escolhas são aplicadas em alguns segundos, sem fechar o programa.

### Qual combinação usar

| Situação | Processamento | Modelo | Precisão |
|---|---|---|---|
| PC com NVIDIA (melhor qualidade) | GPU | `large-v3-turbo` | `float16` |
| PC com NVIDIA, pouca memória | GPU | `small` ou `medium` | `int8_float16` |
| Só processador | CPU | `small` | `int8` |
| Só processador, PC forte | CPU | `medium` | `int8` |

Medido nesta máquina (RTX 5070 Ti), áudio de 16,6 s:

| Onde | Tempo |
|---|---|
| App, GPU `large-v3-turbo` (quente) | 0,28–0,32 s |
| Serviço antigo do DSH (mesmo modelo) | 0,33–0,36 s |
| App, CPU `small` | ~2,8 s |

## Onde ficam os arquivos

- Config: `%LOCALAPPDATA%\WinhDitado\config.json` (Windows) ou
  `~/.local/share/WinhDitado/config.json` (Linux).
- Modelos: `…/WinhDitado/models`.
- Log: `…/WinhDitado/logs/winh.log`.

## GPU (CUDA)

O modo GPU precisa das bibliotecas `cublas` e `cudnn` do CUDA 12. O programa
procura nesta ordem:

1. `%LOCALAPPDATA%\WinhDitado\cuda` (com subpastas `…\bin`).
2. `nvidia\*\bin` ao lado do executável.
3. A variável de ambiente `WINH_CUDA_DIR`.

Para uma máquina limpa, instale o **CUDA Toolkit 12** ou copie as DLLs de uma
instalação que já funcione para a pasta `cuda` acima.

## Linux

Requisitos: sessão **X11** (o atalho global e a digitação não funcionam em
Wayland puro), `libportaudio2`, `python-xlib`.

```bash
./build-linux.sh          # gera WinhDitado-x86_64.AppImage
```

## Build no Windows

```powershell
pip install faster-whisper sounddevice numpy pyinstaller
powershell -ExecutionPolicy Bypass -File build-windows.ps1
# saída: dist\WinhDitado.exe
```

## Comandos

| Comando | O que faz |
|---|---|
| `WinhDitado` | roda o ditado (escolhe o modo na primeira vez) |
| `WinhDitado --settings` | abre as configurações |
| `WinhDitado --mode cpu\|gpu` | força o modo |
| `WinhDitado --status` | mostra modo, modelo e caminhos |
| `WinhDitado --transcribe-file audio.wav` | testa a transcrição de um WAV |
