import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
from PIL import Image, ImageOps
import os
import json
import datetime
from model import SelfLearningNet, load_model

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
MODEL_PATH  = "models/self_learning_ai.pth"
MEMORY_PATH = "memory.json"
DEVICE      = torch.device("cuda" if torch.cuda.is_available() else "cpu")

CONFIDENCE_HIGH   = 90.0   # AI is very sure
CONFIDENCE_MEDIUM = 60.0   # AI is somewhat sure
LEARN_RATE        = 0.0005 # learning rate for online corrections

TRANSFORM = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,))
])

# ─────────────────────────────────────────────
#  MEMORY (interaction log)
# ─────────────────────────────────────────────
def load_memory():
    if os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, "r") as f:
            return json.load(f)
    return {"total_predictions": 0, "correct": 0, "corrections": 0, "history": []}

def save_memory(memory):
    with open(MEMORY_PATH, "w") as f:
        json.dump(memory, f, indent=2)

def log_interaction(memory, image_path, prediction, confidence, correct_label, was_correct):
    memory["total_predictions"] += 1
    if was_correct:
        memory["correct"] += 1
    else:
        memory["corrections"] += 1
    memory["history"].append({
        "time":          datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "image":         image_path,
        "predicted":     prediction,
        "confidence":    round(confidence, 2),
        "correct_label": correct_label,
        "was_correct":   was_correct
    })
    save_memory(memory)

# ─────────────────────────────────────────────
#  IMAGE PREPROCESSING
# ─────────────────────────────────────────────
def preprocess_image(img_path):
    img = Image.open(img_path).convert("L")       # grayscale
    img = ImageOps.autocontrast(img)               # normalize contrast
    img = img.resize((28, 28), Image.LANCZOS)      # resize to 28x28
    return TRANSFORM(img).unsqueeze(0).to(DEVICE)  # add batch dim

# ─────────────────────────────────────────────
#  PREDICTION + ANALYSIS
# ─────────────────────────────────────────────
def analyze(model, img_tensor):
    model.eval()
    with torch.no_grad():
        output     = model(img_tensor)
        probs      = torch.softmax(output, dim=1)[0]
        prediction = torch.argmax(probs).item()
        confidence = probs[prediction].item() * 100
        top3       = torch.topk(probs, 3)
    return prediction, confidence, top3

def decision_message(confidence):
    if confidence >= CONFIDENCE_HIGH:
        return "✅ I am very confident about this."
    elif confidence >= CONFIDENCE_MEDIUM:
        return "🤔 I think this is correct, but I'm not fully sure."
    else:
        return "⚠️  I'm uncertain. Please verify and correct me if I'm wrong."

# ─────────────────────────────────────────────
#  ONLINE LEARNING (learn from correction)
# ─────────────────────────────────────────────
def learn_from_correction(model, optimizer, img_tensor, correct_label):
    model.train()
    label_tensor = torch.tensor([correct_label], dtype=torch.long).to(DEVICE)
    criterion    = nn.CrossEntropyLoss()

    for _ in range(10):  # reinforce correction 10 times
        optimizer.zero_grad()
        loss = criterion(model(img_tensor), label_tensor)
        loss.backward()
        optimizer.step()

    torch.save(model.state_dict(), MODEL_PATH)
    model.eval()

# ─────────────────────────────────────────────
#  COMMANDS
# ─────────────────────────────────────────────
def cmd_predict(model, optimizer, memory, args):
    if not args:
        print("  Usage: predict <image_path>")
        return

    img_path = args[0]
    if not os.path.exists(img_path):
        print(f"  ❌ File not found: {img_path}")
        return

    img_tensor              = preprocess_image(img_path)
    prediction, confidence, top3 = analyze(model, img_tensor)

    print(f"\n  🔍 Analyzing: {img_path}")
    print(f"  ─────────────────────────────")
    print(f"  Prediction  : {prediction}")
    print(f"  Confidence  : {confidence:.1f}%")
    print(f"  {decision_message(confidence)}")
    print(f"\n  Top 3 possibilities:")
    for i in range(3):
        digit = top3.indices[i].item()
        prob  = top3.values[i].item() * 100
        bar   = "█" * int(prob / 5)
        print(f"    {digit} → {prob:5.1f}%  {bar}")

    # Ask for feedback
    print(f"\n  Was I correct? (yes / no / skip): ", end="")
    feedback = input().strip().lower()

    if feedback == "yes":
        log_interaction(memory, img_path, prediction, confidence, prediction, True)
        print("  ✅ Great! I'll remember that.")

    elif feedback == "no":
        print(f"  What is the correct digit? (0-9): ", end="")
        try:
            correct = int(input().strip())
            if 0 <= correct <= 9:
                learn_from_correction(model, optimizer, img_tensor, correct)
                log_interaction(memory, img_path, prediction, confidence, correct, False)
                print(f"  🧠 Got it! I've learned that this is {correct}. Model updated.")
            else:
                print("  ❌ Invalid digit. Must be 0-9.")
        except ValueError:
            print("  ❌ Invalid input.")

    else:
        print("  ⏭️  Skipped feedback.")

