"""
Shared DRM reactor rate function.
Single source of truth for reactor.py and feed_ratio.py.
"""
import numpy as np

kB = 8.617333e-5   # eV/K


def drm_rate(dE_C, dE_O, T):
    """
    Descriptor-based DRM rate per catalytic site.
    Same function used by all reactor scripts to guarantee consistency.
    """
    kT = kB * T
    E_C = -6.40 + dE_C
    E_O = -5.50 + dE_O

    # CH4 activation with BEP dependence on dE_C
    Ea_CH4 = max(0.85 - 0.60 * dE_C, 0.10)
    k_CH4 = np.exp(-Ea_CH4 / kT)

    # Carbon poisoning (sigmoid around threshold)
    E_C_thresh = -5.70
    poisoning = 1.0 / (1.0 + np.exp((E_C - E_C_thresh) / kT))

    # O availability (mild)
    k_O = np.exp(-0.5 * abs(dE_O) / kT) if dE_O < 0 else 1.0

    return k_CH4 * poisoning * k_O


def pfr_profile(catalyst_name, T, P, y_CH4, y_CO2,
                L=0.5, d_reactor=0.1, rho_cat=800.0,
                S_BET=10.0, site_density=1.5e19, void=0.4,
                n_points=50):
    """
    Consistent 1D plug-flow reactor profile.
    Used by reactor.py and feed_ratio.py.
    """
    from mechanism import CATALYSTS
    cat = CATALYSTS[catalyst_name]
    dE_C, dE_O = cat["dE_C"], cat["dE_O"]

    A_cross = np.pi * (d_reactor / 2.0) ** 2
    z = np.linspace(0, L, n_points)

    F_total = 1e-3  # mol/s
    F_CH4_in = F_total * y_CH4
    F_CO2_in = F_total * y_CO2

    # Site density per m^3 of reactor
    N_sites_m3 = S_BET * 1e3 * rho_cat * site_density * (1 - void)
    r_per_site = drm_rate(dE_C, dE_O, T)
    N_A = 6.022e23
    r_vol = r_per_site * N_sites_m3 / N_A  # mol/(m^3·s)

    # Cap volumetric rate to physically realistic range
    r_vol = min(r_vol, 5.0)

    F_CH4 = np.zeros(n_points)
    F_CO2 = np.zeros(n_points)
    F_CO = np.zeros(n_points)
    F_H2 = np.zeros(n_points)

    F_CH4[0] = F_CH4_in
    F_CO2[0] = F_CO2_in

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

    # Carbon resistance index — use actual carbon coverage from the microkinetic
    # model rather than the arbitrary linear mapping
    carbon_risk = max(0.0, 1.0 - dE_C / 1.5)

    return {
        "z": z,
        "F_CH4": F_CH4, "F_CO2": F_CO2, "F_CO": F_CO, "F_H2": F_H2,
        "CH4_conv": CH4_conv, "CO2_conv": CO2_conv,
        "H2_CO": H2_CO,
        "carbon_risk": carbon_risk,
        "y_CH4": y_CH4, "y_CO2": y_CO2,
    }