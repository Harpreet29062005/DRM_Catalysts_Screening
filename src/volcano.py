"""
DRM Volcano Plot Generator
============================

Generates a Sabatier volcano plot for Dry Reforming of Methane across
the (dE_C, dE_O) descriptor space.

Physical model:
    - TOF is limited by two competing factors:
        (1) CH4 activation: requires reasonable C binding (not too weak)
        (2) Carbon removal: requires weak C binding (not too strong)
    - The volcano peak emerges at the balance point
    - Carbon resistance decreases monotonically with dE_C

Produces:
    Figure 1: Two-panel volcano plot (activity + carbon resistance)
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
    """
    Compute relative TOF as a function of descriptors.

    Physics:
        - CH4 activation requires some C binding: activity ∝ exp(-Ea_CH4/kT)
          where Ea_CH4 increases as C binds more weakly
        - Carbon poisoning occurs when C binds too strongly
          poisoning factor = 1 / (1 + K_C) with K_C from Langmuir

    Result: volcano shape in dE_C
    """
    kB = 8.617333e-5
    kT = kB * T

    # Reference: Ni(111) at dE_C = 0, dE_O = 0
    # E_C(Ni) = -6.40 eV
    E_C = -6.40 + dE_C
    E_O = -5.50 + dE_O

    # --- Factor 1: CH4 activation barrier ---
    # Stronger C binding → lower barrier for CH4 dissociation (BEP relation)
    # We use a BEP-like relation: Ea_CH4 = Ea_ref - alpha * dE_C
    # This means weaker C binding → higher barrier → lower activity
    alpha = 0.60
    Ea_ref = 0.85   # eV, barrier on Ni
    Ea_CH4 = max(Ea_ref - alpha * dE_C, 0.10)
    k_CH4 = np.exp(-Ea_CH4 / kT)

    # --- Factor 2: Carbon poisoning ---
    # Stronger C binding → carbon accumulates → poisons surface
    # Use Langmuir-like factor: coverage_C ∝ exp(-E_C/kT)
    # Poisoning factor = 1 / (1 + exp((E_C - E_C_thresh)/kT))
    # with E_C_thresh = -5.7 eV (weak enough C binding is safe)
    E_C_thresh = -5.70
    # Sigmoid centered at threshold
    # When E_C >> -5.70 (weak binding), poisoning factor → 1
    # When E_C << -5.70 (strong binding), poisoning factor → 0
    poisoning = 1.0 / (1.0 + np.exp((E_C - E_C_thresh) / kT))

    # --- Factor 3: O availability (mild effect) ---
    # Slightly stronger O binding helps gasification
    # But O should not bind too strongly either
    k_O = np.exp(-0.5 * abs(dE_O) / kT) if dE_O < 0 else 1.0

    # Combine
    TOF = 1.0 * k_CH4 * poisoning * k_O

    return TOF


def compute_carbon_resistance(dE_C):
    """Carbon resistance index — high when C binds weakly."""
    # Normalize to descriptor range of interest
    # At dE_C = 0 (Ni), resistance = 0.0
    # At dE_C = +1.5, resistance = 1.0
    return np.clip(dE_C / 1.5, 0.0, 1.0)


# ============================================================
# VOLCANO PLOT
# ============================================================

def plot_volcano(save_path="results/figures/volcano.png"):
    # Descriptor grid
    n = 60
    dE_C_vals = np.linspace(-0.5, 2.0, n)
    dE_O_vals = np.linspace(-1.0, 1.5, n)

    # 2D grid of TOF and carbon resistance
    TOF_grid = np.zeros((n, n))
    C_resist_grid = np.zeros((n, n))
    for i, dE_C in enumerate(dE_C_vals):
        for j, dE_O in enumerate(dE_O_vals):
            TOF_grid[j, i] = compute_tof(dE_C, dE_O)
            C_resist_grid[j, i] = compute_carbon_resistance(dE_C)

    # Figure with two panels
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5))

    # ---- Panel 1: TOF volcano ----
    ax = axes[0]
    # Avoid log(0)
    TOF_plot = np.where(TOF_grid > 1e-30, TOF_grid, np.nan)
    levels = np.logspace(np.log10(np.nanmin(TOF_plot)),
                         np.log10(np.nanmax(TOF_plot)), 25)
    cf = ax.contourf(dE_C_vals, dE_O_vals, TOF_plot,
                     levels=levels, cmap="viridis", norm=LogNorm(),
                     extend="both")
    cbar = plt.colorbar(cf, ax=ax)
    cbar.set_label("Relative TOF (arbitrary units)", fontsize=12)

    # Catalyst positions
    for name, cat in CATALYSTS.items():
        x = cat["dE_C"]
        y = cat["dE_O"]
        ax.scatter(x, y, s=200, c="red", edgecolors="black",
                   linewidths=1.5, zorder=10)
        ax.annotate(name, (x, y), xytext=(10, 10),
                    textcoords="offset points", fontsize=10,
                    fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3",
                              fc="white", ec="black", alpha=0.9),
                    zorder=11)

    # Volcano peak
    peak_idx = np.unravel_index(np.nanargmax(TOF_plot), TOF_plot.shape)
    peak_x = dE_C_vals[peak_idx[1]]
    peak_y = dE_O_vals[peak_idx[0]]
    ax.scatter(peak_x, peak_y, s=500, marker="*",
               c="gold", edgecolors="black", linewidths=2,
               zorder=12, label=f"Volcano peak")
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

    # Catalyst positions
    for name, cat in CATALYSTS.items():
        x = cat["dE_C"]
        y = cat["dE_O"]
        ax.scatter(x, y, s=200, c="black", edgecolors="white",
                   linewidths=1.5, zorder=10)
        ax.annotate(name, (x, y), xytext=(10, 10),
                    textcoords="offset points", fontsize=10,
                    fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3",
                              fc="white", ec="black", alpha=0.9),
                    zorder=11)

    # Design rule line
    ax.axvline(x=0.5, color="blue", linestyle="--", linewidth=2,
               label="Carbon resistance threshold (dE_C ≥ 0.5)")
    ax.legend(loc="upper left", fontsize=10)

    ax.set_xlabel(r"$\Delta E_C$ (eV)", fontsize=12)
    ax.set_ylabel(r"$\Delta E_O$ (eV)", fontsize=12)
    ax.set_title("Carbon Resistance Map\n(Design rule: dE_C ≥ +0.5 eV)",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close()

    print(f"OK Saved: {save_path}")

    # ---- Print analysis ----
    print(f"\nVolcano peak position:")
    print(f"  dE_C = {peak_x:+.3f} eV")
    print(f"  dE_O = {peak_y:+.3f} eV")
    print(f"  Relative TOF = {TOF_plot[peak_idx]:.3e}")
    print()

    print(f"Catalyst positions:")
    for name, cat in CATALYSTS.items():
        x = cat["dE_C"]
        y = cat["dE_O"]
        tof = compute_tof(x, y)
        cres = compute_carbon_resistance(x)
        status = "PASS" if x >= 0.5 else "FAIL"
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
    print("  - Carbon resistance increases monotonically with dE_C")
    print("  - Industrial Ni requires promoters to shift dE_C to ~+0.5 eV")
    print("=" * 70)