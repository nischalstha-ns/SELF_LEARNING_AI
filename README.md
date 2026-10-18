# 🤖 SELF_LEARNING_AI — Digit Recognition That Learns From You

A PyTorch digit-recognition AI (28×28 images) with a real **self-learning loop**:
predict a digit, tell it when it's wrong, and it updates its own weights on the
spot. All interactions are logged to `memory.json` so you can track accuracy and
retrain on past corrections.

## How it works

- **Model** (`model.py`): simple MLP — `784 → 256 → 128 → 64 → 10` with dropout.
- **Training** (`train.py`): trains on the MNIST dataset (~98% test accuracy after
  10 epochs) and saves weights to `models/self_learning_ai.pth`. MNIST downloads
  automatically on first run — no manual dataset setup needed.
- **Interactive AI** (`ai.py`): chat-style CLI. Predict digit images, get a
  confidence score + top-3 breakdown, and correct the AI when it's wrong — it
  learns immediately (10 reinforcement steps) and saves the updated model.
- **Quick predict** (`use_ai.py`): one-shot prediction for a single image file.
- **Memory** (`memory.json`, created at runtime): every prediction, correction and
  accuracy stat is logged. `retrain` replays all past corrections.

## Quick start

```bash
pip install -r requirements.txt   # torch, torchvision, Pillow
python train.py                   # train on MNIST (downloads automatically)
python ai.py                      # start the interactive AI
```

## Commands (inside `ai.py`)

| Command | What it does |
|---|---|
| `predict <image>` | Analyze a digit image, show prediction + confidence + top 3 |
| `stats` | Total predictions, accuracy, correction history |
| `history [n]` | Last n interactions |
| `retrain` | Re-train on every correction you've ever made |
| `help` | Show the command menu |
| `exit` | Quit (model and memory are already saved) |

## Project layout

```
SELF_LEARNING_AI/
├── ai.py              # interactive self-learning CLI
├── train.py           # MNIST training script
├── use_ai.py          # one-shot image prediction
├── model.py           # SelfLearningNet + load_model()
├── requirements.txt   # torch, torchvision, Pillow
├── models/            # trained weights (self_learning_ai.pth)
└── memory.json        # created at runtime — interaction log
```

## Notes

- Works on CPU or CUDA automatically.
- The `models/*.pth` file is the trained brain — keep it, or re-run `train.py`.
- `memory.json` is local runtime state (git-ignored).

Built with PyTorch. 🧠
