import os
from PIL import Image
import time

nm = str(int(time.time()))

base_dir = os.path.dirname(__file__)

ppm_path = os.path.abspath(os.path.join(base_dir, "..", "out.ppm"))

print("Abrindo:", ppm_path)

os.makedirs(os.path.join(base_dir, "renders"), exist_ok=True)

im = Image.open(ppm_path).convert("RGB")

im.save(os.path.join(base_dir, "renders", f"{nm}.jpg"), quality=95)