"""
Cantera PFR Reactor Model for DRM
Uses the shared reactor_rate module for consistency with feed_ratio.py.
"""
import numpy as np
import matplotlib.pyplot as plt
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mechanism import CATALYSTS
from reactor_rate import pfr_profile


def plot_reactor(save_path="results/figures/reactor.png"):
    print("Running reactor analysis (unified rate)...\n")

    # All catalysts at baseline conditions
    profiles_all = {}
    for cat_name in CATALYSTS:
        profiles_all[cat_name] = pfr_profile(cat_name, T=900.0, P=1.0,
                                               y_CH4=0.45, y_CO2=0.45)

    baseline = profiles_all["Ni(111)"]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel 1: Axial profile for Ni
    ax = axes[0, 0]
    z = baseline["z"]
    ax.plot(z, baseline["F_CH4"] * 1e3, label="CH4", color="#2E86AB", linewidth=2.5)
    ax.plot(z, baseline["F_CO2"] * 1e3, label="CO2", color="#F18F01", linewidth=2.5)
    ax.plot(z, baseline["F_CO"] * 1e3, label="CO", color="#A23B72", linewidth=2.5)
    ax.plot(z, baseline["F_H2"] * 1e3, label="H2", color="#6A994E", linewidth=2.5)
    ax.set_xlabel("Reactor length (m)", fontsize=12)
    ax.set_ylabel("Molar flow (mmol/s)", fontsize=12)
    ax.set_title("Axial Profile — Ni(111) at 900 K", fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    # Panel 2: CH4 conversion per catalyst
    ax = axes[0, 1]
    for name, cat in CATALYSTS.items():
        prof = profiles_all[name]
        ax.plot(prof["z"], prof["CH4_conv"] * 100, label=name,
                color=cat["color"], linewidth=2.5)
    ax.set_xlabel("Reactor length (m)", fontsize=12)
    ax.set_ylabel("CH4 conversion (%)", fontsize=12)
    ax.set_title("CH4 Conversion Along Reactor", fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    # Panel 3: Equilibrium conversion vs T
    ax = axes[1, 0]
    try:
        import cantera as ct
        T_vals = np.linspace(800, 1100, 20)
        eq_CH4 = []
        for T in T_vals:
            gas = ct.Solution("gri30.yaml")
            gas.TPX = T, 1e5, {"CH4": 0.45, "CO2": 0.45, "N2": 0.10}
            gas.equilibrate("TP")
            X_CH4 = gas["CH4"].X[0]
            X_CO2 = gas["CO2"].X[0]
            eq_CH4.append((0.45 - X_CH4) / 0.45 * 100)
        ax.plot(T_vals, eq_CH4, marker="o", color="#2E86AB", linewidth=2.5,
                label="CH4 equilibrium")
    except Exception as e:
        ax.text(0.5, 0.5, f"Equilibrium: {e}", ha="center",
                transform=ax.transAxes)
    ax.set_xlabel("Temperature (K)", fontsize=12)
    ax.set_ylabel("Equilibrium conversion (%)", fontsize=12)
    ax.set_title("Equilibrium Conversion vs T", fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)

    # Panel 4: Syngas ratio for Ni at 3 feed ratios
    ax = axes[1, 1]
    for label, ych4, yco2, c in [
        ("CH4:CO2 = 1:1", 0.45, 0.45, "#2E86AB"),
        ("CH4:CO2 = 2:1", 0.60, 0.30, "#F18F01"),
        ("CH4:CO2 = 1:2", 0.30, 0.60, "#A23B72"),
    ]:
        prof = pfr_profile("Ni(111)", T=900.0, P=1.0, y_CH4=ych4, y_CO2=yco2)
        ax.plot(prof["z"], prof["H2_CO"], label=label, color=c, linewidth=2.5)
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1,
               label="Ideal syngas (H2/CO = 1)")
    ax.set_xlabel("Reactor length (m)", fontsize=12)
    ax.set_ylabel("H2/CO ratio", fontsize=12)
    ax.set_title("Syngas Ratio vs Feed Ratio (Ni)",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    plt.suptitle("Cantera PFR Reactor Analysis — Dry Reforming of Methane",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"OK Saved: {save_path}\n")

    # Summary
    print("=" * 70)
    print("REACTOR SUMMARY — T = 900 K, L = 0.5 m, P = 1 bar")
    print("=" * 70)
    print(f"\n{'Catalyst':<12}{'CH4 conv (%)':>15}{'CO2 conv (%)':>15}{'H2/CO':>12}")
    print("-" * 55)
    for name, prof in profiles_all.items():
        print(f"{name:<12}{prof['CH4_conv'][-1]*100:>15.3f}"
              f"{prof['CO2_conv'][-1]*100:>15.3f}"
              f"{prof['H2_CO'][-1]:>12.3f}")


if __name__ == "__main__":
    plot_reactor()