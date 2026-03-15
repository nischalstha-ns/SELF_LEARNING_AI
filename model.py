import torch
import torch.nn as nn

class SelfLearningNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Flatten(),
            nn.Linear(28*28, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 10)
        )

    def forward(self, x):
        return self.net(x)

def load_model(path, device):
    model = SelfLearningNet().to(device)
    model.load_state_dict(torch.load(path, map_location=device, weights_only=True))
    return model
