"""
Génère les graphiques et le rapport HTML pour la mission Pathfinder.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings
import base64
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3, "grid.linestyle": "--",
    "figure.facecolor": "white",
})

MISSION_ID = "MSN-2024-DKK-007"
RESEAU = "Dunkerque — Zone Nord"
OPERATEUR = "SUEZ / Agence de l'eau Artois-Picardie"
NOMINAL_THICKNESS = 8.5
Z_SCORE_THRESHOLD = 2.0
SEUIL_FAIBLE, SEUIL_MODERE, SEUIL_CRITIQUE = 5, 15, 30
COLORS = {
    "ok": "#2ECC71", "faible": "#F39C12", "modere": "#E67E22",
    "critique": "#E74C3C", "blue": "#1A3557", "lightblue": "#D6E4F0", "gray": "#7F8C8D",
}
SEV_COLOR_MAP = {"OK": COLORS["ok"], "FAIBLE": COLORS["faible"], "MODÉRÉ": COLORS["modere"], "CRITIQUE": COLORS["critique"]}
RECO = {
    "OK": "Aucune action requise",
    "FAIBLE": "Surveillance — ré-inspection dans 6 mois",
    "MODÉRÉ": "Inspection complémentaire — planifier réhabilitation",
    "CRITIQUE": "Intervention urgente — risque de rupture structurelle",
}
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Chargement & enrichissement ───────────────────────────────────────────────
df = pd.read_csv("data/mission_sample.csv", parse_dates=["timestamp"])
df["delta_epaisseur_mm"] = np.round(df["epaisseur_mm"] - NOMINAL_THICKNESS, 2)
df["perte_pct"] = np.round((NOMINAL_THICKNESS - df["epaisseur_mm"]) / NOMINAL_THICKNESS * 100, 1)
df["z_score_epaisseur"] = np.round((df["epaisseur_mm"] - df["epaisseur_mm"].mean()) / df["epaisseur_mm"].std(), 2)
df["anomalie"] = ((df["z_score_epaisseur"] < -Z_SCORE_THRESHOLD) | (df["perte_pct"] >= SEUIL_FAIBLE)).astype(int)

def classify(row):
    if row["anomalie"] == 0: return "OK"
    p = row["perte_pct"]
    return "CRITIQUE" if p >= SEUIL_CRITIQUE else ("MODÉRÉ" if p >= SEUIL_MODERE else "FAIBLE")

df["gravite"] = df.apply(classify, axis=1)
df["recommandation"] = df["gravite"].map(RECO)

n_anom = df["anomalie"].sum()
taux_anom = round(n_anom / len(df) * 100, 1)
sev_counts_dict = df["gravite"].value_counts().to_dict()

# ── Graphiques ────────────────────────────────────────────────────────────────
# Chart 1 : Profil
fig, axes = plt.subplots(3, 1, figsize=(15, 11), sharex=True)
fig.suptitle(f"Profil d'inspection — {RESEAU}\nMission {MISSION_ID}",
             fontsize=14, fontweight="bold", color=COLORS["blue"], y=0.99)

ax = axes[0]
ax.plot(df["position_m"], df["epaisseur_mm"], color=COLORS["blue"], linewidth=1.2, alpha=0.65, label="Épaisseur mesurée")
ax.axhline(NOMINAL_THICKNESS, color="black", linestyle="--", linewidth=1.0, alpha=0.6, label=f"Nominale ({NOMINAL_THICKNESS} mm)")
ax.axhline(NOMINAL_THICKNESS * (1 - SEUIL_CRITIQUE / 100), color=COLORS["critique"], linestyle=":", linewidth=1.4, label="Seuil CRITIQUE")
for sev, color in SEV_COLOR_MAP.items():
    mask = (df["gravite"] == sev) & (df["anomalie"] == 1)
    if mask.any():
        ax.scatter(df[mask]["position_m"], df[mask]["epaisseur_mm"],
                   color=color, s=45, zorder=5, edgecolors="white", linewidths=0.6, label=f"Anomalie — {sev}")
ax.set_ylabel("Épaisseur (mm)", fontsize=10); ax.legend(fontsize=8, loc="lower left", ncol=2); ax.set_ylim(3.0, 10.5)

ax2 = axes[1]
ax2.fill_between(df["position_m"], df["corrosion_pct"], alpha=0.35, color=COLORS["modere"])
ax2.plot(df["position_m"], df["corrosion_pct"], color=COLORS["modere"], linewidth=1.1)
ax2.axhline(SEUIL_CRITIQUE, color=COLORS["critique"], linestyle=":", linewidth=1.4, label=f"Seuil CRITIQUE ({SEUIL_CRITIQUE}%)")
ax2.set_ylabel("Corrosion (%)", fontsize=10); ax2.legend(fontsize=8)

ax3 = axes[2]
ax3.plot(df["position_m"], df["signal_us_db"], color=COLORS["gray"], linewidth=1.0)
ax3.fill_between(df["position_m"], df["signal_us_db"], alpha=0.15, color=COLORS["gray"])
ax3.set_ylabel("Signal US (dB)", fontsize=10); ax3.set_xlabel("Position curviligne (m)", fontsize=10)
plt.tight_layout(rect=[0, 0, 1, 0.97])
fig.savefig(OUTPUT_DIR / "chart_profil_inspection.png", dpi=150, bbox_inches="tight"); plt.close()

# Chart 2 : Stats
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("Analyse statistique des défauts", fontsize=13, fontweight="bold", color=COLORS["blue"])
ax = axes[0]
sev_order = [s for s in ["OK", "FAIBLE", "MODÉRÉ", "CRITIQUE"] if s in df["gravite"].values]
wedges, texts, autotexts = ax.pie(
    [df["gravite"].value_counts()[s] for s in sev_order],
    labels=sev_order, colors=[SEV_COLOR_MAP[s] for s in sev_order],
    autopct="%1.1f%%", startangle=90,
    wedgeprops={"edgecolor": "white", "linewidth": 2}, textprops={"fontsize": 11},
)
[at.set_fontweight("bold") for at in autotexts]
ax.set_title("Répartition des points par gravité", fontsize=11, pad=12)
ax2 = axes[1]
ax2.hist(df["epaisseur_mm"], bins=25, color=COLORS["lightblue"], edgecolor=COLORS["blue"], linewidth=0.5, alpha=0.9)
ax2.axvline(NOMINAL_THICKNESS, color="black", linestyle="--", linewidth=1.8, label=f"Nominale ({NOMINAL_THICKNESS} mm)")
ax2.axvline(NOMINAL_THICKNESS * (1 - SEUIL_CRITIQUE / 100), color=COLORS["critique"], linestyle=":", linewidth=1.5, label="Seuil CRITIQUE")
ax2.set_xlabel("Épaisseur (mm)", fontsize=10); ax2.set_ylabel("Nombre de points", fontsize=10)
ax2.set_title("Distribution épaisseur", fontsize=11, pad=12); ax2.legend(fontsize=8)
plt.tight_layout(); fig.savefig(OUTPUT_DIR / "chart_statistiques.png", dpi=150, bbox_inches="tight"); plt.close()

# Chart 3 : Carto
fig, ax = plt.subplots(figsize=(15, 3.5))
ax.axhline(1, color=COLORS["gray"], linewidth=3, alpha=0.25, zorder=1)
ok_pts = df[df["gravite"] == "OK"]
ax.scatter(ok_pts["position_m"], [1] * len(ok_pts), c=COLORS["ok"], s=55, zorder=3, alpha=0.65, label="OK")
for sev in ["FAIBLE", "MODÉRÉ", "CRITIQUE"]:
    pts = df[df["gravite"] == sev]
    if not pts.empty:
        ax.scatter(pts["position_m"], [1] * len(pts), c=SEV_COLOR_MAP[sev], s=110, zorder=4,
                   edgecolors="white", linewidths=0.8, label=f"{sev} ({len(pts)} pts)")
ax.set_xlim(-5, df["position_m"].max() + 5); ax.set_ylim(0.5, 1.5); ax.set_yticks([])
ax.set_xlabel("Position curviligne (m)", fontsize=11)
ax.set_title(f"Cartographie des défauts — {n_anom} anomalies sur {len(df)} points ({taux_anom}% du tronçon)",
             fontsize=12, fontweight="bold", color=COLORS["blue"])
ax.legend(loc="upper right", fontsize=9, ncol=4)
plt.tight_layout(); fig.savefig(OUTPUT_DIR / "chart_cartographie.png", dpi=150, bbox_inches="tight"); plt.close()

print("✔ Graphiques générés")

# ── Rapport HTML ──────────────────────────────────────────────────────────────
def img_b64(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

def kpi(label, value, sub="", warn=False):
    cls = "kpi warn" if warn else "kpi"
    s = f'<div class="{cls}"><div class="kpi-val">{value}</div><div class="kpi-lbl">{label}</div>'
    if sub:
        s += f'<div class="kpi-sub">{sub}</div>'
    s += '</div>'
    return s

anomalies_df = (
    df[df["anomalie"] == 1][
        ["position_m", "epaisseur_mm", "delta_epaisseur_mm", "perte_pct",
         "corrosion_pct", "signal_us_db", "confiance_pct", "gravite", "recommandation"]
    ].sort_values("perte_pct", ascending=False).reset_index(drop=True)
)

sev_badge = {"OK": ("badge-ok", "OK"), "FAIBLE": ("badge-faible", "FAIBLE"),
             "MODÉRÉ": ("badge-modere", "MODÉRÉ"), "CRITIQUE": ("badge-critique", "CRITIQUE")}
rows_html = ""
for _, row in anomalies_df.iterrows():
    bc, bl = sev_badge.get(row["gravite"], ("", ""))
    rows_html += (
        f'<tr>'
        f'<td>{row["position_m"]} m</td>'
        f'<td>{row["epaisseur_mm"]} mm</td>'
        f'<td>{row["delta_epaisseur_mm"]:+.2f} mm</td>'
        f'<td>{row["perte_pct"]} %</td>'
        f'<td>{row["corrosion_pct"]} %</td>'
        f'<td>{row["signal_us_db"]} dB</td>'
        f'<td>{row["confiance_pct"]} %</td>'
        f'<td><span class="badge {bc}">{bl}</span></td>'
        f'<td>{row["recommandation"]}</td>'
        f'</tr>'
    )

stats = {
    "n_points": len(df),
    "longueur_m": round(df["position_m"].max(), 1),
    "thick_mean": round(df["epaisseur_mm"].mean(), 2),
    "thick_std": round(df["epaisseur_mm"].std(), 2),
    "thick_min": round(df["epaisseur_mm"].min(), 2),
    "corrosion_max": round(df["corrosion_pct"].max(), 1),
    "confiance_mean": round(df["confiance_pct"].mean(), 1),
}

n_critique = sev_counts_dict.get("CRITIQUE", 0)
alert_html = ""
if n_critique > 0:
    alert_html = (
        f'<div class="section">'
        f'<div class="alert">&#9888;&#65039; <strong>ALERTE : {n_critique} point(s) CRITIQUE(S) '
        f'détecté(s)</strong> — Intervention urgente requise. Risque de rupture structurelle identifié.</div>'
        f'</div>'
    )

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Rapport — {MISSION_ID}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:"Segoe UI",Arial,sans-serif;background:#f0f4f8;color:#2c3e50}}
.header{{background:linear-gradient(135deg,#1A3557 0%,#2E6DA4 100%);color:white;padding:32px 48px}}
.header h1{{font-size:22px;font-weight:700;margin-bottom:6px}}
.header .meta{{font-size:12px;opacity:.85;margin-top:10px;display:flex;flex-wrap:wrap;gap:20px}}
.header .meta span::before{{content:"• ";opacity:.6}}
.container{{max-width:1200px;margin:32px auto;padding:0 24px}}
.section{{background:white;border-radius:10px;padding:28px 32px;margin-bottom:24px;box-shadow:0 2px 8px rgba(0,0,0,.07)}}
.section h2{{font-size:13px;color:#1A3557;font-weight:700;border-bottom:3px solid #1A3557;padding-bottom:10px;margin-bottom:20px;text-transform:uppercase;letter-spacing:.8px}}
.kpis{{display:flex;gap:14px;flex-wrap:wrap}}
.kpi{{background:#f8fbff;border:1px solid #D6E4F0;border-radius:8px;padding:18px 20px;text-align:center;flex:1;min-width:110px}}
.kpi-val{{font-size:26px;font-weight:700;color:#1A3557}}
.kpi-lbl{{font-size:10px;color:#7F8C8D;margin-top:4px;text-transform:uppercase}}
.kpi-sub{{font-size:10px;color:#95A5A6;margin-top:2px}}
.kpi.warn .kpi-val{{color:#E74C3C}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:#1A3557;color:white;padding:10px 12px;text-align:left;font-weight:600;font-size:11px}}
td{{padding:9px 12px;border-bottom:1px solid #ECF0F1;vertical-align:middle}}
tr:hover td{{background:#f8fbff}}
.badge{{display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700}}
.badge-ok{{background:#E8F5E9;color:#27AE60}}
.badge-faible{{background:#FEF3E2;color:#E67E22}}
.badge-modere{{background:#FFF3CD;color:#D35400}}
.badge-critique{{background:#FDDEDE;color:#C0392B}}
.chart-img{{width:100%;border-radius:6px;margin-top:4px}}
.alert{{background:#FDDEDE;border-left:4px solid #E74C3C;padding:14px 18px;border-radius:6px;font-size:14px}}
.alert strong{{color:#C0392B}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.footer{{text-align:center;color:#95A5A6;font-size:12px;padding:24px}}
@media(max-width:768px){{.two-col{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="header">
  <h1>&#128203; Rapport d'analyse d'inspection — {RESEAU}</h1>
  <div class="meta">
    <span>Robot : Pathfinder-01</span>
    <span>Date : 14 octobre 2024</span>
    <span>Mission : {MISSION_ID}</span>
    <span>Opérateur : {OPERATEUR}</span>
    <span>Généré le : {datetime.now().strftime("%d/%m/%Y à %H:%M")}</span>
  </div>
</div>
<div class="container">
  <div class="section">
    <h2>Indicateurs clés de mission</h2>
    <div class="kpis">
      {kpi("Points analysés", stats["n_points"])}
      {kpi("Longueur inspectée", f"{stats['longueur_m']} m")}
      {kpi("Épaisseur moyenne", f"{stats['thick_mean']} mm", f"σ = {stats['thick_std']} mm")}
      {kpi("Épaisseur minimale", f"{stats['thick_min']} mm")}
      {kpi("Anomalies détectées", n_anom, f"{taux_anom}% du tronçon", warn=True)}
      {kpi("Corrosion max.", f"{stats['corrosion_max']} %")}
      {kpi("Confiance moy.", f"{stats['confiance_mean']} %")}
    </div>
  </div>
  {alert_html}
  <div class="section">
    <h2>Profil d'inspection le long du tronçon</h2>
    <img class="chart-img" src="{img_b64(OUTPUT_DIR / 'chart_profil_inspection.png')}" alt="Profil">
  </div>
  <div class="two-col">
    <div class="section">
      <h2>Analyse statistique</h2>
      <img class="chart-img" src="{img_b64(OUTPUT_DIR / 'chart_statistiques.png')}" alt="Stats">
    </div>
    <div class="section">
      <h2>Cartographie des défauts</h2>
      <img class="chart-img" src="{img_b64(OUTPUT_DIR / 'chart_cartographie.png')}" alt="Carto">
    </div>
  </div>
  <div class="section">
    <h2>Détail des anomalies détectées ({len(anomalies_df)} points)</h2>
    <table>
      <thead>
        <tr>
          <th>Position</th><th>Épaisseur</th><th>Delta Épaisseur</th>
          <th>Perte %</th><th>Corrosion %</th><th>Signal US</th>
          <th>Confiance</th><th>Gravité</th><th>Recommandation</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
</div>
<div class="footer">
  Rapport généré automatiquement par le pipeline d'analyse Pathfinder — Acwa Robotics | Igor LAMINSI
</div>
</body>
</html>"""

html_path = OUTPUT_DIR / f"rapport_{MISSION_ID}.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"✔ Rapport HTML → {html_path}")
