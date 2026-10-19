\# Multiscale Computational Study of Dry Reforming of Methane (DRM)



\## Overview

This repository contains a complete multiscale computational workflow for the design of carbon-resistant Dry Reforming of Methane (DRM) catalysts. The study progresses from Mean-Field Microkinetics to Kinetic Monte Carlo (kMC) simulations and Density Functional Theory (DFT) calculations.



\## Repository Structure

\- `src/`: Python source code for all simulations.

\- `docs/`: The final research paper (PDF/DOCX).

\- `results/`: Generated figures, plots, and data tables.



\## Methodology \& Advanced Extensions

1\. \*\*Mean-Field Microkinetics (14-step):\*\* Solved using stiff ODE integration (BDF) in `scipy.integrate.solve\_ivp`.

2\. \*\*Realistic Sticking Coefficients:\*\* Verified model robustness by applying realistic gas sticking probabilities.

3\. \*\*Virtual Promoter Screening:\*\* Proved the +0.8 eV design rule required to push Ni catalysts below the coking threshold.

4\. \*\*Kinetic Monte Carlo (kMC):\*\* Performed 10,000-step simulations on a 20x20 lattice using `kmos` to visualize spatial site-blocking.

5\. \*\*Density Functional Theory (DFT):\*\* Independently validated the Pt(111) carbon binding energy using `GPAW` (-7.076 eV).



\## Requirements

\- Python 3.10+

\- Libraries: `numpy`, `scipy`, `matplotlib`, `ase`, `gpaw`, `kmos`

