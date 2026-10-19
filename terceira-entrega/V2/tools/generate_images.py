from pathlib import Path
import struct
ROOT = Path(__file__).resolve().parents[1] / 'www'
ROOT.mkdir(exist_ok=True)
width = height = 2048
size = width * height * 3
for index in (1, 2):
    path = ROOT / f'imagem{index}.bmp'
    with path.open('wb') as f:
        f.write(struct.pack('<2sIHHI', b'BM', 54 + size, 0, 0, 54))
        f.write(struct.pack('<IiiHHIIiiII', 40, width, height, 1, 24, 0, size, 2835, 2835, 0, 0))
        for y in range(height):
            f.write(bytes(v for x in range(width) for v in ((x // 8) % 256, (y // 8) % 256, 80 * index)))
    print(f'{path.name}: {path.stat().st_size} bytes')
