"""
Degree of Selectivity Control (DSC) Analysis
==============================================
Campbell-style sensitivity of the carbon-removal selectivity to each
elementary step barrier.

Selectivity defined as: S_CO = rate_CO_formation / (rate_CO + rate_C_accumulation)
Or more practically: S = TOF_CO / (TOF_CO + net_rate_CH_dehydrogenation)

DSC_i = d ln(S) / d ln(k_i)

Perturb each step by +0.05 eV, re-solve steady state, measure change in S.
"""

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
import sys, os, warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import microkinetics as mk
from mechanism import CATALYSTS, ELEMENTARY_STEPS


def compute_rates_and_selectivity(catalyst_name, barrier_perturbations=None,
                                   T=900.0, P_total=1.0):
    """Solve steady state and return CO selectivity + all rates."""
    cat = CATALYSTS[catalyst_name]
    dE_CH4, dE_C, dE_O = cat["dE_CH4"], cat["dE_C"], cat["dE_O"]

    P_dict = {
        "CH4_g": P_total * 0.45, "CO2_g": P_total * 0.45,
        "CO_g": 0.0, "H2_g": 0.0, "H2O_g": 0.0,
    }

    k_fwd, k_rev = mk.compute_rate_constants(T, P_dict, dE_CH4, dE_C, dE_O)

    if barrier_perturbations:
        for name, dEa in barrier_perturbations.items():
            factor = np.exp(-dEa / (mk.kB * T))
            k_fwd[name] *= factor
            k_rev[name] *= factor

    theta0 = np.ones(mk.N - 1) * 1e-6
    sol = solve_ivp(mk.rhs, t_span=(0, 1e6), y0=theta0,
                    args=(k_fwd, k_rev), method="BDF",
                    rtol=1e-6, atol=1e-10, max_step=1e5)

    theta_final = np.clip(sol.y[:, -1], 0.0, 1.0)
    occ = np.sum(theta_final)
    if occ > 1.0:
        theta_final = theta_final / occ * 0.99
    theta = np.zeros(mk.N)
    theta[1:] = theta_final
    theta[0] = max(1.0 - np.sum(theta_final), 0.0)

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

    # Selectivity: fraction of CHx that gets oxidized to CO vs decomposed to C
    # Rate of CH -> C (carbon formation):
    r_carbon = max(rates["CH_dehydrogenation"], 0.0)
    # Rate of CH -> CO (carbon removal via oxidation):
    r_co = max(rates["CH_oxidation"], 0.0) + max(rates["C_oxidation_by_O"], 0.0)

    S = r_co / (r_co + r_carbon + 1e-30)
    return S, rates


def compute_dsc(catalyst_name, dEa=0.05):
    """Compute DSC for all elementary steps."""
    S_base, _ = compute_rates_and_selectivity(catalyst_name)
    if S_base < 1e-10 or S_base > 1 - 1e-10:
        return {s["name"]: 0.0 for s in ELEMENTARY_STEPS}, S_base

    ln_S_base = np.log(S_base / (1 - S_base))  # logit transform
    kT_factor = dEa / (mk.kB * 900.0)

    dsc = {}
    for step in ELEMENTARY_STEPS:
        name = step["name"]
        perturbed = {name: dEa}
        S_new, _ = compute_rates_and_selectivity(catalyst_name, perturbed)
        if S_new < 1e-10 or S_new > 1 - 1e-10:
            dsc[name] = 0.0
        else:
            ln_S_new = np.log(S_new / (1 - S_new))
            dsc[name] = (ln_S_new - ln_S_base) / (-kT_factor)

    return dsc, S_base


def main():
    print("=" * 70)
    print("DEGREE OF SELECTIVITY CONTROL ANALYSIS")
    print("=" * 70)
    print()
    print("S_CO = rate(CO formation) / (rate(CO) + rate(carbon formation))")
    print("DSC_i = d ln(S/(1-S)) / d ln(k_i)")
    print()

    catalysts = list(CATALYSTS.keys())
    results = {}

    for cat in catalysts:
        print(f"Computing DSC for {cat}...")
        dsc, S = compute_dsc(cat)
        results[cat] = {"dsc": dsc, "S": S}

    # Summary
    print()
    print("=" * 70)
    print("SELECTIVITY AND TOP CONTROLLING STEPS")
    print("=" * 70)
    print(f"\n{'Catalyst':<12}{'S_CO':>10}{'Top controlling step':<35}{'DSC':>12}")
    print("-" * 69)

    for cat in catalysts:
        r = results[cat]
        top = max(r["dsc"].items(), key=lambda x: abs(x[1]))
        print(f"{cat:<12}{r['S']:>10.4f}{top[0]:<35}{top[1]:>12.4f}")

    # Figure: DSC bar chart for two key catalysts
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    for ax, cat in zip(axes, ["Ni(111)", "Pt(111)"]):
        steps = [s["name"] for s in ELEMENTARY_STEPS]
        values = [results[cat]["dsc"][s] for s in steps]
        y_pos = np.arange(len(steps))
        colors = ["#D62246" if abs(v) > 0.3 else "#2E86AB" for v in values]

        ax.barh(y_pos, values, color=colors, edgecolor="black", linewidth=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(steps, fontsize=9)
        ax.invert_yaxis()
        ax.axvline(0, color="black", linewidth=0.8)
        ax.axvline(0.3, color="red", linestyle="--", linewidth=1, alpha=0.6)
        ax.axvline(-0.3, color="red", linestyle="--", linewidth=1, alpha=0.6)
        ax.set_xlabel("Degree of Selectivity Control", fontsize=11)
        ax.set_title(f"{cat}\n$S_{{CO}}$ = {results[cat]['S']:.3f}",
                     fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="x")

    plt.suptitle("Degree of Selectivity Control Analysis",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    os.makedirs("results/figures", exist_ok=True)
    plt.savefig("results/figures/dsc.png", dpi=200, bbox_inches="tight")
    plt.close()
    print(f"\nOK Saved: results/figures/dsc.png")

    # CSV
    import csv
    with open("results/dsc_table.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Step"] + catalysts)
        for step in [s["name"] for s in ELEMENTARY_STEPS]:
            writer.writerow([step] + [f"{results[c]['dsc'][step]:.4f}"
                                       for c in catalysts])
    print(f"OK Saved: results/dsc_table.csv")

    print()
    print("=" * 70)
    print("Interpretation:")
    print("  - Large positive DSC → step strongly favors CO formation")
    print("  - Large negative DSC → step strongly favors carbon formation")
    print("  - Small DSC       → step has minimal effect on selectivity")
    print("=" * 70)


if __name__ == "__main__":
    main()