"""
Graphical Abstract for DRM Paper
==================================
Single composite figure summarizing the entire study:
reaction scheme + mechanism + volcano + ranking + design rule.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mechanism import CATALYSTS


def make_graphical_abstract(save_path="results/figures/graphical_abstract.png"):
    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.35,
                          left=0.05, right=0.95, top=0.92, bottom=0.05)

    # ============================================================
    # Top Left: Overall Reaction
    # ============================================================
    ax = fig.add_subplot(gs[0, 0])
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)

    ax.text(5, 9, "Overall Reaction", ha="center", fontsize=13,
            fontweight="bold", color="#1F3A6E")
    ax.text(5, 7.5, "CH$_4$ + CO$_2$", ha="center", fontsize=14,
            bbox=dict(boxstyle="round,pad=0.5", fc="#E8F4F8", ec="#2E86AB", lw=2))
    ax.annotate("", xy=(7, 5.2), xytext=(5, 6.7),
                arrowprops=dict(arrowstyle="->", lw=2, color="#2E86AB"))
    ax.text(7.3, 6.2, "catalyst", fontsize=10, style="italic", color="#666")
    ax.text(5, 4, "2 CO + 2 H$_2$", ha="center", fontsize=14,
            bbox=dict(boxstyle="round,pad=0.5", fc="#FFF4E5", ec="#F18F01", lw=2))
    ax.text(5, 2, "ΔH = +247 kJ/mol", ha="center", fontsize=10,
            color="#A23B72")
    ax.text(5, 0.5, "DRY REFORMING\nOF METHANE (DRM)", ha="center",
            fontsize=11, fontweight="bold", color="#1F3A6E")

    # ============================================================
    # Top Middle: 14-step mechanism summary
    # ============================================================
    ax = fig.add_subplot(gs[0, 1])
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)

    ax.text(5, 9.3, "14-Step Mechanism", ha="center", fontsize=13,
            fontweight="bold", color="#1F3A6E")
    ax.text(5, 8.3, "(Langmuir-Hinshelwood)", ha="center", fontsize=10,
            style="italic", color="#666")

    steps_text = [
        "1.  CH$_4$ → CH$_3$* + H*",
        "2.  CH$_3$* → CH$_2$* + H*",
        "3.  CH$_2$* → CH* + H*",
        "4.  CH* → C* + H*",
        "5.  CO$_2$ → CO$_2$*",
        "6.  CO$_2$* → CO* + O*",
        "7.  C* + O* → CO*  (gasif.)",
        "8.  C* + CO$_2$* → 2 CO*",
        "9-14.  H$_2$, H$_2$O paths",
    ]
    for i, s in enumerate(steps_text):
        ax.text(0.5, 7.3 - i * 0.82, s, fontsize=9.5, color="#333",
                family="monospace")

    # ============================================================
    # Top Right: Solver
    # ============================================================
    ax = fig.add_subplot(gs[0, 2])
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)

    ax.text(5, 9.3, "Numerical Solution", ha="center", fontsize=13,
            fontweight="bold", color="#1F3A6E")
    ax.text(5, 8.3, "d\u03b8$_i$/dt = \u03a3 \u03bd$_{ij}$ r$_j$", ha="center",
            fontsize=11, style="italic")

    # Big box for solver steps
    box = Rectangle((1.5, 1.5), 7, 6.3, fc="#F0F8FF", ec="#2E86AB", lw=2)
    ax.add_patch(box)

    ax.text(5, 6.8, "Steady-state solver", ha="center", fontsize=11,
            fontweight="bold", color="#2E86AB")
    solver_lines = [
        "• BDF stiff ODE integrator",
        "• scipy.integrate.solve_ivp",
        "• 10$^6$ s integration window",
        "• 14 coupled rate equations",
        "• Hertz-Knudsen adsorption",
        "• Arrhenius desorption",
        "• Step-specific prefactors",
    ]
    for i, line in enumerate(solver_lines):
        ax.text(2, 5.9 - i * 0.65, line, fontsize=9.5, color="#333")

    ax.text(5, 0.6, "Predicts:  θ$_C$, θ$_{CH}$, TOF, selectivity",
            ha="center", fontsize=10, fontweight="bold", color="#A23B72")

    # ============================================================
    # Bottom: Volcano plot (spanning all columns)
    # ============================================================
    ax = fig.add_subplot(gs[1, :])
    ax.set_xlim(-0.6, 2.0)
    ax.set_ylim(-1.0, 1.6)

    # Generate a schematic volcano
    dE_C_vals = np.linspace(-0.6, 2.0, 100)
    dE_O_vals = np.linspace(-1.0, 1.6, 100)
    XX, YY = np.meshgrid(dE_C_vals, dE_O_vals)
    # Synthetic activity landscape
    Z = -((XX - 0.73)**2) / 0.5 - (YY - 0.0)**2 / 2.0
    Z = np.exp(Z)

    cf = ax.contourf(XX, YY, Z, levels=20, cmap="viridis", alpha=0.8)
    ax.contour(XX, YY, Z, levels=[0.3, 0.5, 0.7, 0.9],
               colors="white", linewidths=1, alpha=0.6)

    # Catalyst markers
    for name, cat in CATALYSTS.items():
        ax.scatter(cat["dE_C"], cat["dE_O"], s=350, c="red",
                   edgecolors="black", linewidths=2, zorder=10)
        ax.annotate(name, (cat["dE_C"], cat["dE_O"]),
                    xytext=(15, 10), textcoords="offset points",
                    fontsize=11, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.4",
                              fc="white", ec="black", alpha=0.95),
                    zorder=11)

    # Volcano peak
    ax.scatter(0.73, 0.0, s=700, marker="*", c="gold",
               edgecolors="black", linewidths=2, zorder=12)

    ax.set_xlabel(r"$\Delta E_C$ (eV)  —  carbon binding shift vs Ni",
                  fontsize=13)
    ax.set_ylabel(r"$\Delta E_O$ (eV)", fontsize=13)
    ax.set_title("Sabatier Volcano — Optimal Carbon Binding at ΔE$_C$ = +0.73 eV",
                 fontsize=14, fontweight="bold", color="#1F3A6E")

    # Annotation box for main result
    ax.text(1.35, -0.75,
            "CARBON RESISTANCE RANKING:\n"
            "Ir > Pt > Rh > Ru > Co > Ni\n\n"
            "DESIGN RULE:\n"
            "ΔE$_C$ ≥ +0.8 eV (E$_C$ ≤ −5.6 eV)",
            fontsize=11, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.7", fc="#FFF4E5",
                      ec="#A23B72", lw=2),
            color="#1F3A6E")

    # Main title
    fig.suptitle("CatalystGPT for DRM: A Numerical Microkinetic Study",
                 fontsize=16, fontweight="bold", color="#1F3A6E", y=0.98)

    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches="tight",
                facecolor="white")
    plt.close()
    print(f"OK Saved: {save_path}")


if __name__ == "__main__":
    print("Generating graphical abstract...")
    make_graphical_abstract()
    print("Done.")