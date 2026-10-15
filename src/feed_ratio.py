"""
Feed Ratio Study for DRM
=========================
Runs the PFR reactor at three CH4:CO2 ratios (1:1, 2:1, 1:2) to study
how feed composition affects conversion, H2/CO ratio, and carbon risk.
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


def pfr_profile(catalyst_name, T, P, y_CH4, y_CO2, n_points=50):
    """1D PFR profile with given feed."""
    cat = CATALYSTS[catalyst_name]
    dE_C, dE_O = cat["dE_C"], cat["dE_O"]

    L = 0.5
    A_cross = np.pi * (0.1 / 2) ** 2
    z = np.linspace(0, L, n_points)

    F_total = 1e-3
    F_CH4_in = F_total * y_CH4
    F_CO2_in = F_total * y_CO2

    S_BET = 10.0
    rho_cat = 800
    site_density = 1.5e19
    void = 0.4
    N_sites_m3 = S_BET * 1e3 * rho_cat * site_density * (1 - void)

    r_per_site = drm_rate(dE_C, dE_O, T)
    N_A = 6.022e23
    r_vol = min(r_per_site * N_sites_m3 / N_A, 100.0)

    F_CH4 = np.zeros(n_points); F_CO2 = np.zeros(n_points)
    F_CO = np.zeros(n_points); F_H2 = np.zeros(n_points)

    F_CH4[0] = F_CH4_in; F_CO2[0] = F_CO2_in

    for i in range(1, n_points):
        dz = z[i] - z[i-1]
        dV = A_cross * dz
        dF = r_vol * dV
        dF = min(dF, F_CH4[i-1] * 0.5, F_CO2[i-1] * 0.5)
        F_CH4[i] = F_CH4[i-1] - dF
        F_CO2[i] = F_CO2[i-1] - dF
        F_CO[i]  = F_CO[i-1] + 2 * dF
        F_H2[i]  = F_H2[i-1] + 2 * dF

    CH4_conv = (F_CH4_in - F_CH4) / F_CH4_in
    CO2_conv = (F_CO2_in - F_CO2) / F_CO2_in
    with np.errstate(divide='ignore', invalid='ignore'):
        H2_CO = np.where(F_CO > 1e-12, F_H2 / F_CO, 0.0)

    # Carbon risk index: 0 (safe) to 1 (severe coking risk)
    # Based on dE_C — catalysts with strong C binding have higher risk
    carbon_risk = max(0.0, 1.0 - dE_C / 1.5)

    return {
        "z": z, "F_CH4": F_CH4, "F_CO2": F_CO2, "F_CO": F_CO,
        "F_H2": F_H2, "CH4_conv": CH4_conv, "CO2_conv": CO2_conv,
        "H2_CO": H2_CO, "carbon_risk": carbon_risk,
        "y_CH4": y_CH4, "y_CO2": y_CO2,
    }


def plot_feed_ratio(save_path="results/figures/feed_ratio.png"):
    print("Running feed ratio study...\n")

    ratios = [
        ("1:1 (equimolar)", 0.45, 0.45),
        ("2:1 (CH4 rich)", 0.60, 0.30),
        ("1:2 (CO2 rich)", 0.30, 0.60),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # ---- Panel 1: CH4 conversion vs ratio ----
    ax = axes[0, 0]
    colors = ["#2E86AB", "#F18F01", "#A23B72"]
    for (label, y_CH4, y_CO2), c in zip(ratios, colors):
        prof = pfr_profile("Ni(111)", 900.0, 1.0, y_CH4, y_CO2)
        ax.plot(prof["z"], prof["CH4_conv"] * 100,
                label=f"CH4:CO2 = {label}", color=c, linewidth=2.5)
    ax.set_xlabel("Reactor length (m)", fontsize=12)
    ax.set_ylabel("CH4 conversion (%)", fontsize=12)
    ax.set_title("CH4 Conversion vs Feed Ratio (Ni, 900 K)",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    # ---- Panel 2: H2/CO ratio vs feed ratio ----
    ax = axes[0, 1]
    for (label, y_CH4, y_CO2), c in zip(ratios, colors):
        prof = pfr_profile("Ni(111)", 900.0, 1.0, y_CH4, y_CO2)
        ax.plot(prof["z"], prof["H2_CO"],
                label=f"CH4:CO2 = {label}", color=c, linewidth=2.5)
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1,
               label="Ideal syngas (H2/CO = 1)")
    ax.set_xlabel("Reactor length (m)", fontsize=12)
    ax.set_ylabel("H2/CO ratio", fontsize=12)
    ax.set_title("Syngas Ratio vs Feed Ratio (Ni, 900 K)",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    # ---- Panel 3: Carbon risk comparison ----
    ax = axes[1, 0]
    cats = list(CATALYSTS.keys())
    risks = [max(0.0, 1.0 - CATALYSTS[c]["dE_C"] / 1.5) for c in cats]
    colors_cat = [CATALYSTS[c]["color"] for c in cats]
    bars = ax.bar(cats, risks, color=colors_cat, edgecolor="black", linewidth=1.2)
    ax.set_ylabel("Carbon risk index", fontsize=12)
    ax.set_title("Carbon Risk at Working Conditions",
                 fontsize=13, fontweight="bold")
    ax.set_ylim(0, 1.05)
    ax.axhline(0.5, color="red", linestyle="--", linewidth=1,
               label="Safety threshold")
    ax.grid(True, alpha=0.3, axis="y")
    ax.tick_params(axis="x", rotation=20)
    ax.legend(fontsize=10)

    # ---- Panel 4: Summary table ----
    ax = axes[1, 1]
    ax.axis("off")

    table_data = [["Feed ratio", "CH4 conv", "CO2 conv", "H2/CO"]]
    for label, y_CH4, y_CO2 in ratios:
        prof = pfr_profile("Ni(111)", 900.0, 1.0, y_CH4, y_CO2)
        table_data.append([
            label,
            f"{prof['CH4_conv'][-1]*100:.1f}%",
            f"{prof['CO2_conv'][-1]*100:.1f}%",
            f"{prof['H2_CO'][-1]:.2f}",
        ])

    tbl = ax.table(cellText=table_data, loc="center",
                   cellLoc="center", colWidths=[0.32, 0.22, 0.22, 0.18])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(12)
    tbl.scale(1.3, 2.5)

    for i in range(len(table_data[0])):
        tbl[(0, i)].set_facecolor("#2E86AB")
        tbl[(0, i)].set_text_props(weight="bold", color="white")

    ax.set_title("Reactor Performance Summary",
                 fontsize=13, fontweight="bold", pad=20)

    plt.suptitle("Feed Ratio Study — DRM on Ni(111) at 900 K",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"OK Saved: {save_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("FEED RATIO SUMMARY (Ni, 900 K, 0.5 m reactor)")
    print("=" * 70)
    print(f"\n{'Feed ratio':<20}{'CH4 conv':>12}{'CO2 conv':>12}{'H2/CO':>10}")
    print("-" * 54)
    for label, y_CH4, y_CO2 in ratios:
        prof = pfr_profile("Ni(111)", 900.0, 1.0, y_CH4, y_CO2)
        print(f"{label:<20}{prof['CH4_conv'][-1]*100:>11.1f}%"
              f"{prof['CO2_conv'][-1]*100:>11.1f}%"
              f"{prof['H2_CO'][-1]:>10.2f}")


if __name__ == "__main__":
    plot_feed_ratio()
    print("\nOK Feed ratio study complete.")