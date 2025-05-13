import torch
import numpy as np
from PIL import Image
from ccn_helper.dataset import PIECE_TO_IDX
from ccn_helper.ccn_model import CCN



IDX_TO_PIECE = {v: k for k, v in PIECE_TO_IDX.items()}


def load_model(path="ccn_model_default.pth", device=None):
    model = CCN()  # <-- use new architecture
    model.load_state_dict(torch.load(path, map_location=device or torch.device("cpu")))
    model.eval()
    return model


def load_image(path, my_color="w"):
    img = Image.open(path).convert("RGB").resize((256, 256))
    tensor = torch.from_numpy(np.array(img)).permute(2, 0, 1).float() / 255.0
    return tensor.unsqueeze(0)


def flip_fen_ranks(fen_str):
    parts = fen_str.split(" ")
    ranks = parts[0].split("/")
    flipped = ranks[::-1]
    parts[0] = "/".join(flipped)
    return " ".join(parts)

def detect_castling_rights(fen_rows):
    board = []
    for row in fen_rows:
        expanded = ""
        for char in row:
            if char.isdigit():
                expanded += '.' * int(char)
            else:
                expanded += char
        board.append(expanded)

    rights = ""
    # White
    if board[7][4] == 'K':
        if board[7][7] == 'R':
            rights += 'K'
        if board[7][0] == 'R':
            rights += 'Q'
    # Black
    if board[0][4] == 'k':
        if board[0][7] == 'r':
            rights += 'k'
        if board[0][0] == 'r':
            rights += 'q'

    return rights or "-"



def predict_fen(model, image_tensor, my_color="w"):
    with torch.no_grad():
        output = model(image_tensor)
        preds = output.argmax(dim=-1).squeeze(0)

        # Flip back the board if image was rotated
        if my_color == "b":
            preds = torch.flip(preds, dims=[0, 1])

    fen_rows = []
    for row in preds:
        fen_row = ""
        empty = 0
        for idx in row:
            piece = IDX_TO_PIECE[int(idx)]
            if piece == ".":
                empty += 1
            else:
                if empty > 0:
                    fen_row += str(empty)
                    empty = 0
                fen_row += piece
        if empty > 0:
            fen_row += str(empty)
        fen_rows.append(fen_row)

    castling = detect_castling_rights(fen_rows)
    fen = "/".join(fen_rows) + f" ? {castling} - 0 1"

    return fen
