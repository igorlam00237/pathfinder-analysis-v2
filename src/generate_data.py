"""
generate_data.py
----------------
Génère un dataset CSV simulant une mission d'inspection Pathfinder.
Les données reproduisent fidèlement la structure réelle des capteurs embarqués :
  - Capteur ultrason (épaisseur de paroi, corrosion)
  - GPS / encodeur odométrique (position)
  - Sondes physiques (température, pression)

Usage :
    python src/generate_data.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# ── Paramètres de simulation ──────────────────────────────────────────────────
SEED              = 42
N_POINTS          = 120          # Nombre de points de mesure
NOMINAL_THICKNESS = 8.5          # mm — épaisseur nominale acier DN200
MISSION_LENGTH_M  = 487          # mètres inspectés
BASE_TIME         = datetime(2024, 10, 14, 8, 30, 0)
SAMPLING_INTERVAL = 8            # secondes entre chaque mesure

# Zones de dégradation simulées (début_m, fin_m, perte_min_mm, perte_max_mm)
DEGRADED_ZONES = [
    (110, 150, 0.4, 1.1),   # Zone 1 : dégradation légère
    (290, 360, 1.8, 3.5),   # Zone 2 : dégradation sévère (zone critique)
]

OUTPUT_PATH = Path("data/mission_sample.csv")


def generate_mission_data() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)

    # Temps et position
    timestamps = [BASE_TIME + timedelta(seconds=i * SAMPLING_INTERVAL) for i in range(N_POINTS)]
    positions  = np.round(np.linspace(0, MISSION_LENGTH_M, N_POINTS), 1)

    # Épaisseur de paroi (bruit gaussien autour du nominal)
    thickness = rng.normal(loc=NOMINAL_THICKNESS, scale=0.15, size=N_POINTS)

    # Injection des zones dégradées
    for start_m, end_m, loss_min, loss_max in DEGRADED_ZONES:
        mask = (positions >= start_m) & (positions <= end_m)
        thickness[mask] -= rng.uniform(loss_min, loss_max, mask.sum())

    thickness = np.round(np.clip(thickness, 3.0, 10.5), 2)

    # Variables corrélées physiquement
    corrosion  = np.round(np.clip(
        (NOMINAL_THICKNESS - thickness) / NOMINAL_THICKNESS * 100 + rng.normal(0, 1.2, N_POINTS),
        0, 100), 1)
    signal_us  = np.round(np.clip(75 - corrosion * 0.35 + rng.normal(0, 1.5, N_POINTS), 45, 82), 1)
    confidence = np.round(np.clip(98 - corrosion * 0.30 + rng.normal(0, 2.0, N_POINTS), 60, 99), 1)

    # Variables physiques indépendantes
    temp_eau  = np.round(rng.normal(12.4, 0.3, N_POINTS), 1)
    pressure  = np.round(rng.normal(3.2, 0.05, N_POINTS), 2)
    speed     = np.round(rng.uniform(4.7, 5.3, N_POINTS), 1)

    # Coordonnées GPS (réseau fictif Dunkerque)
    x_gps = np.round(2.589412 + np.linspace(0, 0.0022, N_POINTS) + rng.normal(0, 2e-6, N_POINTS), 6)
    y_gps = np.round(51.034567 + np.linspace(0, 0.0011, N_POINTS) + rng.normal(0, 2e-6, N_POINTS), 6)

    frame_ids = [f"FRM-{i+1:04d}" for i in range(N_POINTS)]

    df = pd.DataFrame({
        "timestamp":     [t.strftime("%Y-%m-%d %H:%M:%S") for t in timestamps],
        "position_m":    positions,
        "x_gps":         x_gps,
        "y_gps":         y_gps,
        "epaisseur_mm":  thickness,
        "corrosion_pct": corrosion,
        "signal_us_db":  signal_us,
        "confiance_pct": confidence,
        "temp_eau_c":    temp_eau,
        "pression_bar":  pressure,
        "vitesse_cmps":  speed,
        "frame_id":      frame_ids,
    })

    return df


if __name__ == "__main__":
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = generate_mission_data()
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"✔ Dataset généré : {len(df)} lignes → {OUTPUT_PATH}")
