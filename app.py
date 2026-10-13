from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Dashboard Ketenagakerjaan Indonesia",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Tampilan ----------
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
      [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        padding: 16px 18px;
        border-radius: 12px;
        box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
      }
      [data-testid="stMetricLabel"] {font-size: 0.88rem;}
      [data-testid="stMetricValue"] {font-size: 1.7rem;}
      .small-note {color: #64748b; font-size: 0.85rem;}
      div[data-testid="stTabs"] button {font-weight: 600;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Dashboard Analisis Ketenagakerjaan Indonesia")
st.caption(
    "Analisis deskriptif perubahan Tingkat Pengangguran Terbuka (TPT) "
    "dan Tingkat Partisipasi Angkatan Kerja (TPAK) antarprovinsi."
)

DEFAULT_DATA = Path(__file__).with_name("data_ketenagakerjaan_agustus_2021_2025.csv")
REQUIRED = ["Provinsi", "Tahun", "TPT", "TPAK"]


def read_uploaded_file(file):
    if file is None:
        if DEFAULT_DATA.exists():
            return pd.read_csv(DEFAULT_DATA), DEFAULT_DATA.name
        return None, None
    if file.name.lower().endswith(".xlsx"):
        return pd.read_excel(file), file.name
    return pd.read_csv(file), file.name


with st.sidebar:
    st.header("Pengaturan")
    upload = st.file_uploader(
        "Unggah dataset CSV/Excel",
        type=["csv", "xlsx"],
        help="Format kolom: Provinsi, Tahun, TPT, TPAK.",
    )
    stable_threshold = st.number_input(
        "Ambang kategori stabil (poin persentase)",
        min_value=0.0,
        max_value=5.0,
        value=0.2,
        step=0.1,
        help="Ambang ini adalah parameter analisis dan perlu dijelaskan dalam metodologi.",
    )

try:
    df, source_name = read_uploaded_file(upload)
except Exception as exc:
    st.error(f"File tidak dapat dibaca: {exc}")
    st.stop()

if df is None:
    st.info("Unggah dataset untuk mulai menggunakan dashboard.")
    st.stop()

df.columns = [str(col).strip() for col in df.columns]
missing_cols = [col for col in REQUIRED if col not in df.columns]
if missing_cols:
    st.error(
        "Kolom wajib belum tersedia: "
        + ", ".join(missing_cols)
        + ". Gunakan kolom Provinsi, Tahun, TPT, dan TPAK."
    )
    st.stop()

df = df[REQUIRED].copy()
df["Provinsi"] = df["Provinsi"].astype("string").str.strip()
for col in ["Tahun", "TPT", "TPAK"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Data rows that are incomplete or duplicate are shown for checking, not silently hidden.
invalid = df[df[REQUIRED].isna().any(axis=1)]
duplicates = df[df.duplicated(subset=["Provinsi", "Tahun"], keep=False)]
df = df.dropna(subset=REQUIRED).copy()
df["Tahun"] = df["Tahun"].astype(int)
df = df[~df.duplicated(subset=["Provinsi", "Tahun"], keep=False)].copy()

if df.empty:
    st.error("Tidak ada baris valid setelah pemeriksaan data.")
    st.stop()

if ((df["TPT"] < 0) | (df["TPT"] > 100) | (df["TPAK"] < 0) | (df["TPAK"] > 100)).any():
    st.warning("Ada nilai TPT/TPAK di luar rentang 0–100. Verifikasi dataset sumber.")

all_years = sorted(df["Tahun"].unique().tolist())
min_year, max_year = min(all_years), max(all_years)

with st.sidebar:
    st.subheader("Filter data")
    year_range = st.slider(
        "Rentang tahun",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        step=1,
    )
    province_options = sorted(df["Provinsi"].unique().tolist())
    default_provinces = province_options[: min(5, len(province_options))]
    selected_provinces = st.multiselect(
        "Provinsi untuk grafik tren (maks. 8)",
        province_options,
        default=default_provinces,
        max_selections=8,
        help="Pilih maksimal 8 provinsi agar grafik tetap mudah dibaca.",
    )

period_df = df[df["Tahun"].between(year_range[0], year_range[1])].copy()
if period_df.empty:
    st.warning("Tidak ada data pada rentang tahun yang dipilih.")
    st.stop()

latest_year = int(period_df["Tahun"].max())
latest = period_df[period_df["Tahun"] == latest_year]
prior_year = latest_year - 1
prior = period_df[period_df["Tahun"] == prior_year]

# KPI values use all valid provinces in the latest year, not only trend selections.
avg_tpt = latest["TPT"].mean()
avg_tpak = latest["TPAK"].mean()
n_provinces = latest["Provinsi"].nunique()
coverage = len(latest)

tpt_change = None
tpak_change = None
if not prior.empty:
    tpt_change = latest["TPT"].mean() - prior["TPT"].mean()
    tpak_change = latest["TPAK"].mean() - prior["TPAK"].mean()

st.markdown(f"**Sumber file:** `{source_name}`")
if len(invalid) or len(duplicates):
    with st.expander("⚠️ Pemeriksaan kualitas data", expanded=True):
        st.write(f"Baris dengan nilai kosong/tidak terbaca: **{len(invalid)}**")
        st.write(f"Baris yang terlibat duplikasi provinsi-tahun: **{len(duplicates)}**")
        if len(invalid):
            st.caption("Baris tidak lengkap:")
            st.dataframe(invalid, use_container_width=True, hide_index=True)
        if len(duplicates):
            st.caption("Baris duplikat:")
            st.dataframe(duplicates, use_container_width=True, hide_index=True)

st.subheader(f"Ringkasan indikator — {latest_year}")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Rata-rata TPT", f"{avg_tpt:.2f}%" if pd.notna(avg_tpt) else "—",
          delta=f"{tpt_change:+.2f} poin" if tpt_change is not None else None,
          delta_color="inverse")
k2.metric("Rata-rata TPAK", f"{avg_tpak:.2f}%" if pd.notna(avg_tpak) else "—",
          delta=f"{tpak_change:+.2f} poin" if tpak_change is not None else None)
k3.metric("Provinsi tercatat", f"{n_provinces}")
k4.metric("Baris valid tahun terakhir", f"{coverage}")

st.caption(
    "Rata-rata dihitung dari provinsi yang memiliki data valid pada tahun terakhir dalam filter. "
    "Perubahan pada kartu dibandingkan dengan tahun kalender sebelumnya jika datanya tersedia."
)

tab_overview, tab_trends, tab_changes, tab_data = st.tabs(
    ["Ikhtisar", "Tren Provinsi", "Perubahan Antarperiode", "Data & Unduh"]
)

with tab_overview:
    left, right = st.columns(2)
    with left:
        st.markdown("#### 10 provinsi dengan TPT tertinggi")
        ranking_tpt = latest.nlargest(min(10, len(latest)), "TPT").sort_values("TPT")
        fig = px.bar(
            ranking_tpt, x="TPT", y="Provinsi", orientation="h",
            labels={"TPT": "TPT (%)", "Provinsi": ""},
            text=ranking_tpt["TPT"].map(lambda x: f"{x:.2f}%"),
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(height=430, margin=dict(l=10, r=45, t=15, b=20),
                          yaxis=dict(title="", automargin=True), xaxis=dict(rangemode="tozero"))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown("#### 10 provinsi dengan TPAK tertinggi")
        ranking_tpak = latest.nlargest(min(10, len(latest)), "TPAK").sort_values("TPAK")
        fig2 = px.bar(
            ranking_tpak, x="TPAK", y="Provinsi", orientation="h",
            labels={"TPAK": "TPAK (%)", "Provinsi": ""},
            text=ranking_tpak["TPAK"].map(lambda x: f"{x:.2f}%"),
        )
        fig2.update_traces(textposition="outside", cliponaxis=False)
        fig2.update_layout(height=430, margin=dict(l=10, r=45, t=15, b=20),
                           yaxis=dict(title="", automargin=True), xaxis=dict(rangemode="tozero"))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("#### Ringkasan data tahun terakhir")
    summary_latest = latest[["Provinsi", "TPT", "TPAK"]].sort_values("TPT", ascending=False)
    st.dataframe(summary_latest, use_container_width=True, hide_index=True,
                 column_config={
                     "TPT": st.column_config.NumberColumn("TPT (%)", format="%.2f"),
                     "TPAK": st.column_config.NumberColumn("TPAK (%)", format="%.2f"),
                 })

with tab_trends:
    if not selected_provinces:
        st.info("Pilih minimal satu provinsi di sidebar untuk menampilkan grafik tren.")
    else:
        trend = period_df[period_df["Provinsi"].isin(selected_provinces)].sort_values(["Tahun", "Provinsi"])
        st.markdown("#### Tren Tingkat Pengangguran Terbuka (TPT)")
        f_tpt = px.line(
            trend, x="Tahun", y="TPT", color="Provinsi", markers=True,
            labels={"Tahun": "Tahun", "TPT": "TPT (%)", "Provinsi": "Provinsi"},
        )
        f_tpt.update_xaxes(tickmode="array", tickvals=sorted(trend["Tahun"].unique()),
                           ticktext=[str(int(y)) for y in sorted(trend["Tahun"].unique())], dtick=1)
        f_tpt.update_layout(height=420, hovermode="x unified",
                            margin=dict(l=10, r=10, t=20, b=10), legend_title_text="Provinsi")
        st.plotly_chart(f_tpt, use_container_width=True)

        st.markdown("#### Tren Tingkat Partisipasi Angkatan Kerja (TPAK)")
        f_tpak = px.line(
            trend, x="Tahun", y="TPAK", color="Provinsi", markers=True,
            labels={"Tahun": "Tahun", "TPAK": "TPAK (%)", "Provinsi": "Provinsi"},
        )
        f_tpak.update_xaxes(tickmode="array", tickvals=sorted(trend["Tahun"].unique()),
                            ticktext=[str(int(y)) for y in sorted(trend["Tahun"].unique())], dtick=1)
        f_tpak.update_layout(height=420, hovermode="x unified",
                             margin=dict(l=10, r=10, t=20, b=10), legend_title_text="Provinsi")
        st.plotly_chart(f_tpak, use_container_width=True)

with tab_changes:
    st.markdown("#### Perubahan dari tahun awal ke tahun akhir yang tersedia")
    result_rows = []
    for province, group in period_df.groupby("Provinsi"):
        group = group.sort_values("Tahun")
        first, last = group.iloc[0], group.iloc[-1]
        changes_tpt = group["TPT"].diff().dropna()
        changes_tpak = group["TPAK"].diff().dropna()

        def classify(start, end, changes, threshold):
            delta = float(end - start)
            if abs(delta) <= threshold:
                endpoint = "Stabil (sesuai ambang)"
            elif delta > 0:
                endpoint = "Meningkat"
            else:
                endpoint = "Menurun"
            directions = set()
            for value in changes:
                if value > threshold:
                    directions.add("naik")
                elif value < -threshold:
                    directions.add("turun")
            pattern = "Berfluktuasi" if {"naik", "turun"}.issubset(directions) else endpoint
            return delta, pattern

        delta_tpt, pattern_tpt = classify(first["TPT"], last["TPT"], changes_tpt, stable_threshold)
        delta_tpak, pattern_tpak = classify(first["TPAK"], last["TPAK"], changes_tpak, stable_threshold)
        result_rows.append({
            "Provinsi": province,
            "Tahun awal": int(first["Tahun"]),
            "Tahun akhir": int(last["Tahun"]),
            "TPT awal (%)": first["TPT"],
            "TPT akhir (%)": last["TPT"],
            "Perubahan TPT (poin persentase)": delta_tpt,
            "Pola TPT": pattern_tpt,
            "TPAK awal (%)": first["TPAK"],
            "TPAK akhir (%)": last["TPAK"],
            "Perubahan TPAK (poin persentase)": delta_tpak,
            "Pola TPAK": pattern_tpak,
        })
    result = pd.DataFrame(result_rows).sort_values("Perubahan TPT (poin persentase)")
    st.caption(
        f"Kategori stabil menggunakan ambang ±{stable_threshold:.2f} poin persentase. "
        "Ambang ini perlu diberi dasar metodologis dalam laporan."
    )
    st.dataframe(result, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Unduh hasil analisis CSV",
        data=result.to_csv(index=False).encode("utf-8-sig"),
        file_name="hasil_analisis_tpt_tpak.csv",
        mime="text/csv",
    )

with tab_data:
    st.markdown("#### Data yang digunakan")
    st.dataframe(period_df.sort_values(["Tahun", "Provinsi"]), use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Unduh data terfilter CSV",
        data=period_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="data_tpt_tpak_terfilter.csv",
        mime="text/csv",
    )
    coverage_table = (
        df.groupby("Tahun")["Provinsi"].nunique().rename("Jumlah provinsi tercatat").reset_index()
    )
    st.markdown("#### Cakupan provinsi per tahun")
    st.dataframe(coverage_table, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "Catatan metodologis: sistem bersifat deskriptif, tidak membuktikan sebab-akibat, "
    "dan hasil bergantung pada kualitas serta konsistensi dataset sumber. "
    "Pastikan angka diperiksa terhadap publikasi resmi BPS sebelum laporan final."
)
