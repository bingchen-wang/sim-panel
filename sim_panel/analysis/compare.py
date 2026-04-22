"""
Backward-compatible compare entry points.

Prefer importing from sim_panel.analysis.compare.
"""

from sim_panel.analysis.compare.runner import run_comparison

__all__ = ["run_comparison"]