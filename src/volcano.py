"""
DRM Volcano Plot Generator — CORRECTED
========================================
Threshold updated to +0.8 eV throughout.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mechanism import CATALYSTS


# ============================================================
# TOF MODEL (Volcano shape from competing constraints)
# ============================================================

def compute_tof(dE_C, dE_O, T=900.0):
    kB = 8.617333e-5
    kT = kB * T

    E_C = -6.40 + dE_C
    E_O = -5.50 + dE_O

    alpha = 0.60
    Ea_ref = 0.85
    Ea_CH4 = max(Ea_ref - alpha * dE_C, 0.10)
    k_CH4 = np.exp(-Ea_CH4 / kT)

    E_C_thresh = -5.70
    poisoning = 1.0 / (1.0 + np.exp((E_C - E_C_thresh) / kT))

    k_O = np.exp(-0.5 * abs(dE_O) / kT) if dE_O < 0 else 1.0

    return 1.0 * k_CH4 * poisoning * k_O


def compute_carbon_resistance(dE_C):
    """Carbon resistance index — high when C binds weakly."""
    return np.clip(dE_C / 1.5, 0.0, 1.0)


# ============================================================
# VOLCANO PLOT
# ============================================================

def plot_volcano(save_path="results/figures/volcano_v2.png"):
    n = 60
    dE_C_vals = np.linspace(-0.5, 2.0, n)
    dE_O_vals = np.linspace(-1.0, 1.5, n)

    TOF_grid = np.zeros((n, n))
    C_resist_grid = np.zeros((n, n))
    for i, dE_C in enumerate(dE_C_vals):
        for j, dE_O in enumerate(dE_O_vals):
            TOF_grid[j, i] = compute_tof(dE_C, dE_O)
            C_resist_grid[j, i] = compute_carbon_resistance(dE_C)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5))

    # ---- Panel 1: TOF volcano ----
    ax = axes[0]
    TOF_plot = np.where(TOF_grid > 1e-30, TOF_grid, np.nan)
    levels = np.logspace(np.log10(np.nanmin(TOF_plot)),
                         np.log10(np.nanmax(TOF_plot)), 25)
    cf = ax.contourf(dE_C_vals, dE_O_vals, TOF_plot,
                     levels=levels, cmap="viridis", norm=LogNorm(),
                     extend="both")
    cbar = plt.colorbar(cf, ax=ax)
    cbar.set_label("Relative TOF (arbitrary units)", fontsize=12)

    for name, cat in CATALYSTS.items():
        x, y = cat["dE_C"], cat["dE_O"]
        ax.scatter(x, y, s=200, c="red", edgecolors="black",
                   linewidths=1.5, zorder=10)
        ax.annotate(name, (x, y), xytext=(10, 10),
                    textcoords="offset points", fontsize=10,
                    fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3",
                              fc="white", ec="black", alpha=0.9),
                    zorder=11)

    peak_idx = np.unravel_index(np.nanargmax(TOF_plot), TOF_plot.shape)
    peak_x = dE_C_vals[peak_idx[1]]
    peak_y = dE_O_vals[peak_idx[0]]
    ax.scatter(peak_x, peak_y, s=500, marker="*",
               c="gold", edgecolors="black", linewidths=2,
               zorder=12, label="Volcano peak")
    ax.legend(loc="upper right", fontsize=11)

    ax.set_xlabel(r"$\Delta E_C$ (eV)  —  shift in C binding vs Ni(111)",
                  fontsize=12)
    ax.set_ylabel(r"$\Delta E_O$ (eV)  —  shift in O binding vs Ni(111)",
                  fontsize=12)
    ax.set_title("DRM Activity Volcano Plot\n(T = 900 K, P = 1 bar)",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5, color="white")

    # ---- Panel 2: Carbon resistance map ----
    ax = axes[1]
    cf2 = ax.contourf(dE_C_vals, dE_O_vals, C_resist_grid,
                      levels=20, cmap="RdYlGn", vmin=0, vmax=1)
    cbar2 = plt.colorbar(cf2, ax=ax)
    cbar2.set_label("Carbon resistance index (1 = excellent)", fontsize=12)

    for name, cat in CATALYSTS.items():
        x, y = cat["dE_C"], cat["dE_O"]
        ax.scatter(x, y, s=200, c="black", edgecolors="white",
                   linewidths=1.5, zorder=10)
        ax.annotate(name, (x, y), xytext=(10, 10),
                    textcoords="offset points", fontsize=10,
                    fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3",
                              fc="white", ec="black", alpha=0.9),
                    zorder=11)

    # UPDATED: threshold from +0.5 to +0.8 eV
    ax.axvline(x=0.8, color="blue", linestyle="--", linewidth=2,
               label="Carbon resistance threshold (dE_C ≥ 0.8)")

    ax.set_xlabel(r"$\Delta E_C$ (eV)", fontsize=12)
    ax.set_ylabel(r"$\Delta E_O$ (eV)", fontsize=12)
    ax.set_title("Carbon Resistance Map\n(Design rule: dE_C ≥ +0.8 eV)",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
    ax.legend(loc="upper left", fontsize=10)

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close()

    print(f"OK Saved: {save_path}")
    print(f"\nVolcano peak position:")
    print(f"  dE_C = {peak_x:+.3f} eV")
    print(f"  dE_O = {peak_y:+.3f} eV")
    print(f"  Relative TOF = {TOF_plot[peak_idx]:.3e}")
    print()

    print(f"Catalyst positions:")
    for name, cat in CATALYSTS.items():
        x, y = cat["dE_C"], cat["dE_O"]
        tof = compute_tof(x, y)
        cres = compute_carbon_resistance(x)
        status = "PASS" if x >= 0.8 else "FAIL"
        print(f"  {name:<10} dE_C={x:+.2f}  dE_O={y:+.2f}  "
              f"TOF={tof:.3e}  C-resist={cres:.3f}  [{status}]")

    return peak_x, peak_y


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("DRM VOLCANO PLOT GENERATOR")
    print("=" * 70)
    print()
    peak = plot_volcano()
    print()
    print("=" * 70)
    print("Interpretation:")
    print("  - The volcano peak identifies the optimal C binding")
    print("  - Strong C binding (dE_C << 0) → carbon poisoning")
    print("  - Weak C binding (dE_C >> 0) → poor CH4 activation")
    print("  - Carbon resistance threshold: dE_C ≥ +0.8 eV")
    print("  - Industrial Ni requires promoters to shift dE_C to ~+0.8 eV")
    print("=" * 70)