"""Reproduce the v10b non-finite-loss batch and identify the bad component."""
import torch
from torch.utils.data import DataLoader
from voxshield.config import load_config
from voxshield.data.dataset import RandomMixDataset
from voxshield.losses import EnhancementLoss
from voxshield.model import build_model

config = load_config("configs/deep_filter_v10b_stoi.yaml")
device = torch.device("cuda")
state = torch.load("checkpoints_deep_filter_v10b_stoi/last.pt", map_location=device, weights_only=False)
print("resuming from epoch", state["epoch"], flush=True)
model = build_model(config).to(device)
model.load_state_dict(state["model"])
model.train()
criterion = EnhancementLoss(config).to(device)
train_set = RandomMixDataset(config, "train")

epoch = state["epoch"] + 1
train_set.set_epoch(epoch)
loader = DataLoader(train_set, batch_size=16, num_workers=0, shuffle=False)
for index, batch in enumerate(loader):
    mixture = batch["mixture"].to(device)
    clean = batch["clean"].to(device)
    reference = batch["reference"].to(device)
    preservation = torch.tensor(
        [str(c) == "clean" or str(c).startswith("near_clean:") for c in batch["category"]],
        device=device,
    )
    with torch.autocast("cuda", enabled=True):
        estimate, spectrum = model.forward_audio(mixture, reference, 256)
        loss, components = criterion(
            estimate, clean, spectrum, mixture_audio=mixture, preservation_mask=preservation
        )
    bad = {k: float(v) for k, v in components.items() if not torch.isfinite(v)}
    if bad or not torch.isfinite(loss):
        print(f"epoch {epoch} batch {index}: NON-FINITE: {bad}", flush=True)
        print("  estimate finite:", torch.isfinite(estimate).all().item(),
              "max abs:", float(estimate.abs().max()))
        print("  spectrum finite:", torch.isfinite(spectrum).all().item(),
              "max abs:", float(spectrum.abs().max()))
        print("  mixture max:", float(mixture.abs().max()), "clean max:", float(clean.abs().max()))
        print("  categories:", batch["category"])
        break
else:
    print(f"epoch {epoch} completed clean; failure not reproduced with num_workers=0", flush=True)
