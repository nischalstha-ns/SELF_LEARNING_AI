import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image
import os

# ================== MODEL DEFINITION (copy from train.py) ==================
class SelfLearningNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Flatten(),
            nn.Linear(28*28, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 10)
        )
    
    def forward(self, x):
        return self.net(x)

# ================== LOAD THE TRAINED MODEL ==================
model = SelfLearningNet()

# Load the model you trained earlier
model_path = "models/self_learning_ai.pth"
if not os.path.exists(model_path):
    print("❌ Model file not found! First run: python train.py")
    exit()

model.load_state_dict(torch.load(model_path, weights_only=True))
model.eval()
print("✅ Model loaded successfully!")

# ================== PREDICT ANY DIGIT IMAGE ==================
# Put any handwritten digit image (28x28) in this folder and name it "your_digit.png"
# (You can draw one in Paint, save as PNG, or download from Google "MNIST digit example")

img_path = "your_digit.png"

if not os.path.exists(img_path):
    print(f"❌ {img_path} not found! Create or download a 28x28 grayscale digit image.")
    print("Tip: You can test with a real MNIST image from the internet.")
else:
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    
    img = Image.open(img_path).convert("L").resize((28, 28))
    img_tensor = transform(img).unsqueeze(0)  # add batch dimension
    
    with torch.no_grad():
        output = model(img_tensor)
        prediction = torch.argmax(output, dim=1).item()
        confidence = torch.softmax(output, dim=1).max().item() * 100
    
    print(f"🎉 AI Prediction: {prediction}")
    print(f"Confidence: {confidence:.1f}%")