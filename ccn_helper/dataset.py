import torch
from torch.utils.data import Dataset
from PIL import Image
import numpy as np
import os

PIECE_TO_IDX = {
    '.': 0, 'P': 1, 'N': 2, 'B': 3, 'R': 4, 'Q': 5, 'K': 6,
    'p': 7, 'n': 8, 'b': 9, 'r': 10, 'q': 11, 'k': 12
}

def fen_to_matrix(fen):
    matrix = []
    rows = fen.split()[0].split('/')
    for row in rows:
        expanded = []
        for char in row:
            if char.isdigit():
                expanded.extend(['.'] * int(char))
            else:
                expanded.append(char)
        matrix.append([PIECE_TO_IDX[c] for c in expanded])
    return torch.tensor(matrix, dtype=torch.long)

class ChessBoardDataset(Dataset):
    def __init__(self, data_dir):
        self.data_dir = data_dir
        with open(os.path.join(data_dir, "labels.txt")) as f:
            lines = f.read().splitlines()
        self.samples = []
        for line in lines:
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                self.samples.append((parts[0], parts[1]))


    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_name, fen = self.samples[idx]
        img_path = os.path.join(self.data_dir, img_name)
        img = Image.open(img_path).convert("RGB").resize((256, 256))
        img_tensor = torch.from_numpy(np.array(img)).permute(2, 0, 1).float() / 255.0
        label_matrix = fen_to_matrix(fen)
        return img_tensor, label_matrix