def cmd_stats(memory, args):
    total       = memory["total_predictions"]
    correct     = memory["correct"]
    corrections = memory["corrections"]
    accuracy    = (correct / total * 100) if total > 0 else 0

    print(f"\n  📊 AI Performance Stats")
    print(f"  ─────────────────────────────")
    print(f"  Total predictions : {total}")
    print(f"  Correct           : {correct}")
    print(f"  Corrections made  : {corrections}")
    print(f"  Session accuracy  : {accuracy:.1f}%")

    if corrections > 0:
        print(f"\n  📚 Last 5 corrections:")
        corrections_list = [h for h in memory["history"] if not h["was_correct"]][-5:]
        for c in corrections_list:
            print(f"    [{c['time']}] Predicted {c['predicted']} → Correct: {c['correct_label']} (conf: {c['confidence']}%)")

def cmd_history(memory, args):
    limit   = int(args[0]) if args and args[0].isdigit() else 10
    history = memory["history"][-limit:]
    if not history:
        print("  No history yet.")
        return
    print(f"\n  📜 Last {len(history)} interactions:")
    print(f"  {'Time':<20} {'Image':<25} {'Pred':>4} {'Conf':>7} {'Result'}")
    print(f"  {'─'*70}")
    for h in history:
        result = "✅" if h["was_correct"] else f"❌→{h['correct_label']}"
        print(f"  {h['time']:<20} {os.path.basename(h['image']):<25} {h['predicted']:>4} {h['confidence']:>6.1f}%  {result}")

def cmd_retrain(memory, args):
    corrections = [h for h in memory["history"] if not h["was_correct"]]
    if not corrections:
        print("  No corrections to retrain on.")
        return
    print(f"  🔄 Retraining on {len(corrections)} past corrections...")
    model_local    = load_model(MODEL_PATH, DEVICE)
    optimizer_local = optim.Adam(model_local.parameters(), lr=LEARN_RATE)
    for c in corrections:
        if os.path.exists(c["image"]):
            img_tensor = preprocess_image(c["image"])
            learn_from_correction(model_local, optimizer_local, img_tensor, c["correct_label"])
    print("  ✅ Retrained on all past corrections. Model updated.")

def cmd_help(args=None):
    print("""
  ╔══════════════════════════════════════════════════╗
  ║           SELF-LEARNING AI — COMMANDS            ║
  ╠══════════════════════════════════════════════════╣
  ║  predict <image>   Analyze a digit image         ║
  ║  stats             Show performance statistics   ║
  ║  history [n]       Show last n interactions      ║
  ║  retrain           Retrain on all corrections    ║
  ║  help              Show this help menu           ║
  ║  exit              Exit the AI                   ║
  ╚══════════════════════════════════════════════════╝
    """)

# ─────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────
def main():
    print("\n" + "═"*52)
    print("   🤖  SELF-LEARNING AI  |  Digit Recognition")
    print("═"*52)

    # Load model
    if not os.path.exists(MODEL_PATH):
        print("❌ No trained model found. Run: python train.py")
        return

    model     = load_model(MODEL_PATH, DEVICE)
    optimizer = optim.Adam(model.parameters(), lr=LEARN_RATE)
    memory    = load_memory()

    print(f"✅ Model loaded | Device: {DEVICE}")
    print(f"📊 Past sessions: {memory['total_predictions']} predictions, {memory['corrections']} corrections")
    print("Type 'help' to see all commands.\n")

    COMMANDS = {
        "predict":  lambda args: cmd_predict(model, optimizer, memory, args),
        "stats":    lambda args: cmd_stats(memory, args),
        "history":  lambda args: cmd_history(memory, args),
        "retrain":  lambda args: cmd_retrain(memory, args),
        "help":     lambda args: cmd_help(args),
    }

    while True:
        try:
            raw = input("AI> ").strip()
            if not raw:
                continue

            parts   = raw.split()
            command = parts[0].lower()
            args    = parts[1:]

            if command == "exit":
                print("👋 Goodbye! Model and memory saved.")
                break
            elif command in COMMANDS:
                COMMANDS[command](args)
            else:
                print(f"  ❓ Unknown command: '{command}'. Type 'help' for commands.")

        except KeyboardInterrupt:
            print("\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    main()
