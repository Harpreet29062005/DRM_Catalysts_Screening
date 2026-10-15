"""
Temperature Sensitivity Analysis for Dry Reforming of Methane
==============================================================

Studies the effect of temperature (700-1100 K) on:
  - Relative TOF for syngas production
  - Carbon resistance index
  - Apparent activation energy (Arrhenius analysis)
  - H2/CO product ratio (industrial syngas quality metric)

Generates Figure 2 with 4 panels.
"""

import numpy as np
import matplotlib.pyplot as plt
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mechanism import CATALYSTS


kB = 8.617333e-5   # eV/K


# ============================================================
# DRM KINETIC MODEL (descriptor-based)
# ============================================================

def compute_tof(dE_C, dE_O, T):
    """
    Relative TOF for DRM as a function of descriptors and temperature.
    Same physics as volcano.py but with T as a variable.
    """
    kT = kB * T

    E_C = -6.40 + dE_C
    E_O = -5.50 + dE_O

    # CH4 activation barrier (BEP relation)
    alpha = 0.60
    Ea_ref = 0.85
    Ea_CH4 = max(Ea_ref - alpha * dE_C, 0.10)
    k_CH4 = np.exp(-Ea_CH4 / kT)

    # Carbon poisoning factor (sigmoid around threshold)
    E_C_thresh = -5.70
    poisoning = 1.0 / (1.0 + np.exp((E_C - E_C_thresh) / kT))

    # O availability factor
    k_O = np.exp(-0.5 * abs(dE_O) / kT) if dE_O < 0 else 1.0

    TOF = 1.0 * k_CH4 * poisoning * k_O
    return TOF


def compute_carbon_resistance(dE_C, T):
    """
    Carbon resistance index at temperature T.
    Higher T → easier to remove carbon → higher resistance
    Lower T → carbon accumulates → lower resistance
    """
    # Base resistance from descriptor
    base = np.clip(dE_C / 1.5, 0.0, 1.0)

    # Temperature effect: resistance improves at high T
    # At 900 K reference, multiply by sigmoid that goes from ~0.7 at 700 K to ~1.0 at 1100 K
    T_ref = 900.0
    T_factor = 1.0 / (1.0 + np.exp(-(T - T_ref) / 100.0))  # 0.5 at 900 K
    # Scale so factor is ~1 at high T and ~0.5 at low T
    T_factor = 0.7 + 0.6 * (T_factor - 0.5) * 2
    T_factor = np.clip(T_factor, 0.4, 1.0)

    return base * T_factor


def compute_h2_co_ratio(dE_C, dE_O, T):
    """
    H2/CO ratio from product distribution.
    At low T: methanation dominates → H2/CO > 1
    At high T: DRM dominates → H2/CO ≈ 1
    Descriptors weakly affect ratio via side reactions
    """
    # Reference: DRM gives 1:1 ratio ideally
    # Methanation (CO + 3H2 → CH4 + H2O) consumes H2 at low T
    T_ref = 900.0
    # Deviation at low T: ratio goes up to 2
    T_factor = 1.0 + np.exp(-(T - T_ref) / 150.0)
    # Weak dependence on descriptor
    desc_factor = 1.0 + 0.1 * (dE_C - 0.7)
    ratio = T_factor * desc_factor
    return np.clip(ratio, 0.5, 3.0)


# ============================================================
# ARRHENIUS ANALYSIS
# ============================================================

def compute_apparent_Ea(catalyst_name, T_range=(750, 1000)):
    """Extract apparent activation energy from Arrhenius plot."""
    cat = CATALYSTS[catalyst_name]
    T_vals = np.linspace(*T_range, 20)
    tofs = np.array([compute_tof(cat["dE_C"], cat["dE_O"], T) for T in T_vals])

    # Filter out tiny values
    mask = tofs > 1e-30
    T_m = T_vals[mask]
    tof_m = tofs[mask]

    if len(T_m) < 3:
        return np.nan

    x = 1.0 / T_m
    y = np.log(tof_m)
    slope, _ = np.polyfit(x, y, 1)
    Ea = -slope * kB
    return Ea


# ============================================================
# MAIN PLOT
# ============================================================

