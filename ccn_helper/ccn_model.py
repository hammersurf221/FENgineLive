import torch
import torch.nn as nn
import torch.nn.functional as F

class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        identity = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += identity
        return F.relu(out)

class CCN(nn.Module):
    def __init__(self, num_classes=13):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=5, padding=2)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(128)

        # Residual enhancement
        self.res1 = ResidualBlock(128)

        self.dropout = nn.Dropout(0.3)
        self.global_pool = nn.AdaptiveAvgPool2d((8, 8))  # Output shape [B, 128, 8, 8]
        self.fc = nn.Conv2d(128, num_classes, kernel_size=1)

    def forward(self, x):
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.max_pool2d(x, 2)  # → [B, 32, 128, 128]

        x = F.relu(self.bn2(self.conv2(x)))
        x = F.max_pool2d(x, 2)  # → [B, 64, 64, 64]

        x = F.relu(self.bn3(self.conv3(x)))
        x = F.max_pool2d(x, 2)  # → [B, 128, 32, 32]

        x = self.res1(x)  # Add residual refinement

        x = self.dropout(x)
        x = self.global_pool(x)  # → [B, 128, 8, 8]
        x = self.fc(x)           # → [B, 13, 8, 8]
        x = x.permute(0, 2, 3, 1)  # → [B, 8, 8, 13]

        return x
