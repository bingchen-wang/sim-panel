from __future__ import annotations

from sim_panel.policies.base import Policy, PolicyConfig
from sim_panel.policies.manual import ManualAssignmentPolicy
from sim_panel.policies.random import RandomAssignmentPolicy
from sim_panel.policies.self_selection import SelfSelectionPolicy


def build_policy(cfg: PolicyConfig) -> Policy:
    if cfg.name == "random":
        return RandomAssignmentPolicy(cfg)
    if cfg.name == "manual":
        return ManualAssignmentPolicy(cfg)
    if cfg.name == "self_selection":
        return SelfSelectionPolicy(cfg)
    raise ValueError(f"Unknown policy name: {cfg.name}")