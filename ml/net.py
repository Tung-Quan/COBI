from torch import nn


def network(inputs, hidden):
    layers = []
    for width in hidden:
        layers.extend([nn.Linear(inputs, width), nn.ReLU()])
        inputs = width
    return nn.Sequential(*layers, nn.Linear(inputs, 1), nn.Flatten(0))
