"""
Train the E2EDriver model on rosbag-derived image + control pairs.

Data format expected in --data-dir:
  images/  *.png   (RGB, any resolution — resized to 224×224)
  labels.csv       columns: filename, steer, throttle  (both [-1, 1])

Usage:
  python -m e2e_control.train --data-dir /data/awsim_dataset --epochs 30
"""

import argparse
import csv
import pathlib

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import transforms
from PIL import Image

from .model import E2EDriver


class DriveDataset(Dataset):
    _tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    def __init__(self, data_dir: pathlib.Path):
        self._data_dir = data_dir
        self._samples = []
        with open(data_dir / "labels.csv") as f:
            for row in csv.DictReader(f):
                self._samples.append(
                    (row["filename"], float(row["steer"]), float(row["throttle"]))
                )

    def __len__(self):
        return len(self._samples)

    def __getitem__(self, idx):
        fname, steer, throttle = self._samples[idx]
        img = Image.open(self._data_dir / "images" / fname).convert("RGB")
        return self._tf(img), torch.tensor([steer, throttle], dtype=torch.float32)


def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on {device}")

    dataset = DriveDataset(pathlib.Path(args.data_dir))
    val_size = max(1, int(len(dataset) * 0.1))
    train_ds, val_ds = random_split(dataset, [len(dataset) - val_size, val_size])
    train_dl = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=4)
    val_dl   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False, num_workers=2)

    model = E2EDriver(pretrained=True).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, args.epochs)
    criterion = nn.MSELoss()

    best_val = float("inf")
    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        for imgs, labels in train_dl:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = criterion(model(imgs), labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(imgs)
        train_loss /= len(train_ds)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for imgs, labels in val_dl:
                imgs, labels = imgs.to(device), labels.to(device)
                val_loss += criterion(model(imgs), labels).item() * len(imgs)
        val_loss /= len(val_ds)
        scheduler.step()

        print(f"Epoch {epoch:3d}/{args.epochs} | train {train_loss:.4f} | val {val_loss:.4f}")

        if val_loss < best_val:
            best_val = val_loss
            out = pathlib.Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), out)
            print(f"  -> Saved best model to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--out", default="weights/e2e_driver.pt")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    train(parser.parse_args())
