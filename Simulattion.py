import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.title("Simulation de voyage ski - Suisse Janvier 2026")

# =========================
# Onglets pour paramètres
# =========================
tab1, tab2, tab3 = st.tabs(["Risques de base", "Risques personnels", "Sévérité personnelle"])

with tab1:
    st.header("Risques de base")
    N = st.number_input("Nombre de simulations (N)", min_value=10_000, max_value=1_000_000, value=500_000, step=10_000)
    trip_days = st.slider("Nombre de jours de ski", 1, 14, 3)
    p_transport_cancel = st.slider("Probabilité annulation transport", 0.0, 0.5, 0.02)
    p_transport_delay = st.slider("Probabilité retard transport", 0.0, 0.5, 0.15)
    p_no_snow = st.slider("Probabilité pas/neige insuffisante", 0.0, 0.5, 0.10)
    p_storm_block = st.slider("Probabilité tempête (blocage)", 0.0, 0.5, 0.05)
    p_sanitary_block = st.slider("Probabilité blocage sanitaire", 0.0, 0.5, 0.02)
    p_injury_per_day = st.slider("Probabilité blessure par jour", 0.0, 0.05, 0.001)

with tab2:
    st.header("Risques personnels (occurrence)")
    p_self_ill = st.slider("Maladie personnelle", 0.0, 0.2, 0.035)
    p_child_ill = st.slider("Maladie enfant", 0.0, 0.2, 0.025)
    p_work_block = st.slider("Blocage professionnel", 0.0, 0.2, 0.015)
    p_financial = st.slider("Problème financier", 0.0, 0.2, 0.015)

with tab3:
    st.header("Sévérité des événements personnels (annulation vs voyage impacté)")
    c_self_ill_cancel = st.slider("Maladie personnelle → annulation", 0.0, 1.0, 0.60)
    c_child_ill_cancel = st.slider("Maladie enfant → annulation", 0.0, 1.0, 0.70)
    c_work_block_cancel = st.slider("Blocage professionnel → annulation", 0.0, 1.0, 0.80)
    c_financial_cancel = st.slider("Problème financier → annulation", 0.0, 1.0, 0.90)

# =========================
# Simulation
# =========================
rng = np.random.default_rng()

# Événements de base
transport_cancel_mask = rng.random(N) < p_transport_cancel
sanitary_block_mask = rng.random(N) < p_sanitary_block
transport_delay_mask = rng.random(N) < p_transport_delay
no_snow_mask = rng.random(N) < p_no_snow
storm_mask = rng.random(N) < p_storm_block
injury_mask = rng.random(N) < (1 - (1 - p_injury_per_day) ** trip_days)

# Événements personnels
self_ill_mask = rng.random(N) < p_self_ill
self_ill_cancel_mask = self_ill_mask & (rng.random(N) < c_self_ill_cancel)
self_ill_mild_mask = self_ill_mask & ~self_ill_cancel_mask

child_ill_mask = rng.random(N) < p_child_ill
child_ill_cancel_mask = child_ill_mask & (rng.random(N) < c_child_ill_cancel)
child_ill_mild_mask = child_ill_mask & ~child_ill_cancel_mask

work_block_mask = rng.random(N) < p_work_block
work_block_cancel_mask = work_block_mask & (rng.random(N) < c_work_block_cancel)
work_block_mild_mask = work_block_mask & ~work_block_cancel_mask

financial_mask = rng.random(N) < p_financial
financial_cancel_mask = financial_mask & (rng.random(N) < c_financial_cancel)
financial_mild_mask = financial_mask & ~financial_cancel_mask

personal_cancel_mask = self_ill_cancel_mask | child_ill_cancel_mask | work_block_cancel_mask | financial_cancel_mask
personal_mild_mask = self_ill_mild_mask | child_ill_mild_mask | work_block_mild_mask | financial_mild_mask

# =========================
# Classement des issues avec priorité stricte
# =========================
outcomes = np.full(N, "Perfect trip", dtype=object)

# Priorité 1 : annulations totales
mask_cancelled = transport_cancel_mask | sanitary_block_mask | personal_cancel_mask
outcomes[mask_cancelled] = "Cancelled"

# Priorité 2 : disruption majeure
mask_major = (~mask_cancelled) & (storm_mask | no_snow_mask)
outcomes[mask_major] = "Major disruption (ski unavailable/limited)"

# Priorité 3 : blessure
mask_injury = (~mask_cancelled) & (~mask_major) & injury_mask
outcomes[mask_injury] = "Injury (medical attention needed)"

# Priorité 4 : problèmes personnels légers
mask_personal_mild = (~mask_cancelled) & (~mask_major) & (~mask_injury) & personal_mild_mask
outcomes[mask_personal_mild] = "Personal issue but travel proceeds (reduced enjoyment)"

# Priorité 5 : retards mineurs / perturbations
mask_disturbed = (~mask_cancelled) & (~mask_major) & (~mask_injury) & (~mask_personal_mild) & transport_delay_mask
outcomes[mask_disturbed] = "Disturbed (delay / minor inconvenience)"

# =========================
# Résumé et visualisation
# =========================
summary = pd.Series(outcomes).value_counts().rename_axis("outcome").reset_index(name="count")
summary["probability"] = summary["count"] / N
summary = summary.reset_index(drop=True)
summary["probability"] = pd.to_numeric(summary["probability"], errors="coerce")

st.subheader("Résultats de la simulation")
st.dataframe(summary)

st.subheader("Diagramme des probabilités")
# Remove rows with NaN or zero probability to avoid plotting errors
summary_plot = summary[summary["probability"].notna() & (summary["probability"] > 0)]
fig = px.pie(summary_plot, names="outcome", values="probability", title="Probabilités de chaque issue")
st.plotly_chart(fig)

