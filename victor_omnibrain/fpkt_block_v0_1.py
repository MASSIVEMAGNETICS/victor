# FILE: victor_omnibrain/fpkt_block_v0_1.py
# VERSION: v0.1.3-FPKT-ANNEAL-TRACE-GODCORE
# NAME: FPKTBlock
# AUTHOR: Brandon "iambandobandz" Emery x Victor (Fractal Architect Mode)
# PURPOSE: PyTorch-only Fractal Product-Key Tree (FPKT) block with telemetry-driven annealing.
#          Compute model: Shallow Always / Deep Conditional (true sparse recursion).
#          Features: STE gating, depth-resolved telemetry trace, honest entropy aggregation,
#                    annealing: lower temp on low entropy_by_depth (sharpen routing live).
#          Updated: Multimodal Support (v0.1.4)

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any

import torch
import torch.nn as nn
import torch.nn.functional as F


# -----------------------------
# Utilities / telemetry
# -----------------------------

@dataclass
class FPKTTelemetry:
    # Aggregates (scalars)
    router_entropy: torch.Tensor          # scalar (tokens-weighted mean across depths)
    mean_topk_prob: torch.Tensor          # scalar
    expected_depth: torch.Tensor          # scalar (avg expected depth)
    recurse_rate: torch.Tensor            # scalar (fraction of tokens at root that recursed)

    # Trace (vectors)
    entropy_by_depth: torch.Tensor        # [max_depth]
    recurse_rate_by_depth: torch.Tensor   # [max_depth]
    tokens_by_depth: torch.Tensor         # [max_depth]
    clamp_oob_by_depth: torch.Tensor      # [max_depth]
    temp_by_depth: torch.Tensor           # [max_depth] annealed temperatures

    # Local expert load (root only, local bank)
    expert_load: torch.Tensor             # [E_local] counts

    warnings: Tuple[str, ...] = ()


def _entropy_from_probs(p: torch.Tensor, eps: float = 1e-9) -> torch.Tensor:
    p = p.clamp_min(eps)
    return -(p * p.log()).sum(dim=-1).mean()


def _safe_l2_normalize(x: torch.Tensor, dim: int = -1, eps: float = 1e-12) -> torch.Tensor:
    return x / (x.norm(p=2, dim=dim, keepdim=True).clamp_min(eps))


def _zeros_trace(max_depth: int, device: torch.device, dtype: torch.dtype = torch.float32) -> torch.Tensor:
    return torch.zeros(max_depth, device=device, dtype=dtype)


def _tokens_weighted_mean(values: torch.Tensor, weights: torch.Tensor, eps: float = 1e-9) -> torch.Tensor:
    denom = weights.sum().clamp_min(eps)
    return (values * weights).sum() / denom


# -----------------------------
# Product-Key Router (Top-M expansion -> Top-K pairs) with annealing
# -----------------------------

