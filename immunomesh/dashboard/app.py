"""ImmunoMesh research dashboard (Streamlit).  Launch:  python -m immunomesh.cli dashboard
Displays ONLY data produced by the implemented pipeline (results/final/demo + results/final/tables)."""
import os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from immunomesh.dashboard.data import RunData

RUN_DIR = Path(os.environ.get("IMMUNOMESH_RUN_DIR", "results/final/demo"))
FINAL_DIR = RUN_DIR.parent
STATE_COLORS = {"NORMAL": "#dfe6e9", "SUSPICIOUS": "#ffeaa7", "HIGH_RISK": "#fab1a0", "QUARANTINED": "#d63031",
                "RECOVERING": "#74b9ff", "RESTORED": "#55efc4"}

st.set_page_config(page_title="ImmunoMesh Research Dashboard", layout="wide")
st.title("ImmunoMesh — research dashboard")
st.warning("All data are SIMULATED / SYNTHETIC. Response actions are software state changes only; "
           "no real device, network, or hardware is involved.")
try:
    d = RunData(RUN_DIR)
except FileNotFoundError as e:
    st.error(str(e)); st.stop()
st.caption(f"Run: {d.meta['experiment_id']} · seed {d.meta['seed']} · detector threshold {d.meta['threshold']:.4f} · "
           f"decision time is software time on the host machine")

tabs = st.tabs(["Overview", "Detection", "Evidence", "Trust & consensus", "Response", "Audit", "Experiments", "Live Network"])
with tabs[0]:
    o = d.overview()
    cols = st.columns(4)
    for i, (k, v) in enumerate(o.items()):
        cols[i % 4].metric(k.replace("_", " ").title(), v)
    st.subheader("Anomalous flows by device")
    st.dataframe(d.anomaly_by_device(), use_container_width=True)

with tabs[1]:
    f = d.flows
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.hist(f[f.label == 0].anomaly_score, bins=60, alpha=.6, label="normal flows (ground truth)")
    ax.hist(f[f.label == 1].anomaly_score, bins=60, alpha=.6, label="attack flows (ground truth)")
    ax.axvline(d.meta["threshold"], color="k", ls="--", label="threshold")
    ax.set_xlabel("anomaly score (higher = more anomalous)"); ax.set_ylabel("flows"); ax.legend()
    st.pyplot(fig)
    st.subheader("Timeline of flagged flows")
    dev_order = sorted(f.device.unique())
    fig, ax = plt.subplots(figsize=(9, 3.5))
    t0 = f.timestamp.min()
    fl = f[f.is_anomaly == 1]
    ax.scatter(fl.timestamp - t0, fl.device.map({x: i for i, x in enumerate(dev_order)}), s=6,
               c=np.where(fl.label == 1, "#d63031", "#0984e3"))
    ax.set_yticks(range(len(dev_order))); ax.set_yticklabels(dev_order)
    ax.set_xlabel("simulated time (s)"); ax.set_title("red = true attack flow, blue = false positive")
    st.pyplot(fig)

with tabs[2]:
    st.subheader("Top contributing features (SHAP on Isolation Forest path length; positive = toward anomalous)")
    st.dataframe(d.top_features(12), use_container_width=True)
    ex = d.evidence
    if len(ex):
        dev = st.selectbox("Device", sorted(ex.device.unique()))
        g = ex[ex.device == dev].head(50)
        st.dataframe(g[["timestamp", "anomaly_score", "evidence_strength", "corroborated", "statements", "attack_type"]], use_container_width=True)
    p = d.dir / "evidence_examples.md"
    if p.exists(): st.markdown(p.read_text())

with tabs[3]:
    ts = d.trust_series()
    st.subheader("Device trust score over simulated time")
    st.line_chart(ts.pivot(index="epoch", columns="device", values="trust"))
    st.subheader("Peer support and consensus score")
    dev = st.selectbox("Device (consensus)", sorted(ts.device.unique()), key="cons")
    st.line_chart(ts[ts.device == dev].set_index("epoch")[["peer_support", "consensus"]])
    st.dataframe(ts.groupby("device").agg(min_trust=("trust", "min"), final_trust=("trust", "last"),
                                          worst_risk=("risk_level", lambda s: max(s, key=["LOW", "MEDIUM", "HIGH", "CRITICAL"].index))).reset_index())

