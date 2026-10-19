"""
Uncertainty Quantification on DFT-derived Kinetics
====================================================
Runs the DRM solver 30 times for each catalyst, perturbing every barrier
by a random amount drawn from N(0, sigma) where sigma = 0.1 eV (typical DFT error).

Reports mean TOF and 95% confidence intervals.
"""

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
import sys, os, warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import microkinetics as mk
from mechanism import CATALYSTS, ELEMENTARY_STEPS


SIGMA_DFT = 0.10   # eV, typical DFT error
N_SAMPLES = 30


def solve_once(catalyst_name, barrier_perturbations, T=900.0, P_total=1.0):
    """Solve with given per-step barrier perturbations."""
    cat = CATALYSTS[catalyst_name]
    dE_CH4, dE_C, dE_O = cat["dE_CH4"], cat["dE_C"], cat["dE_O"]

    P_dict = {
        "CH4_g": P_total * 0.45, "CO2_g": P_total * 0.45,
        "CO_g": 0.0, "H2_g": 0.0, "H2O_g": 0.0,
    }

    # Compute base rate constants
    k_fwd, k_rev = mk.compute_rate_constants(T, P_dict, dE_CH4, dE_C, dE_O)

    # Apply perturbations to each step
    for step in ELEMENTARY_STEPS:
        name = step["name"]
        if name in barrier_perturbations:
            dEa = barrier_perturbations[name]
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

    # TOF: CH4 dissociative adsorption net rate
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


def uncertainty_analysis(catalyst_name, n_samples=N_SAMPLES, seed=42):
    """Run the solver n_samples times with random barrier perturbations."""
    rng = np.random.default_rng(seed)
    tofs = []

    for _ in range(n_samples):
        perturbations = {step["name"]: rng.normal(0, SIGMA_DFT)
                         for step in ELEMENTARY_STEPS}
        try:
            tof = solve_once(catalyst_name, perturbations)
            if tof > 0 and np.isfinite(tof):
                tofs.append(tof)
        except Exception:
            continue

    tofs = np.array(tofs)
    if len(tofs) == 0:
        return None

    return {
        "mean": np.mean(tofs),
        "std": np.std(tofs),
        "p5": np.percentile(tofs, 5),
        "p95": np.percentile(tofs, 95),
        "samples": tofs,
    }


def main():
    print("=" * 70)
    print("UNCERTAINTY QUANTIFICATION OF DRM TOF PREDICTIONS")
    print("=" * 70)
    print()
    print(f"Method: {N_SAMPLES} Monte Carlo samples, sigma = {SIGMA_DFT} eV on every barrier")
    print()

    catalysts = list(CATALYSTS.keys())
    results = {}

    for cat in catalysts:
        print(f"Running {cat}...")
        results[cat] = uncertainty_analysis(cat)

    # Summary table
    print()
    print("=" * 70)
    print("TOF WITH 95% CONFIDENCE INTERVALS")
    print("=" * 70)
    print(f"\n{'Catalyst':<12}{'Mean TOF':>14}{'Std':>10}{'95% CI':>22}")
    print("-" * 60)

    for cat in catalysts:
        r = results[cat]
        if r is None:
            print(f"{cat:<12}{'N/A':>14}")
            continue
        ci = f"[{r['p5']:.2e}, {r['p95']:.2e}]"
        print(f"{cat:<12}{r['mean']:>14.3e}{r['std']:>10.3e}{ci:>22}")

    # Figure: TOF distribution for 3 representative catalysts
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # Panel 1: Box plots of TOF distribution
    ax = axes[0]
    data = [results[c]["samples"] for c in catalysts if results[c] is not None]
    names = [c for c in catalysts if results[c] is not None]
    colors = [CATALYSTS[c]["color"] for c in names]
    
    bp = ax.boxplot(data, tick_labels=names, patch_artist=True, showfliers=True)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.set_ylabel("TOF (s$^{-1}$)", fontsize=12)
    ax.set_title("TOF Distribution with $\\sigma_{DFT}$ = 0.10 eV",
                 fontsize=13, fontweight="bold")
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3, which="both")
    plt.setp(ax.get_xticklabels(), rotation=20)

    # Panel 2: Error bar plot (mean with 90% CI)
    ax = axes[1]
    y_pos = np.arange(len(names))
    means = [results[c]["mean"] for c in names]
    p5s = [results[c]["p5"] for c in names]
    p95s = [results[c]["p95"] for c in names]
    lower = [m - l for m, l in zip(means, p5s)]
    upper = [u - m for m, u in zip(means, p95s)]

    ax.errorbar(means, y_pos, xerr=[lower, upper], fmt="o",
                color="black", ecolor="#888888", capsize=5, markersize=8)
    for i, c in enumerate(names):
        ax.scatter(means[i], y_pos[i], s=120,
                   c=CATALYSTS[c]["color"], edgecolors="black",
                   linewidths=1.5, zorder=10)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=11)
    ax.set_xlabel("TOF (s$^{-1}$)", fontsize=12)
    ax.set_title("Mean TOF with 90% Confidence Interval",
                 fontsize=13, fontweight="bold")
    ax.set_xscale("log")
    ax.grid(True, alpha=0.3, which="both")

    plt.suptitle("Uncertainty Quantification of Predicted DRM Activity",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    os.makedirs("results/figures", exist_ok=True)
    plt.savefig("results/figures/uncertainty.png", dpi=200, bbox_inches="tight")
    plt.close()
    print(f"\nOK Saved: results/figures/uncertainty.png")

    # Save summary
    import csv
    with open("results/uncertainty_table.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Catalyst", "Mean_TOF", "Std", "p5", "p95"])
        for cat in catalysts:
            r = results[cat]
            if r is None:
                continue
            writer.writerow([cat, r["mean"], r["std"], r["p5"], r["p95"]])
    print(f"OK Saved: results/uncertainty_table.csv")


if __name__ == "__main__":
    main()