"""Permutation-equivariant document logits and field heads from masked set context."""
import torch
from torch import nn


class DeepSets(nn.Module):
    def __init__(self, width, hidden, fields):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(width, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU())
        self.decoder = nn.Sequential(nn.Linear(2 * hidden, hidden), nn.ReLU())
        self.material = nn.Linear(hidden, 1)
        self.field = nn.Linear(hidden, fields)

    def forward(self, values, mask):
        encoded = self.encoder(values)
        context = (encoded * mask[..., None]).sum(dim=1) / mask.sum(dim=1, keepdim=True).clamp(min=1)
        hidden = self.decoder(torch.cat((encoded, context[:, None, :].expand_as(encoded)), dim=-1))
        return self.material(hidden).squeeze(-1), self.field(hidden)
