"""
Temperature Sensitivity Analysis for DRM
FIXED: Arrhenius plot now includes Ru, Rh, Co (all six catalysts).
"""
import numpy as np
import matplotlib.pyplot as plt
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mechanism import CATALYSTS

kB = 8.617333e-5


def drm_rate(dE_C, dE_O, T):
    kT = kB * T
    E_C = -6.40 + dE_C
    E_O = -5.50 + dE_O
    Ea_CH4 = max(0.85 - 0.60 * dE_C, 0.10)
    k_CH4 = np.exp(-Ea_CH4 / kT)
    E_C_thresh = -5.70
    poisoning = 1.0 / (1.0 + np.exp((E_C - E_C_thresh) / kT))
    k_O = np.exp(-0.5 * abs(dE_O) / kT) if dE_O < 0 else 1.0
    return k_CH4 * poisoning * k_O


def carbon_resistance(dE_C, T):
    base = np.clip(dE_C / 1.5, 0.0, 1.0)
    T_ref = 900.0
    T_factor = 1.0 / (1.0 + np.exp(-(T - T_ref) / 100.0))
    T_factor = 0.7 + 0.6 * (T_factor - 0.5) * 2
    T_factor = np.clip(T_factor, 0.4, 1.0)
    return base * T_factor


def h2_co_ratio(dE_C, dE_O, T):
    T_ref = 900.0
    T_factor = 1.0 + np.exp(-(T - T_ref) / 150.0)
    desc_factor = 1.0 + 0.1 * (dE_C - 0.7)
    return np.clip(T_factor * desc_factor, 0.5, 3.0)


def apparent_Ea(catalyst_name, T_range=(750, 1000)):
    cat = CATALYSTS[catalyst_name]
    T_vals = np.linspace(*T_range, 20)
    tofs = np.array([drm_rate(cat["dE_C"], cat["dE_O"], T) for T in T_vals])
    mask = tofs > 1e-30
    T_m, tof_m = T_vals[mask], tofs[mask]
    if len(T_m) < 3:
        return np.nan
    slope, _ = np.polyfit(1.0 / T_m, np.log(tof_m), 1)
    return -slope * kB


def plot_sensitivity(save_path="results/figures/sensitivity.png"):
    print("Running temperature sensitivity...\n")
    T_vals = np.linspace(700, 1100, 30)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel 1: TOF vs T
    ax = axes[0, 0]
    for name, cat in CATALYSTS.items():
        tofs = np.array([drm_rate(cat["dE_C"], cat["dE_O"], T) for T in T_vals])
        ax.semilogy(T_vals, tofs, marker="o", markersize=4, label=name,
                    color=cat["color"], linewidth=2)
    ax.set_xlabel("Temperature (K)", fontsize=12)
    ax.set_ylabel("Relative TOF (arbitrary units)", fontsize=12)
    ax.set_title("DRM Activity vs Temperature", fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3, which="both")
    ax.legend(fontsize=9, loc="lower right")

    # Panel 2: Carbon resistance vs T
    ax = axes[0, 1]
    for name, cat in CATALYSTS.items():
        cres = np.array([carbon_resistance(cat["dE_C"], T) for T in T_vals])
        ax.plot(T_vals, cres, marker="s", markersize=4, label=name,
                color=cat["color"], linewidth=2)
    ax.set_xlabel("Temperature (K)", fontsize=12)
    ax.set_ylabel("Carbon resistance index", fontsize=12)
    ax.set_title("Carbon Resistance vs Temperature",
                 fontsize=13, fontweight="bold")
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, loc="lower right")

    # Panel 3: Arrhenius plot — NOW WITH ALL SIX CATALYSTS
    ax = axes[1, 0]
    for name, cat in CATALYSTS.items():
        tofs = np.array([drm_rate(cat["dE_C"], cat["dE_O"], T) for T in T_vals])
        mask = tofs > 1e-30
        Ea = apparent_Ea(name)
        label = f"{name} (Ea={Ea*1000:.0f} meV)" if not np.isnan(Ea) else name
        ax.plot(1000.0 / T_vals[mask], np.log(tofs[mask]),
                marker="o", markersize=4, label=label,
                color=cat["color"], linewidth=2)

    ax.set_xlabel("1000/T (K$^{-1}$)", fontsize=12)
    ax.set_ylabel("ln(Relative TOF)", fontsize=12)
    ax.set_title("Arrhenius Plot — All Six Catalysts",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc="upper right")

    # Panel 4: H2/CO ratio vs T
    ax = axes[1, 1]
    for name, cat in CATALYSTS.items():
        ratios = np.array([h2_co_ratio(cat["dE_C"], cat["dE_O"], T)
                            for T in T_vals])
        ax.plot(T_vals, ratios, marker="^", markersize=4, label=name,
                color=cat["color"], linewidth=2)
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1,
               label="Ideal syngas (H2/CO = 1)")
    ax.set_xlabel("Temperature (K)", fontsize=12)
    ax.set_ylabel("H2/CO ratio", fontsize=12)
    ax.set_title("Syngas H2/CO Ratio vs Temperature",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, loc="upper right")

    plt.suptitle("Temperature Sensitivity Analysis — Dry Reforming of Methane",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"OK Saved: {save_path}\n")

    print("=" * 70)
    print("SUMMARY AT T = 900 K")
    print("=" * 70)
    print(f"\n{'Catalyst':<12}{'TOF':>12}{'C-resist':>12}{'H2/CO':>10}{'Ea (meV)':>14}")
    print("-" * 60)
    for name, cat in CATALYSTS.items():
        tof = drm_rate(cat["dE_C"], cat["dE_O"], 900)
        cres = carbon_resistance(cat["dE_C"], 900)
        ratio = h2_co_ratio(cat["dE_C"], cat["dE_O"], 900)
        Ea = apparent_Ea(name)
        Ea_str = f"{Ea*1000:.0f}" if not np.isnan(Ea) else "N/A"
        print(f"{name:<12}{tof:>12.3e}{cres:>12.3f}{ratio:>10.3f}{Ea_str:>14}")


if __name__ == "__main__":
    print("=" * 70)
    print("DRM TEMPERATURE SENSITIVITY ANALYSIS")
    print("=" * 70)
    print()
    plot_sensitivity()