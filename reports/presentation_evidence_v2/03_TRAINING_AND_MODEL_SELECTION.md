# Candidate training and selection

Every candidate uses the same 85-input transformation and the same 18,000 training and 4,500 validation records. We loaded all 11 saved checkpoints, checked SHA-256 against the inventory and recomputed validation log loss. Training was not replayed. [Candidate inventory and complete configuration](../final/uci350-v2.0/candidates.json) · [Audit](audit_summary.json).

| Candidate | Configuration | Effective / observed steps | Validation log loss | Termination |
|---|---|---:|---:|---|
| Dummy | Constant train prevalence 0.221222 | 0 | 0.528311 | Train prevalence |
| logistic-C0.1 | LBFGS, L2, C=0.1 | 176 | 0.444747 | Converged |
| logistic-C1 | LBFGS, L2, C=1 | 457 | 0.446682 | Converged |
| logistic-C10 | LBFGS, L2, C=10 | 1,268 | 0.449490 | Converged after cap increase |
| xgb-d2-lr0.03 | Depth 2, η=0.03 | 350 / 350 | 0.433940 | Round cap |
| **xgb-d2-lr0.1** | **Depth 2, η=0.10** | **210 / 230** | **0.432396** | Patience 20 |
| xgb-d4-lr0.03 | Depth 4, η=0.03 | 224 / 244 | 0.433805 | Patience 20 |
| xgb-d4-lr0.1 | Depth 4, η=0.10 | 76 / 96 | 0.433929 | Patience 20 |
| mlp-b32 | 85–64–32–1, batch 32 | 5 / 11 epochs | 0.438727 | Patience 6 |
| mlp-b64 | 85–64–32–1, batch 64 | 6 / 12 epochs | 0.437312 | Patience 6 |
| mlp-b128 | 85–64–32–1, batch 128 | 7 / 13 epochs | 0.435273 | Patience 6 |

## Optimization and artifacts

- **Dummy** uses the training mean of the binary label. It has no optimizer or learning rate. Its checkpoint records prevalence.
- **Logistic Regression** minimizes full-batch binary cross-entropy with L2 penalty. LBFGS adapts its own step lengths, with tolerance 1e−8 and max iterations 5,000. The original cap of 1,000 stopped `C=10` before convergence. Increasing the cap preceded the test unlock. The checkpoints preserve coefficient and intercept arrays. The log records terminal losses and the L2 norm of the regularized gradient. [Original failed fit](../final/training-attempt1.log).
- **XGBoost** uses CPU histogram trees, binary logistic objective, validation log loss, seed 42 and one thread. It uses all rows and columns per round, `reg_lambda=1`, `reg_alpha=0`, `gamma=0`, `min_child_weight=1` and `max_bin=256`. The round cap is 350. Gradient and Hessian drive tree construction internally. The audit has per-round losses and resolved configurations. [Training implementation](../../ml/candidates.py).
- **MLP** uses ReLU after the two hidden layers, a single logit, mean `BCEWithLogitsLoss`, AdamW (learning rate 0.001, weight decay 0.0001, default β₁=0.9, β₂=0.999 and ε=1e−8), 40-epoch cap, patience 6 and seed 42. Gradients are clipped to norm 5 after logging their pre-clip norm. Each shuffled batch produces one update, including the smaller final batch. All checkpoint architectures and optimizer defaults are in `candidates.json`. [Network](../../ml/net.py) · [Protocol](../../ml/protocol.json).

| MLP batch | Batches per epoch | Last batch | Actual epochs | Optimizer updates | Best epoch |
|---|---:|---:|---:|---:|---:|
| 32 | 563 | 16 | 11 | 6,193 | 5 |
| 64 | 282 | 16 | 12 | 3,384 | 6 |
| 128 | 141 | 80 | 13 | 1,833 | 7 |

| MLP batch | Train BCE at best epoch | Validation loss at best epoch | Mean / max gradient norm before clipping |
|---|---:|---:|---:|
| 32 | 0.425927 | 0.438727 | 0.377150 / 1.150387 |
| 64 | 0.424433 | 0.437312 | 0.303476 / 1.083598 |
| 128 | 0.424535 | 0.435273 | 0.216299 / 0.465092 |

Epoch histories are `candidates.json[].history`. They include train BCE, validation log loss, gradient mean and maximum, rate, best epoch, checkpoint hash and optimizer updates. The audit recomputed weighted train BCE and gradient summaries from [batch 32](../final/uci350-v2.0/batch-mlp-b32.csv), [batch 64](../final/uci350-v2.0/batch-mlp-b64.csv) and [batch 128](../final/uci350-v2.0/batch-mlp-b128.csv). Checkpoints are under `reports/final/uci350-v2.0/checkpoints/`, keyed by candidate name. The audit records each exact path and hash.

## XGBoost objective and selection

For binary outcome `yᵢ∈{0,1}` and `pᵢ=σ(sᵢ)`,

```text
L = Σᵢ ℓ(yᵢ,pᵢ) + Σₖ Ω(fₖ)
ℓ(y,p) = −y log(p) − (1−y) log(1−p)
sᵢ⁽ᵏ⁾ = sᵢ⁽ᵏ⁻¹⁾ + η fₖ(xᵢ)
Ω(fₖ) = γT + ½λ Σⱼ wⱼ²
```

Each new tree fits a regularized second-order approximation to the current loss. For logistic loss, the gradient is `p−y` and the Hessian is `p(1−p)`. The shrinkage rate η scales the new tree. Depth two caps each tree at four leaves and limits local interactions. It does not guarantee generalization. Log loss directly evaluates the probability forecast and penalizes confident errors. The winner in each family is the smallest validation log loss. The fixed ladder dummy, LR, XGBoost, MLP adopts a challenger only when the improvement exceeds 0.001. XGBoost beat the chosen LR by 0.012352 validation log-loss units and the best MLP had higher loss. That supports the selected configuration within this experiment. [XGBoost paper](https://arxiv.org/abs/1603.02754) · [Selection implementation](../../ml/candidates.py).

### Why 230 trees appear in metadata

Training attained the best validation value at zero-based iteration 209, or round **210**. It ran **20 more rounds** without a new best, so the resolved pre-slice configuration shows **230** trees. The trainer saved `booster[:210]`. The native predictor uses the full stored slice, effectively `[0,210)`. The selected checkpoint and registry model have the same hash. The audit reproduced raw and calibrated outputs for all 4,500 stored test rows and verified 100 of those rows through the current research API. The resolved training configuration is diagnostic metadata. [Registry manifest](../final/uci350-v2.0/model/model_manifest.json) · [Verified parity](audit_summary.json) · [Native prediction semantics](https://xgboost.readthedocs.io/en/release_3.0.0/prediction.html).

**Slide visuals** · [Validation comparison](figures/validation_performance.svg) · [Training trace](figures/training_performance.svg).