class ProductKeyRouter(nn.Module):
    def __init__(
        self,
        dim: int,
        num_experts: int,
        num_keys: Optional[int] = None,
        top_k: int = 4,
        expand_factor: int = 4,
        temperature: float = 1.0,
        normalize_qk: bool = True,
        anneal_factor: float = 0.9,
        entropy_thresh: float = 0.05,
    ) -> None:
        super().__init__()
        if dim % 2 != 0:
            raise ValueError(f"ProductKeyRouter requires even dim; got dim={dim}")

        self.dim = int(dim)
        self.num_experts = int(num_experts)
        self.top_k = int(top_k)
        self.expand_factor = int(max(1, expand_factor))
        self.base_temp = float(max(1e-6, temperature))
        self.normalize_qk = bool(normalize_qk)
        self.anneal_factor = float(anneal_factor)
        self.entropy_thresh = float(entropy_thresh)

        if num_keys is None:
            K = int(math.ceil(math.sqrt(self.num_experts)))
        else:
            K = int(num_keys)
        self.K = K

        half = self.dim // 2
        self.keys1 = nn.Parameter(torch.randn(K, half) * (1.0 / math.sqrt(half)))
        self.keys2 = nn.Parameter(torch.randn(K, half) * (1.0 / math.sqrt(half)))

        self.M = min(self.K, self.top_k * self.expand_factor)

        # Runtime state: current temp (annealed per forward if low entropy)
        self.register_buffer("current_temp", torch.tensor(self.base_temp))

    def forward(self, x: torch.Tensor, prev_entropy: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Anneals temp if prev_entropy < thresh (from parent telemetry).
        Returns:
            probs:    [B,S,top_k]
            gids:     [B,S,top_k] in [0, num_experts)
            clamp_oob:[B,S,top_k] bool
            entropy:  scalar (this router's entropy)
        """
        if prev_entropy is not None and prev_entropy.item() < self.entropy_thresh:
            self.current_temp *= self.anneal_factor
            self.current_temp.clamp_min(1e-6)

        temp = self.current_temp.item()

        B, S, D = x.shape
        q1, q2 = x.chunk(2, dim=-1)

        k1, k2 = self.keys1, self.keys2
        if self.normalize_qk:
            q1 = _safe_l2_normalize(q1)
            q2 = _safe_l2_normalize(q2)
            k1 = _safe_l2_normalize(k1)
            k2 = _safe_l2_normalize(k2)

        s1 = torch.matmul(q1, k1.t()) / temp
        s2 = torch.matmul(q2, k2.t()) / temp

        v1, i1 = torch.topk(s1, k=self.M, dim=-1)
        v2, i2 = torch.topk(s2, k=self.M, dim=-1)

        pair = v1.unsqueeze(-1) + v2.unsqueeze(-2)
        flat = pair.reshape(B, S, -1)
        topv, topidx = torch.topk(flat, k=self.top_k, dim=-1)

        row = torch.div(topidx, self.M, rounding_mode="floor")
        col = topidx % self.M

        sel_i1 = torch.gather(i1, dim=2, index=row)
        sel_i2 = torch.gather(i2, dim=2, index=col)

        gids = sel_i1 * self.K + sel_i2
        clamp_oob = gids >= self.num_experts
        if clamp_oob.any():
            gids = gids.clamp_max(self.num_experts - 1)

        probs = F.softmax(topv, dim=-1)
        entropy = _entropy_from_probs(probs)

        return probs, gids.to(torch.int64), clamp_oob, entropy


# -----------------------------
# Expert bank + dispatch (local shard) — unchanged from v0.1.2
# -----------------------------

class ExpertMLP(nn.Module):
    def __init__(self, dim: int, expansion: int = 4, dropout: float = 0.0) -> None:
        super().__init__()
        hid = int(expansion * dim)
        self.fc1 = nn.Linear(dim, hid)
        self.fc2 = nn.Linear(hid, dim)
        self.drop = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc2(self.drop(F.gelu(self.fc1(x))))


class LocalExpertBank(nn.Module):
    def __init__(self, dim: int, num_local_experts: int = 256, expansion: int = 4, dropout: float = 0.0) -> None:
        super().__init__()
        self.num_local_experts = int(num_local_experts)
        self.experts = nn.ModuleList([ExpertMLP(dim, expansion, dropout) for _ in range(self.num_local_experts)])

    def forward(
        self,
        x_flat: torch.Tensor,
        local_ids_flat: torch.Tensor,
        weights_flat: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        sort_idx = torch.argsort(local_ids_flat)
        local_sorted = local_ids_flat[sort_idx]
        x_sorted = x_flat[sort_idx]
        w_sorted = weights_flat[sort_idx]

        y_sorted = torch.zeros_like(x_sorted)
        load = torch.zeros(self.num_local_experts, device=x_flat.device, dtype=torch.long)

        uniq, counts = torch.unique_consecutive(local_sorted, return_counts=True)
        offsets = torch.cumsum(counts, dim=0)
        starts = torch.cat([offsets.new_zeros(1), offsets[:-1]])

        for u, start, count in zip(uniq.tolist(), starts.tolist(), counts.tolist()):
            eid = int(u)
            load[eid] += count
            chunk_x = x_sorted[start : start + count]
            chunk_w = w_sorted[start : start + count].unsqueeze(-1)
            out = self.experts[eid](chunk_x)
            y_sorted[start : start + count] = out * chunk_w

        deep_full = torch.zeros_like(y_sorted)
        deep_full[sort_idx] = y_sorted
        return deep_full, load


# -----------------------------
# FPKT recursive node — with annealing integration
# -----------------------------

class FPKTNode(nn.Module):
    def __init__(
        self,
        dim: int,
        num_experts: int,
        num_local_experts: int,
        top_k: int,
        expand_factor: int,
        max_depth: int,
        depth: int,
        gate_threshold: float,
        gate_hard: bool,
        normalize_qk: bool,
        temperature: float,
        mlp_expansion: int,
        dropout: float,
        anneal_factor: float = 0.9,
        entropy_thresh: float = 0.05,
    ) -> None:
        super().__init__()
        self.dim = int(dim)
        self.depth = int(depth)
        self.max_depth = int(max_depth)
        self.gate_threshold = float(gate_threshold)
        self.gate_hard = bool(gate_hard)

        self.router = ProductKeyRouter(
            dim=dim,
            num_experts=num_experts,
            top_k=top_k,
            expand_factor=expand_factor,
            temperature=temperature,
            normalize_qk=normalize_qk,
            anneal_factor=anneal_factor,
            entropy_thresh=entropy_thresh,
        )
        self.bank = LocalExpertBank(dim, num_local_experts, mlp_expansion, dropout)

        self.proj = nn.Linear(dim, dim, bias=False)
        self.gate = nn.Sequential(
            nn.Linear(dim * 2 + 1, dim),
            nn.GELU(),
            nn.Linear(dim, 1),
        )
        self.norm = nn.LayerNorm(dim)

        self.child: Optional[FPKTNode] = None
        if self.depth < self.max_depth - 1:
            self.child = FPKTNode(
                dim=dim,
                num_experts=num_experts,
                num_local_experts=num_local_experts,
                top_k=top_k,
                expand_factor=expand_factor,
                max_depth=max_depth,
                depth=depth + 1,
                gate_threshold=gate_threshold,
                gate_hard=gate_hard,
                normalize_qk=normalize_qk,
                temperature=temperature,
                mlp_expansion=mlp_expansion,
                dropout=dropout,
                anneal_factor=anneal_factor,
                entropy_thresh=entropy_thresh,
            )

    def forward(self, x: torch.Tensor, prev_entropy: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, FPKTTelemetry]:
        B, S, D = x.shape
        device = x.device

        ent_trace = _zeros_trace(self.max_depth, device=device)
        rec_trace = _zeros_trace(self.max_depth, device=device)
        tok_trace = _zeros_trace(self.max_depth, device=device)
        oob_trace = _zeros_trace(self.max_depth, device=device)
        temp_trace = _zeros_trace(self.max_depth, device=device) + self.router.base_temp  # Init with base

        # 1) Routing with annealing (pass prev_entropy to sharpen if low)
        probs, gids, clamp_oob, my_entropy = self.router(x, prev_entropy)
        temp_trace[self.depth] = self.router.current_temp

        tokens_here = torch.tensor(float(B * S), device=device)
        tok_trace[self.depth] = tokens_here
        ent_trace[self.depth] = my_entropy
        oob_trace[self.depth] = clamp_oob.float().mean()

        # 2) Shallow mix
        local_ids = (gids % self.bank.num_local_experts).to(torch.int64)
        x_flat = x.reshape(-1, D)
        y_acc = torch.zeros_like(x_flat)
        load_acc = torch.zeros(self.bank.num_local_experts, device=device, dtype=torch.long)

        K = probs.shape[-1]
        for kk in range(K):
            y_k, load_k = self.bank(
                x_flat,
                local_ids[..., kk].reshape(-1),
                probs[..., kk].reshape(-1),
            )
            y_acc += y_k
            load_acc += load_k

        y = self.norm(y_acc.reshape(B, S, D))

        # 3) Residual + gating
        approx = self.proj(y)
        r = x - approx
        r_norm = r.norm(p=2, dim=-1, keepdim=True)
        gate_in = torch.cat([x, r, r_norm], dim=-1)

        alpha_soft = torch.sigmoid(self.gate(gate_in))

        if self.gate_hard:
            if self.training:
                gate_bool = (alpha_soft > self.gate_threshold)
                gate_h = gate_bool.float()
                alpha_eff = gate_h - alpha_soft.detach() + alpha_soft
            else:
                alpha_eff = (alpha_soft > self.gate_threshold).float()
        else:
            alpha_eff = alpha_soft

        recurse_mask = (alpha_eff > 0.5).squeeze(-1)
        recurse_rate_here = recurse_mask.float().mean()
        rec_trace[self.depth] = recurse_rate_here

        expected_depth_scalar = torch.ones((), device=device)

        # 4) Recursion (pass my_entropy to child for annealing)
        if (self.child is None) or (recurse_mask.sum() == 0):
            router_entropy = _tokens_weighted_mean(ent_trace, tok_trace)
            mean_topk = probs.max(dim=-1).values.mean()

            warn = []
            if router_entropy.item() < 0.05:
                warn.append(f"depth_{self.depth}_collapse")
            if oob_trace[self.depth].item() > 0.0:
                warn.append("oob_clamped")

            tel = FPKTTelemetry(
                router_entropy=router_entropy,
                mean_topk_prob=mean_topk,
                expected_depth=expected_depth_scalar,
                recurse_rate=recurse_rate_here,
                entropy_by_depth=ent_trace,
                recurse_rate_by_depth=rec_trace,
                tokens_by_depth=tok_trace,
                clamp_oob_by_depth=oob_trace,
                temp_by_depth=temp_trace,
                expert_load=load_acc,
                warnings=tuple(warn),
            )
            return y, tel

        r_flat = r.reshape(-1, D)
        mask_flat = recurse_mask.reshape(-1)

        r_sel = r_flat[mask_flat]
        deep_sel, child_tel = self.child(r_sel.unsqueeze(1), my_entropy)
        deep_sel = deep_sel.squeeze(1)

        deep_full = torch.zeros_like(r_flat)
        deep_full[mask_flat] = deep_sel
        deep_full = deep_full.reshape(B, S, D)

        out = y + alpha_eff * deep_full

        ent_trace += child_tel.entropy_by_depth
        rec_trace = torch.maximum(rec_trace, child_tel.recurse_rate_by_depth)
        tok_trace += child_tel.tokens_by_depth
        oob_trace = torch.maximum(oob_trace, child_tel.clamp_oob_by_depth)
        temp_trace = torch.minimum(temp_trace, child_tel.temp_by_depth)  # Propagate annealed temps

        expected_depth_scalar = 1.0 + alpha_soft.mean() * child_tel.expected_depth.detach()

        router_entropy = _tokens_weighted_mean(ent_trace, tok_trace)
        mean_topk = probs.max(dim=-1).values.mean()

        warn = list(child_tel.warnings)
        if router_entropy.item() < 0.05:
            warn.append(f"depth_{self.depth}_collapse")
        if oob_trace[self.depth].item() > 0.0:
            warn.append("oob_clamped")

        tel = FPKTTelemetry(
            router_entropy=router_entropy,
            mean_topk_prob=mean_topk,
            expected_depth=expected_depth_scalar,
            recurse_rate=recurse_rate_here,
            entropy_by_depth=ent_trace,
            recurse_rate_by_depth=rec_trace,
            tokens_by_depth=tok_trace,
            clamp_oob_by_depth=oob_trace,
            temp_by_depth=temp_trace,
            expert_load=load_acc,
            warnings=tuple(warn),
        )
        return out, tel


# -----------------------------
# Top-level FPKTBlock — with annealing
# -----------------------------

class FPKTBlock(nn.Module):
    def __init__(
        self,
        dim: int,
        num_experts: int,
        num_local_experts: int = 256,
        max_depth: int = 3,
        top_k: int = 4,
        expand_factor: int = 4,
        gate_threshold: float = 0.5,
        gate_hard: bool = True,
        normalize_qk: bool = True,
        temperature: float = 1.0,
        mlp_expansion: int = 4,
        dropout: float = 0.0,
        resid_dropout: float = 0.0,
        anneal_factor: float = 0.9,
        entropy_thresh: float = 0.05,
    ) -> None:
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.drop = nn.Dropout(resid_dropout)

        # Multimodal Encoders
        self.text_encoder = nn.Linear(512, dim)  # Assuming text embedding dim 512
        self.image_encoder = nn.Linear(3*64*64, dim)  # Flattened image (64x64 for Sandbox)
        self.reasoning_encoder = nn.Linear(128, dim)  # Assuming reasoning embedding dim 128

        self.root = FPKTNode(
            dim=dim,
            num_experts=num_experts,
            num_local_experts=num_local_experts,
            top_k=top_k,
            expand_factor=expand_factor,
            max_depth=max_depth,
            depth=0,
            gate_threshold=gate_threshold,
            gate_hard=gate_hard,
            normalize_qk=normalize_qk,
            temperature=temperature,
            mlp_expansion=mlp_expansion,
            dropout=dropout,
            anneal_factor=anneal_factor,
            entropy_thresh=entropy_thresh,
        )

    def forward(self, x: torch.Tensor | Dict[str, Any], modality_weights: Dict[str, float] = None) -> Tuple[torch.Tensor, Dict[str, Any]]:

        device = None
        if isinstance(x, dict):
            # Multimodal input
            encoded_features = []

            # Determine device from input tensors
            if 'text' in x and isinstance(x['text'], torch.Tensor):
                device = x['text'].device
            elif 'image' in x and isinstance(x['image'], torch.Tensor):
                device = x['image'].device
            elif 'reasoning' in x and isinstance(x['reasoning'], torch.Tensor):
                device = x['reasoning'].device

            # Ensure modality weights exist
            if modality_weights is None:
                modality_weights = {'text': 1.0, 'image': 1.0, 'reasoning': 1.0}

            if 'text' in x and isinstance(x['text'], torch.Tensor):
                text_features = self.text_encoder(x['text'])
                encoded_features.append(text_features * modality_weights.get('text', 1.0))

            if 'image' in x and isinstance(x['image'], torch.Tensor):
                # Flatten image: [B, S, C, H, W] -> [B, S, C*H*W]
                # Assuming S is dim 1
                img_flat = x['image'].flatten(start_dim=2)
                img_features = self.image_encoder(img_flat)
                encoded_features.append(img_features * modality_weights.get('image', 1.0))

            if 'reasoning' in x and isinstance(x['reasoning'], torch.Tensor):
                reason_features = self.reasoning_encoder(x['reasoning'])
                encoded_features.append(reason_features * modality_weights.get('reasoning', 1.0))

            if not encoded_features:
                 # Fallback
                 device = torch.device('cpu')
                 combined_features = torch.zeros(1, self.dim, device=device)
            else:
                 combined_features = torch.stack(encoded_features).sum(dim=0)
                 device = combined_features.device
        else:
            combined_features = x
            device = x.device

        z = self.ln(combined_features)
        y, tel = self.root(z)
        out = combined_features + self.drop(y)

        stats = {
            "router_entropy": tel.router_entropy,
            "mean_topk_prob": tel.mean_topk_prob.detach(),
            "expected_depth": tel.expected_depth.detach(),
            "recurse_rate": tel.recurse_rate.detach(),
            "entropy_by_depth": tel.entropy_by_depth.detach(),
            "recurse_rate_by_depth": tel.recurse_rate_by_depth.detach(),
            "tokens_by_depth": tel.tokens_by_depth.detach(),
            "clamp_oob_by_depth": tel.clamp_oob_by_depth.detach(),
            "temp_by_depth": tel.temp_by_depth.detach(),  # New: annealed temps
            "expert_load": tel.expert_load.detach(),
            "warnings": torch.tensor([hash(w) % (2**31 - 1) for w in tel.warnings], device=device, dtype=torch.int64),
        }
        return out, stats
