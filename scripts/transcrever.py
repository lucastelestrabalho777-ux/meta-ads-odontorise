#!/usr/bin/env python3
"""
meta-ads-odontorise: transcrição de fala de vídeo ou áudio (local, sem enviar o arquivo a ninguém).

Uso:
  python3 scripts/transcrever.py ARQUIVO [ARQUIVO2 ...] [--json]
  python3 scripts/transcrever.py --downloads-latest N        os N vídeos mais recentes em ~/Downloads

Motor: mlx-whisper (Mac com chip Apple) ou faster-whisper (Mac Intel e Windows), o que estiver
instalado. Requisitos: ffmpeg no PATH e um dos dois pacotes num ambiente Python separado:
  Mac Apple:   python3 -m venv ~/.cache/whisper-venv && ~/.cache/whisper-venv/bin/pip install mlx-whisper
  Windows/Intel: python -m venv %USERPROFILE%\\whisper-venv && whisper-venv\\Scripts\\pip install faster-whisper
Rode este script com o Python desse ambiente. Se o pacote faltar, ele explica o que instalar.
"""

import glob
import json
import os
import subprocess
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MODELO_MLX = "mlx-community/whisper-large-v3-turbo"
MODELO_FASTER = "large-v3-turbo"
EXTS = (".mp4", ".mov", ".m4v", ".avi", ".webm", ".mkv", ".mp3", ".m4a", ".wav", ".ogg", ".opus", ".aac")


def _erro(msg, code=1):
    print(f"ERRO: {msg}", file=sys.stderr)
    sys.exit(code)


def recentes(n):
    home = os.path.expanduser("~/Downloads")
    arqs = [p for p in glob.glob(os.path.join(home, "*")) if p.lower().endswith(EXTS)]
    arqs.sort(key=os.path.getmtime, reverse=True)
    return arqs[:n]


def extrair_audio(caminho):
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"arquivo não encontrado: {caminho}")
    fd, wav = tempfile.mkstemp(suffix=".wav", prefix="odr_")
    os.close(fd)
    r = subprocess.run(["ffmpeg", "-y", "-i", caminho, "-ar", "16000", "-ac", "1", "-vn", wav],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falhou: " + r.stderr.decode("utf-8", "ignore")[-300:])
    return wav


def motor():
    try:
        import mlx_whisper  # noqa: F401
        return "mlx"
    except ImportError:
        pass
    try:
        import faster_whisper  # noqa: F401
        return "faster"
    except ImportError:
        return None


def transcrever(wav, qual):
    if qual == "mlx":
        import mlx_whisper
        return mlx_whisper.transcribe(wav, path_or_hf_repo=MODELO_MLX, language="pt", fp16=True)["text"].strip()
    from faster_whisper import WhisperModel
    modelo = WhisperModel(MODELO_FASTER, compute_type="int8")
    segs, _ = modelo.transcribe(wav, language="pt")
    return " ".join(s.text.strip() for s in segs).strip()


def main(argv):
    args, como_json, arquivos = argv[1:], False, []
    i = 0
    while i < len(args):
        if args[i] == "--json":
            como_json = True; i += 1
        elif args[i] == "--downloads-latest":
            arquivos = recentes(int(args[i + 1])); i += 2
        else:
            arquivos.append(args[i]); i += 1
    if not arquivos:
        _erro("informe o arquivo (vídeo ou áudio) ou --downloads-latest N", 2)
    if subprocess.run(["which", "ffmpeg"], stdout=subprocess.DEVNULL).returncode != 0 and os.name != "nt":
        _erro("ffmpeg não encontrado. Mac: brew install ffmpeg (passo 3 do guia).", 3)
    qual = motor()
    if not qual:
        _erro("nenhum motor de transcrição instalado neste Python. Veja o cabeçalho deste script para instalar mlx-whisper (Mac Apple) ou faster-whisper.", 3)
    saida = []
    for a in arquivos:
        wav = None
        try:
            wav = extrair_audio(a)
            saida.append({"arquivo": os.path.basename(a), "caminho": a, "texto": transcrever(wav, qual), "motor": qual})
        finally:
            if wav and os.path.exists(wav):
                os.remove(wav)
    if como_json:
        print(json.dumps(saida, ensure_ascii=False, indent=2))
    else:
        for s in saida:
            print(f"\n======== {s['arquivo']} ========\n{s['texto']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
