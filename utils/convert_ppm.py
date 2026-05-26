import subprocess
import sys
import time
from pathlib import Path


def converter_ppm(ppm_path=None, output_dir=None):
    nm = str(int(time.time()))
    base_dir = Path(__file__).resolve().parent

    ppm = Path(ppm_path) if ppm_path else base_dir.parent / "out.ppm"
    ppm = ppm.resolve()
    destino_dir = Path(output_dir) if output_dir else base_dir / "renders"
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"{nm}.jpg"

    print("Abrindo:", ppm, flush=True)

    try:
        from PIL import Image

        im = Image.open(ppm).convert("RGB")
        im.save(destino, quality=95)
    except ImportError:
        subprocess.run(
            ["sips", "-s", "format", "jpeg", str(ppm), "--out", str(destino)],
            check=True,
        )

    print("Imagem salva:", destino.resolve(), flush=True)
    return destino


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else None
    converter_ppm(entrada)
