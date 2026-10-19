"""
Degree of Rate Control (DRC) Analysis
======================================
Campbell's DRC: DRC_i = d(ln TOF) / d(ln k_i)

Computed by perturbing each elementary step's rate constant by a factor
exp(-dEa/kBT), re-solving the full steady state, and measuring the change
in TOF. This identifies the rate-determining step (RDS) on each catalyst.

Reference: Campbell, C. T. ACS Catal. 2017, 7, 2770-2779.
"""

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
import sys, os, warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import microkinetics as mk
from mechanism import CATALYSTS, ELEMENTARY_STEPS


# ============================================================
# SOLVE WITH PERTURBED RATE CONSTANTS
# ============================================================

def solve_with_perturbation(catalyst_name, perturb_step=None, dEa=0.05,
                             T=900.0, P_total=1.0):
    """
    Solve steady state, optionally with the rate constants of one step
    scaled by exp(-dEa / kBT) to mimic raising its barrier.
    """
    cat = CATALYSTS[catalyst_name]
    dE_CH4, dE_C, dE_O = cat["dE_CH4"], cat["dE_C"], cat["dE_O"]

    P_dict = {
        "CH4_g": P_total * 0.45,
        "CO2_g": P_total * 0.45,
        "CO_g": 0.0,
        "H2_g": 0.0,
        "H2O_g": 0.0,
    }

    k_fwd, k_rev = mk.compute_rate_constants(T, P_dict, dE_CH4, dE_C, dE_O)

    if perturb_step is not None:
        factor = np.exp(-dEa / (mk.kB * T))
        k_fwd[perturb_step] *= factor
        k_rev[perturb_step] *= factor

    theta0 = np.ones(mk.N - 1) * 1e-6
    sol = solve_ivp(
        mk.rhs, t_span=(0, 1e6), y0=theta0,
        args=(k_fwd, k_rev),
        method="BDF", rtol=1e-7, atol=1e-11, max_step=1e5,
    )

    theta_final = np.clip(sol.y[:, -1], 0.0, 1.0)
    occupied = np.sum(theta_final)
    if occupied > 1.0:
        theta_final = theta_final / occupied * 0.99
    theta = np.zeros(mk.N)
    theta[1:] = theta_final
    theta[0] = max(1.0 - np.sum(theta_final), 0.0)

    # Compute TOF for CH4 conversion
    rates = {}
    for step in ELEMENTARY_STEPS:
        name = step["name"]
        Qf, Qr = 1.0, 1.0
        for sp, st in step["reactants"].items():
            if sp.endswith("_g"):
                continue
            Qf *= max(theta[mk.SP[sp]], 1e-30) ** st
        for sp, st in step["products"].items():
            if sp.endswith("_g"):
                continue
            Qr *= max(theta[mk.SP[sp]], 1e-30) ** st
        rates[name] = k_fwd[name] * Qf - k_rev[name] * Qr

    return rates["CH4_dissociative_adsorption"]


# ============================================================
# DRC
# ============================================================

def compute_drc(catalyst_name, dEa=0.05, T=900.0):
    """
    Compute the Degree of Rate Control for every elementary step.
    """
    tof_base = solve_with_perturbation(catalyst_name, None, 0, T)

    if abs(tof_base) < 1e-40:
        return {step["name"]: 0.0 for step in ELEMENTARY_STEPS}, tof_base

    ln_tof_base = np.log(abs(tof_base))
    kT_factor = dEa / (mk.kB * T)

    drc = {}
    for step in ELEMENTARY_STEPS:
        name = step["name"]
        tof_perturbed = solve_with_perturbation(catalyst_name, name, dEa, T)

        if abs(tof_perturbed) < 1e-40:
            drc[name] = 0.0
        else:
            ln_tof_new = np.log(abs(tof_perturbed))
            # dEa raises barrier -> k decreases by exp(-dEa/kT)
            # DRC = d ln(TOF) / d ln(k) = (ln TOF_new - ln TOF_old) / (-kT_factor)
            drc[name] = (ln_tof_new - ln_tof_base) / (-kT_factor)

    return drc, tof_base


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("DEGREE OF RATE CONTROL ANALYSIS (Campbell 2017)")
    print("=" * 70)
    print()
    print("Method: perturb each step's barrier by +0.05 eV, re-solve")
    print("        steady state, measure change in ln(TOF).")
    print()

    catalysts = ["Ni(111)", "Co(0001)", "Ru(0001)", "Rh(111)", "Pt(111)", "Ir(111)"]
    results = {}

    for cat in catalysts:
        print(f"Computing DRC for {cat}...")
        drc, tof = compute_drc(cat)
        results[cat] = {"drc": drc, "tof": tof}

    print()
    print("=" * 70)
    print("DRC SUMMARY — Top step for each catalyst")
    print("=" * 70)
    print(f"\n{'Catalyst':<12}{'RDS':<35}{'DRC':>12}")
    print("-" * 60)

    for cat in catalysts:
        drc = results[cat]["drc"]
        rds = max(drc.items(), key=lambda x: abs(x[1]))
        print(f"{cat:<12}{rds[0]:<35}{rds[1]:>12.4f}")

    # ---- Figure: DRC bar charts for 3 representative catalysts ----
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    steps = [step["name"] for step in ELEMENTARY_STEPS]
    y_pos = np.arange(len(steps))

    for ax, cat in zip(axes, ["Ni(111)", "Rh(111)", "Pt(111)"]):
        drc = results[cat]["drc"]
        values = [drc[s] for s in steps]
        colors = ["#D62246" if abs(v) > 0.3 else "#2E86AB" for v in values]

        ax.barh(y_pos, values, color=colors, edgecolor="black", linewidth=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(steps, fontsize=9)
        ax.invert_yaxis()
        ax.axvline(0, color="black", linewidth=0.8)
        ax.axvline(0.3, color="red", linestyle="--", linewidth=1, alpha=0.6)
        ax.axvline(-0.3, color="red", linestyle="--", linewidth=1, alpha=0.6)
        ax.set_xlabel("Degree of Rate Control", fontsize=11)
        ax.set_title(f"{cat}\n(TOF = {results[cat]['tof']:.2e} s$^{{-1}}$)",
                     fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="x")

    plt.suptitle("Degree of Rate Control Analysis — DRM on Transition Metals",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    os.makedirs("results/figures", exist_ok=True)
    plt.savefig("results/figures/drc.png", dpi=200, bbox_inches="tight")
    plt.close()
    print(f"\nOK Saved: results/figures/drc.png")

    # ---- Full DRC table saved as CSV ----
    import csv
    with open("results/drc_table.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Step"] + catalysts)
        for step in steps:
            row = [step] + [f"{results[cat]['drc'][step]:.4f}" for cat in catalysts]
            writer.writerow(row)

    print(f"OK Saved: results/drc_table.csv")

    print()
    print("=" * 70)
    print("Interpretation:")
    print("  - DRC near 1.0 → step is rate-determining")
    print("  - DRC near 0.0 → step is at quasi-equilibrium")
    print("  - Negative DRC  → increasing barrier accelerates net rate")
    print("  - The sum of all DRC values equals 1.0 for a valid microkinetic model")
    print("=" * 70)

    # Verify Campbell's theorem
    print("\nVerification (Campbell's theorem: sum of DRC = 1):")
    for cat in catalysts:
        s = sum(results[cat]["drc"].values())
        print(f"  {cat:<12} sum = {s:.4f}")