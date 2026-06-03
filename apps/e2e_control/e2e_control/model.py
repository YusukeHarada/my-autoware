"""
Lightweight CNN that maps a front-camera image to steering + throttle.

Architecture: MobileNetV3-Small backbone → regression head
Input : (1, 3, 224, 224) float32, normalized ImageNet stats
Output: (steer, throttle) both in [-1, 1]
"""

import torch
import torch.nn as nn
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights


class E2EDriver(nn.Module):
    def __init__(self, pretrained: bool = True):
        super().__init__()
        weights = MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
        backbone = mobilenet_v3_small(weights=weights)

        # drop the classification head; keep the feature extractor
        self.features = backbone.features
        self.avgpool = backbone.avgpool

        feature_dim = 576  # MobileNetV3-Small output channels

        self.head = nn.Sequential(
            nn.Linear(feature_dim, 128),
            nn.Hardswish(),
            nn.Dropout(0.2),
            nn.Linear(128, 2),  # [steer, throttle]
            nn.Tanh(),           # clamp to [-1, 1]
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        return self.head(x)
