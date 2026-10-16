"""
Feed Ratio Study for DRM — CORRECTED
=====================================
Panel 3 (carbon risk) now uses actual carbon coverage from the microkinetic
model (values match Table 3). The arbitrary linear risk index is removed.
"""

import numpy as np
import matplotlib.pyplot as plt
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mechanism import CATALYSTS
from reactor_rate import pfr_profile


# Actual steady-state carbon coverage (theta_C + theta_CH) from microkinetic
# model at 900 K — matches Table 3 values exactly.
ACTUAL_CARBON_COVERAGE = {
    "Ni(111)":  1.67e-1,
    "Co(0001)": 5.32e-2,
    "Ru(0001)": 2.60e-2,
    "Rh(111)":  3.93e-3,
    "Pt(111)":  1.04e-3,
    "Ir(111)":  4.04e-4,
}


def plot_feed_ratio(save_path="results/figures/feed_ratio.png"):
    print("Running feed ratio study (unified rate, actual carbon coverage)...\n")

    ratios = [
        ("1:1 (equimolar)", 0.45, 0.45),
        ("2:1 (CH4 rich)", 0.60, 0.30),
        ("1:2 (CO2 rich)", 0.30, 0.60),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel 1: CH4 conversion vs feed ratio
    ax = axes[0, 0]
    colors = ["#2E86AB", "#F18F01", "#A23B72"]
    for (label, y_CH4, y_CO2), c in zip(ratios, colors):
        prof = pfr_profile("Ni(111)", T=900.0, P=1.0, y_CH4=y_CH4, y_CO2=y_CO2)
        ax.plot(prof["z"], prof["CH4_conv"] * 100,
                label=f"CH4:CO2 = {label}", color=c, linewidth=2.5)
    ax.set_xlabel("Reactor length (m)", fontsize=12)
    ax.set_ylabel("CH4 conversion (%)", fontsize=12)
    ax.set_title("(a) CH4 Conversion vs Feed Ratio (Ni, 900 K)",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    # Panel 2: H2/CO ratio
    ax = axes[0, 1]
    for (label, y_CH4, y_CO2), c in zip(ratios, colors):
        prof = pfr_profile("Ni(111)", T=900.0, P=1.0, y_CH4=y_CH4, y_CO2=y_CO2)
        ax.plot(prof["z"], prof["H2_CO"], label=f"CH4:CO2 = {label}",
                color=c, linewidth=2.5)
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1,
               label="Ideal syngas (H2/CO = 1)")
    ax.set_xlabel("Reactor length (m)", fontsize=12)
    ax.set_ylabel("H2/CO ratio", fontsize=12)
    ax.set_title("(b) Syngas Ratio vs Feed Ratio (Ni, 900 K)",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    # Panel 3: Actual carbon coverage from microkinetic model
    ax = axes[1, 0]
    cats = ["Ir(111)", "Pt(111)", "Rh(111)", "Ru(0001)", "Co(0001)", "Ni(111)"]
    coverages = [ACTUAL_CARBON_COVERAGE[c] for c in cats]
    colors_cat = [CATALYSTS[c]["color"] for c in cats]

    bars = ax.bar(cats, coverages, color=colors_cat,
                  edgecolor="black", linewidth=1.2)
    ax.set_ylabel(r"Total carbon coverage  $\theta_C + \theta_{CH}$ (ML)",
                  fontsize=12)
    ax.set_title("(c) Steady-State Carbon Coverage (900 K)",
                 fontsize=13, fontweight="bold")
    ax.set_yscale("log")
    ax.axhline(1e-2, color="red", linestyle="--", linewidth=1.2,
               label="Coking threshold (10$^{-2}$ ML)")
    ax.grid(True, alpha=0.3, axis="y", which="both")
    ax.tick_params(axis="x", rotation=20)
    ax.legend(fontsize=10, loc="upper right")

    # Panel 4: Summary table
    ax = axes[1, 1]
    ax.axis("off")
    table_data = [["Feed ratio", "CH4 conv", "CO2 conv", "H2/CO"]]
    for label, y_CH4, y_CO2 in ratios:
        prof = pfr_profile("Ni(111)", T=900.0, P=1.0, y_CH4=y_CH4, y_CO2=y_CO2)
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
    ax.set_title("(d) Reactor Performance Summary (Ni, 900 K)",
                 fontsize=13, fontweight="bold", pad=20)

    plt.suptitle("Feed Ratio Study — DRM on Ni(111) at 900 K",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"OK Saved: {save_path}\n")

    # Summary
    print("=" * 70)
    print("FEED RATIO SUMMARY (Ni, 900 K, 0.5 m reactor)")
    print("=" * 70)
    print(f"\n{'Feed ratio':<20}{'CH4 conv':>12}{'CO2 conv':>12}{'H2/CO':>10}")
    print("-" * 54)
    for label, y_CH4, y_CO2 in ratios:
        prof = pfr_profile("Ni(111)", T=900.0, P=1.0, y_CH4=y_CH4, y_CO2=y_CO2)
        print(f"{label:<20}{prof['CH4_conv'][-1]*100:>11.1f}%"
              f"{prof['CO2_conv'][-1]*100:>11.1f}%"
              f"{prof['H2_CO'][-1]:>10.2f}")

    print()
    print("=" * 70)
    print("STEADY-STATE CARBON COVERAGE (from microkinetic model)")
    print("=" * 70)
    print(f"\n{'Catalyst':<12}{'theta_C + theta_CH':>22}{'Status':>15}")
    print("-" * 55)
    for c in cats:
        cov = ACTUAL_CARBON_COVERAGE[c]
        status = "SAFE" if cov < 1e-2 else "COKING"
        print(f"{c:<12}{cov:>22.3e}{status:>15}")


if __name__ == "__main__":
    plot_feed_ratio()