def plot_sensitivity(save_path="results/figures/sensitivity.png"):
    print("Running temperature sensitivity analysis...\n")

    T_vals = np.linspace(700, 1100, 30)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # ---- Panel 1: TOF vs T for all catalysts ----
    ax = axes[0, 0]
    for name, cat in CATALYSTS.items():
        tofs = np.array([compute_tof(cat["dE_C"], cat["dE_O"], T) for T in T_vals])
        ax.semilogy(T_vals, tofs, marker="o", markersize=4,
                    label=name, color=cat["color"], linewidth=2)

    ax.set_xlabel("Temperature (K)", fontsize=12)
    ax.set_ylabel("Relative TOF (arbitrary units)", fontsize=12)
    ax.set_title("DRM Activity vs Temperature", fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3, which="both")
    ax.legend(fontsize=9, loc="lower right")

    # ---- Panel 2: Carbon resistance vs T ----
    ax = axes[0, 1]
    for name, cat in CATALYSTS.items():
        cres = np.array([compute_carbon_resistance(cat["dE_C"], T) for T in T_vals])
        ax.plot(T_vals, cres, marker="s", markersize=4,
                label=name, color=cat["color"], linewidth=2)

    ax.set_xlabel("Temperature (K)", fontsize=12)
    ax.set_ylabel("Carbon resistance index", fontsize=12)
    ax.set_title("Carbon Resistance vs Temperature",
                 fontsize=13, fontweight="bold")
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, loc="lower right")

    # ---- Panel 3: Arrhenius plot (log TOF vs 1000/T) ----
    ax = axes[1, 0]
    for name in ["Ni(111)", "Pt(111)", "Ir(111)"]:
        cat = CATALYSTS[name]
        tofs = np.array([compute_tof(cat["dE_C"], cat["dE_O"], T) for T in T_vals])
        mask = tofs > 1e-30
        ax.plot(1000.0 / T_vals[mask], np.log(tofs[mask]),
                marker="o", markersize=4, label=name,
                color=cat["color"], linewidth=2)

        # Fit line for activation energy
        Ea = compute_apparent_Ea(name)
        if not np.isnan(Ea):
            x_fit = 1000.0 / T_vals[mask]
            slope = -Ea / kB
            # Find intercept from fit
            y_vals = np.log(tofs[mask])
            _, intercept = np.polyfit(1.0 / T_vals[mask], y_vals, 1)
            y_fit = slope * (1.0 / T_vals[mask]) + intercept
            ax.plot(x_fit, y_fit, "--", linewidth=1.5, alpha=0.7,
                    color=cat["color"])

    ax.set_xlabel("1000/T (1/K)", fontsize=12)
    ax.set_ylabel("ln(Relative TOF)", fontsize=12)
    ax.set_title("Arrhenius Plot (Ni, Pt, Ir)", fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    # ---- Panel 4: H2/CO ratio vs T ----
    ax = axes[1, 1]
    for name, cat in CATALYSTS.items():
        ratios = np.array([compute_h2_co_ratio(cat["dE_C"], cat["dE_O"], T)
                            for T in T_vals])
        ax.plot(T_vals, ratios, marker="^", markersize=4,
                label=name, color=cat["color"], linewidth=2)

    ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1,
               label="Ideal syngas (H2/CO = 1)")
    ax.set_xlabel("Temperature (K)", fontsize=12)
    ax.set_ylabel("H2/CO ratio", fontsize=12)
    ax.set_title("Syngas H2/CO Ratio vs Temperature",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, loc="upper right")

    plt.suptitle("Temperature Sensitivity Analysis — Dry Reforming of Methane",
                 fontsize=14, fontweight="bold", y=1.00)
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"OK Saved: {save_path}\n")

    # ---- Summary table ----
    print("=" * 70)
    print("SUMMARY AT T = 900 K")
    print("=" * 70)
    print(f"\n{'Catalyst':<12}{'TOF':>12}{'C-resist':>12}{'H2/CO':>10}{'Ea (meV)':>14}")
    print("-" * 60)

    for name, cat in CATALYSTS.items():
        tof = compute_tof(cat["dE_C"], cat["dE_O"], 900)
        cres = compute_carbon_resistance(cat["dE_C"], 900)
        ratio = compute_h2_co_ratio(cat["dE_C"], cat["dE_O"], 900)
        Ea = compute_apparent_Ea(name)
        Ea_str = f"{Ea*1000:.0f}" if not np.isnan(Ea) else "N/A"
        print(f"{name:<12}{tof:>12.3e}{cres:>12.3f}{ratio:>10.3f}{Ea_str:>14}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("DRM TEMPERATURE SENSITIVITY ANALYSIS")
    print("=" * 70)
    print()
    plot_sensitivity()
    print()
    print("=" * 70)
    print("Interpretation:")
    print("  - Activity increases with T (Arrhenius-like)")
    print("  - Carbon resistance improves at higher T (carbon gasification)")
    print("  - Ni deactivates fastest; Ir/Pt remain stable at all T")
    print("  - H2/CO ratio approaches 1 at high T (ideal DRM stoichiometry)")
    print("=" * 70)