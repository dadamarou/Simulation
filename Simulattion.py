import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Simulation de voyage ski", layout="wide")
st.title("Simulation de l'escapade des guerriers - Suisse Janvier 2026")

# =========================
# Onglets pour paramètres
# =========================
tab1, tab2, tab3, tab4 = st.tabs(["Risques de base", "Risques personnels", "Sévérité personnelle", "Scénarios"])

# === Onglet Risques de base ===
with tab1:
    st.header("Risques de base")
    N = st.number_input("Nombre de simulations (N)", min_value=10000, max_value=1000000, value=500000, step=10000)
    trip_days = st.slider("Nombre de jours de ski", 1, 14, 3)
    p_transport_cancel = st.slider("Probabilité annulation transport (%)", 0.0, 50.0, 2.0)/100
    p_transport_delay = st.slider("Probabilité retard transport (%)", 0.0, 50.0, 15.0)/100
    p_no_snow = st.slider("Probabilité pas/neige insuffisante (%)", 0.0, 50.0, 10.0)/100
    p_storm_block = st.slider("Probabilité tempête (blocage) (%)", 0.0, 50.0, 5.0)/100
    p_sanitary_block = st.slider("Probabilité blocage sanitaire (%)", 0.0, 50.0, 2.0)/100
    p_injury_per_day = st.slider("Probabilité blessure par jour (%)", 0.0, 5.0, 0.1)/100

# === Onglet Risques personnels ===
with tab2:
    st.header("Risques personnels (occurrence)")
    p_self_ill = st.slider("Maladie personnelle (%)", 0.0, 20.0, 3.5)/100
    p_child_ill = st.slider("Maladie enfant (%)", 0.0, 20.0, 2.5)/100
    p_work_block = st.slider("Blocage professionnel (%)", 0.0, 20.0, 1.5)/100
    p_financial = st.slider("Problème financier (%)", 0.0, 20.0, 1.5)/100

# === Onglet Sévérité personnelle ===
with tab3:
    st.header("Sévérité des événements personnels (annulation vs voyage impacté)")
    c_self_ill_cancel = st.slider("Maladie personnelle → annulation (%)", 0.0, 100.0, 60.0)/100
    c_child_ill_cancel = st.slider("Maladie enfant → annulation (%)", 0.0, 100.0, 70.0)/100
    c_work_block_cancel = st.slider("Blocage professionnel → annulation (%)", 0.0, 100.0, 80.0)/100
    c_financial_cancel = st.slider("Problème financier → annulation (%)", 0.0, 100.0, 90.0)/100

# === Onglet Scénarios prédéfinis ===
with tab4:
    st.header("Scénarios prédéfinis")
    scenario = st.selectbox("Choisir un scénario", ["Réalisme", "Optimiste", "Pessimiste"])
    if scenario == "Optimiste":
        p_transport_cancel, p_transport_delay, p_no_snow, p_storm_block, p_sanitary_block = 0.01, 0.10, 0.05, 0.02, 0.01
        p_self_ill, p_child_ill, p_work_block, p_financial = 0.02, 0.01, 0.01, 0.01
    elif scenario == "Pessimiste":
        p_transport_cancel, p_transport_delay, p_no_snow, p_storm_block, p_sanitary_block = 0.05, 0.20, 0.20, 0.10, 0.05
        p_self_ill, p_child_ill, p_work_block, p_financial = 0.05, 0.03, 0.03, 0.03

# =========================
# Simulation
# =========================
rng = np.random.default_rng()

transport_cancel_mask = rng.random(N) < p_transport_cancel
sanitary_block_mask = rng.random(N) < p_sanitary_block
transport_delay_mask = rng.random(N) < p_transport_delay
no_snow_mask = rng.random(N) < p_no_snow
storm_mask = rng.random(N) < p_storm_block
injury_mask = rng.random(N) < (1 - (1 - p_injury_per_day) ** trip_days)

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
# Classement des issues
# =========================
outcomes = np.full(N, "Perfect trip", dtype=object)

mask_cancelled = transport_cancel_mask | sanitary_block_mask | personal_cancel_mask
outcomes[mask_cancelled] = "Cancelled"

mask_major = (~mask_cancelled) & (storm_mask | no_snow_mask)
outcomes[mask_major] = "Major disruption (ski unavailable/limited)"

mask_injury = (~mask_cancelled) & (~mask_major) & injury_mask
outcomes[mask_injury] = "Injury (medical attention needed)"

mask_personal_mild = (~mask_cancelled) & (~mask_major) & (~mask_injury) & personal_mild_mask
outcomes[mask_personal_mild] = "Personal issue but travel proceeds (reduced enjoyment)"

mask_disturbed = (~mask_cancelled) & (~mask_major) & (~mask_injury) & (~mask_personal_mild) & transport_delay_mask
outcomes[mask_disturbed] = "Disturbed (delay / minor inconvenience)"

# =========================
# Résumé et visualisation
# =========================
summary = pd.Series(outcomes).value_counts().rename_axis("outcome").reset_index(name="count")
summary["probability"] = summary["count"] / N

# Probabilité globale de voyage réussi
success_mask = (outcomes == "Perfect trip") | \
               (outcomes == "Personal issue but travel proceeds (reduced enjoyment)") | \
               (outcomes == "Disturbed (delay / minor inconvenience)")
success_rate = success_mask.sum() / N * 100
st.metric("Probabilité globale de voyage réussi", f"{success_rate:.2f} %")

# Tableau en pourcentages
summary_display = summary.copy()
summary_display["probability"] = (summary_display["probability"]*100).round(2).astype(str)+" %"
st.subheader("Résultats de la simulation")
st.dataframe(summary_display)

# Camembert
summary_plot = summary[summary["probability"]>0]
st.subheader("Diagramme des probabilités")
fig = px.pie(summary_plot, names="outcome", values="probability", title="Probabilités de chaque issue")
fig.update_traces(textinfo='percent+label')
st.plotly_chart(fig)

# Histogramme
st.subheader("Histogramme des issues")
fig_bar = px.bar(summary_plot, x="outcome", y="probability",
                 text=(summary_plot["probability"]*100).round(2).astype(str)+"%")
fig_bar.update_layout(yaxis_title="Probabilité")
st.plotly_chart(fig_bar)

# Export CSV
csv = summary.to_csv(index=False)
st.download_button("Télécharger les résultats CSV", data=csv, file_name="simulation_ski.csv", mime="text/csv")

# Résumé narratif
st.markdown(f"""
### Résumé :
- Sur {N} simulations, {success_rate:.2f}% des voyages sont globalement réussis.
- {summary_display.loc[summary_display['outcome']=='Cancelled','probability'].values[0]} ont été annulés.
- {summary_display.loc[summary_display['outcome']=='Major disruption (ski unavailable/limited)','probability'].values[0]} ont connu une disruption majeure.
""")

