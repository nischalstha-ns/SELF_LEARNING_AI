import torch
import torchvision.transforms as transforms
from PIL import Image, ImageOps
import os

from model import SelfLearningNet, load_model

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ================== LOAD THE TRAINED MODEL ==================
model_path = "models/self_learning_ai.pth"
if not os.path.exists(model_path):
    print("❌ Model file not found! First run: python train.py")
    exit()

model = load_model(model_path, DEVICE)
model.eval()
print("✅ Model loaded successfully!")

# ================== PREDICT ANY DIGIT IMAGE ==================
# Put any handwritten digit image in this folder and name it "your_digit.png"
# (You can draw one in Paint, save as PNG, or use an MNIST sample.)

img_path = "your_digit.png"

if not os.path.exists(img_path):
    print(f"❌ {img_path} not found! Create or download a 28x28 grayscale digit image.")
    print("Tip: You can test with a real MNIST image from the internet.")
else:
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])

    img = Image.open(img_path).convert("L")
    img = ImageOps.autocontrast(img)
    img = img.resize((28, 28), Image.LANCZOS)
    img_tensor = transform(img).unsqueeze(0).to(DEVICE)  # add batch dimension

    with torch.no_grad():
        output = model(img_tensor)
        prediction = torch.argmax(output, dim=1).item()
        confidence = torch.softmax(output, dim=1).max().item() * 100

    print(f"🎉 AI Prediction: {prediction}")
    print(f"Confidence: {confidence:.1f}%")