with tabs[4]:
    sm = d.state_matrix()
    names = list(STATE_COLORS)
    arr = sm.apply(lambda c: c.map({n: i for i, n in enumerate(names)})).to_numpy(dtype=float)
    from matplotlib.colors import ListedColormap
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.imshow(arr, aspect="auto", cmap=ListedColormap(list(STATE_COLORS.values())), vmin=0, vmax=len(names) - 1, interpolation="nearest")
    ax.set_yticks(range(len(sm.index))); ax.set_yticklabels(sm.index)
    E = d.meta.get("timing") and 10
    ax.set_xlabel("epoch (10 s each, simulated time)"); ax.set_title("Response state per device")
    for dev, ws in d.windows.items():
        for _, t0, t1 in ws:
            ax.plot([t0 / 10, t1 / 10], [list(sm.index).index(dev)] * 2, color="k", lw=3)
    st.pyplot(fig)
    st.caption("Legend: " + ", ".join(f"{k}" for k in STATE_COLORS) + ". Black bars = ground-truth attack windows.")
    ev = d.events
    if len(ev): st.dataframe(ev[ev.event_type.isin(["QUARANTINE_STARTED", "RECOVERY_STARTED", "RESTORED", "HIGH_RISK_DECLARED", "RECOVERY_FAILED_REQUARANTINE"])], use_container_width=True)

with tabs[5]:
    dev = st.selectbox("Device filter", ["(all)"] + sorted(d.epochs.device.unique()), key="aud")
    et = st.selectbox("Event type", ["(all)"] + sorted(d.audit_events().event_type.unique()), key="aud2")
    a = d.audit_events(None if dev == "(all)" else dev, None if et == "(all)" else et)
    st.dataframe(a, use_container_width=True)
    st.download_button("Download audit CSV", a.to_csv(index=False), "audit_events.csv")

with tabs[6]:
    st.subheader("Research Experiments")

    tdir = FINAL_DIR / "tables"

    if tdir.exists():
        table_names = [
            "ablation_E2_low_intensity",
            "ablation_E3_high_intensity",
            "ablation_E4_multi_device_5",
            "ablation_E10_recovery_quarantine",
            "model_comparison",
            "per_attack_recall_E3",
            "threshold_analysis_flow",
            "threshold_analysis_mesh",
            "window_length_sweep",
            "flow_detection_by_scenario",
        ]

        for name in table_names:
            table_path = tdir / f"{name}.csv"

            if table_path.is_file():
                st.subheader(name.replace("_", " "))
                st.dataframe(
                    pd.read_csv(table_path),
                    use_container_width=True,
                )

        figures_dir = FINAL_DIR / "figures"

        if figures_dir.exists():
            for img in sorted(figures_dir.glob("*.png"))[:12]:
                st.image(str(img), caption=img.stem)
    else:
        st.info(
            "Research tables are unavailable. "
            "Check the committed results/final directory."
        )

with tabs[7]:
    st.subheader("LIVE NETWORK")
    st.caption("This tab reads real capture runs only (results/live/ or results/hil/) — never "
              "simulation data. Simulation (Phases 1-10) and live/HIL results are kept in "
              "separate directories and are never mixed in one chart.")
    from immunomesh.integration.dashboard_live import LiveRunData
    import os
    live_dir = st.selectbox("Run directory", ["results/hil", "results/live"], index=0)
    if not os.path.isdir(live_dir):
        st.info(f"No run found at {live_dir}. Run `python -m immunomesh.cli edge` or "
                "`python -m immunomesh.integration.hil_selftest` first.")
    else:
        ld = LiveRunData(live_dir)
        h = ld.health()
        st.warning(f"Mode: {h['mode']} — " +
                  ("real captured traffic" if h["mode"] != "SIMULATED" else "simulated"))
        cols = st.columns(4)
        for i, (k, v) in enumerate(h.items()):
            cols[i % 4].metric(k.replace("_", " ").title(), v)
        st.markdown("#### Devices")
        st.dataframe(ld.devices(), use_container_width=True)
        st.markdown("#### Alerts")
        st.dataframe(ld.alerts(), use_container_width=True)
        perf = ld.performance()
        if len(perf):
            st.markdown("#### Performance over the run")
            st.line_chart(perf.set_index("ts")[["packets_total"]] if "packets_total" in perf else perf)
