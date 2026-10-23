"""ImmunoMesh research dashboard (Streamlit).  Launch:  python -m immunomesh.cli dashboard
Displays ONLY data produced by the implemented pipeline (results/final/demo + results/final/tables)."""
import os
import sys
from pathlib import Path

# Streamlit Cloud may put this nested app directory, rather than the repository root,
# on sys.path. Add the repository root before importing the local ImmunoMesh package.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from immunomesh.dashboard.data import RunData

RUN_DIR = Path(os.environ.get("IMMUNOMESH_RUN_DIR", str(PROJECT_ROOT / "results/final/demo"))).expanduser()
if not RUN_DIR.is_absolute():
    RUN_DIR = PROJECT_ROOT / RUN_DIR
RUN_DIR = RUN_DIR.resolve()
FINAL_DIR = RUN_DIR.parent
STATE_COLORS = {"NORMAL": "#dfe6e9", "SUSPICIOUS": "#ffeaa7", "HIGH_RISK": "#fab1a0", "QUARANTINED": "#d63031",
                "RECOVERING": "#74b9ff", "RESTORED": "#55efc4"}

st.set_page_config(page_title="ImmunoMesh | Network Security Analytics", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1500px; padding-top: 1.5rem; padding-bottom: 2.2rem;}
.im-hero {
    padding: 1.55rem 1.7rem; margin: 0 0 1.1rem 0; border-radius: 18px;
    background: linear-gradient(120deg, #101b2d 0%, #123b4b 100%);
    border: 1px solid rgba(94, 234, 212, .24);
    box-shadow: 0 10px 30px rgba(0, 0, 0, .12);
}
.im-eyebrow {font-size: .72rem; letter-spacing: .18em; text-transform: uppercase; color: #76e5d4; font-weight: 750;}
.im-hero h1 {font-size: 2.35rem; line-height: 1.16; margin: .45rem 0 .35rem; color: #f8fafc; font-weight: 780;}
.im-hero p {margin: 0; font-size: 1.05rem; color: #d1e3ed;}
.im-chips {display: flex; gap: .5rem; margin-top: 1.05rem; flex-wrap: wrap;}
.im-chip {display: inline-block; padding: .34rem .62rem; border-radius: 999px; font-size: .66rem;
    font-weight: 750; letter-spacing: .08em; color: #d0fff6; background: rgba(20, 184, 166, .12);
    border: 1px solid rgba(94, 234, 212, .23);}
div[data-testid="stTabs"] button[role="tab"] {font-weight: 650; padding: .68rem .82rem;}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {color: #70e4d0; border-bottom-color: #40cbb6;}
</style>
""", unsafe_allow_html=True)

try:
    d = RunData(RUN_DIR)
except FileNotFoundError as e:
    st.error(str(e)); st.stop()

st.markdown("""
<div class="im-hero">
  <div class="im-eyebrow">Network Security Analytics</div>
  <h1>ImmunoMesh</h1>
  <p>Adaptive threat detection · Device trust · Evidence-led response</p>
  <div class="im-chips">
    <span class="im-chip">THREAT DETECTION</span>
    <span class="im-chip">DEVICE TRUST</span>
    <span class="im-chip">SIMULATED RESPONSE</span>
    <span class="im-chip">SCENARIO EVALUATION</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.warning(
    "Research-scope notice: all detection and response results shown here use "
    "synthetic/simulated traffic. This dashboard does not inspect camera malware, "
    "control physical devices, or prove real-network detection performance."
)

with st.expander("About this dashboard", expanded=False):
    st.caption("Scenario evaluation uses simulated network traffic. Isolation and recovery events represent software-level response states; this hosted dashboard does not control physical devices.")

with st.expander("Run details", expanded=False):
    run_cols = st.columns(4)
    run_cols[0].metric("Experiment", d.meta["experiment_id"])
    run_cols[1].metric("Seed", d.meta["seed"])
    run_cols[2].metric("Decision threshold", f"{d.meta['threshold']:.4f}")
    run_cols[3].metric("Data source", "Synthetic / simulated")

tabs = st.tabs(["Overview", "Detection", "Evidence", "Trust & Consensus", "Response Simulation", "Audit Log", "Evaluation", "Capture Test"])
with tabs[0]:
    o = d.overview()
    metric_labels = {
        "monitored_devices": "Devices monitored",
        "total_flows": "Network flows",
        "normal_events": "Normal flows",
        "anomalous_events": "Flagged flows",
        "high_risk_events": "High-risk events",
        "quarantine_events": "Quarantine actions",
        "devices_quarantined": "Devices quarantined",
        "recovered_events": "Recoveries completed",
    }
    cols = st.columns(4)
    for i, (k, v) in enumerate(o.items()):
        cols[i % 4].metric(metric_labels.get(k, k.replace("_", " ").title()), v)
    st.subheader("Traffic summary by device")
    st.dataframe(d.anomaly_by_device(), use_container_width=True)

with tabs[1]:
    f = d.flows
    st.subheader("Anomaly score distribution")
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.hist(f[f.label == 0].anomaly_score, bins=60, alpha=.65, label="Normal traffic")
    ax.hist(f[f.label == 1].anomaly_score, bins=60, alpha=.65, label="Attack-labelled traffic")
    ax.axvline(d.meta["threshold"], color="black", ls="--", label="Decision threshold")
    ax.set_xlabel("Anomaly score"); ax.set_ylabel("Flow count"); ax.legend(frameon=False)
    st.pyplot(fig)
    st.caption("Distribution of scores for the selected scenario.")

    st.subheader("Flagged-flow timeline")
    dev_order = sorted(f.device.unique())
    fig, ax = plt.subplots(figsize=(9, 3.5))
    t0 = f.timestamp.min()
    fl = f[f.is_anomaly == 1]
    ax.scatter(fl.timestamp - t0, fl.device.map({x: i for i, x in enumerate(dev_order)}), s=7,
               c=np.where(fl.label == 1, "#d63031", "#0984e3"))
    ax.set_yticks(range(len(dev_order))); ax.set_yticklabels(dev_order)
    ax.set_xlabel("Time from scenario start (s)"); ax.set_ylabel("Device")
    st.pyplot(fig)
    st.caption("Red markers: attack-labelled flows · Blue markers: normal flows flagged by the detector.")

with tabs[2]:
    st.subheader("Feature-level explanation")
    st.caption("SHAP-based interpretation of features contributing to the Isolation Forest score.")
    feature_view = d.top_features(12).rename(columns={
        "feature": "Feature",
        "mean_contribution": "Mean contribution",
        "count": "Records",
    })
    st.dataframe(feature_view, use_container_width=True)
    ex = d.evidence
    if len(ex):
        dev = st.selectbox("Inspect device", sorted(ex.device.unique()))
        g = ex[ex.device == dev].head(50)
        evidence_view = g[["timestamp", "anomaly_score", "evidence_strength", "corroborated", "statements", "attack_type"]].rename(columns={
            "timestamp": "Timestamp",
            "anomaly_score": "Anomaly score",
            "evidence_strength": "Evidence strength",
            "corroborated": "Corroborated",
            "statements": "Evidence signals",
            "attack_type": "Scenario label",
        })
        st.dataframe(evidence_view, use_container_width=True)
    p = d.dir / "evidence_examples.md"
    if p.exists():
        with st.expander("Example evidence records", expanded=False):
            st.markdown(p.read_text())

with tabs[3]:
    ts = d.trust_series()
    st.subheader("Device trust over time")
    st.line_chart(ts.pivot(index="epoch", columns="device", values="trust"))
    st.subheader("Peer support and consensus")
    dev = st.selectbox("Inspect device", sorted(ts.device.unique()), key="cons")
    st.line_chart(ts[ts.device == dev].set_index("epoch")[["peer_support", "consensus"]])
    trust_summary = ts.groupby("device").agg(
        min_trust=("trust", "min"),
        final_trust=("trust", "last"),
        worst_risk=("risk_level", lambda s: max(s, key=["LOW", "MEDIUM", "HIGH", "CRITICAL"].index)),
    ).reset_index().rename(columns={
        "device": "Device",
        "min_trust": "Minimum trust",
        "final_trust": "Final trust",
        "worst_risk": "Highest risk observed",
    })
    st.dataframe(trust_summary, use_container_width=True)

with tabs[4]:
    sm = d.state_matrix()
    names = list(STATE_COLORS)
    arr = sm.apply(lambda col: col.map({name: i for i, name in enumerate(names)})).to_numpy(dtype=float)
    from matplotlib.colors import ListedColormap
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.imshow(arr, aspect="auto", cmap=ListedColormap(list(STATE_COLORS.values())), vmin=0, vmax=len(names) - 1, interpolation="nearest")
    ax.set_yticks(range(len(sm.index))); ax.set_yticklabels(sm.index)
    ax.set_xlabel("Scenario time (10-second steps)")
    ax.set_title("Device response timeline")
    for dev, windows in d.windows.items():
        for _, t0, t1 in windows:
            ax.plot([t0 / 10, t1 / 10], [list(sm.index).index(dev)] * 2, color="black", lw=3)
    st.pyplot(fig)
    st.caption("States: Normal · Suspicious · High risk · Quarantined · Recovering · Restored. Black bars mark attack windows.")

    ev = d.events
    if len(ev):
        response_events = ev[ev.event_type.isin([
            "QUARANTINE_STARTED", "RECOVERY_STARTED", "RESTORED",
            "HIGH_RISK_DECLARED", "RECOVERY_FAILED_REQUARANTINE",
        ])].copy()
        response_events = response_events[[
            col for col in ["ts", "device", "event_type", "risk_level", "state_from", "state_to", "response"]
            if col in response_events.columns
        ]].rename(columns={
            "ts": "Timestamp",
            "device": "Device",
            "event_type": "Event",
            "risk_level": "Risk level",
            "state_from": "Previous state",
            "state_to": "New state",
            "response": "Response action",
        })
        st.subheader("Simulated response-state history")
        st.dataframe(response_events, use_container_width=True)

with tabs[5]:
    audit_all = d.audit_events()
    col1, col2 = st.columns(2)
    dev = col1.selectbox("Device", ["All devices"] + sorted(d.epochs.device.unique()), key="aud")
    et = col2.selectbox("Event type", ["All event types"] + sorted(audit_all.event_type.unique()), key="aud2")
    a = d.audit_events(None if dev == "All devices" else dev, None if et == "All event types" else et)
    audit_view = a.rename(columns={
        "ts": "Timestamp",
        "device": "Device",
        "event_type": "Event",
        "detection_score": "Detection score",
        "risk_level": "Risk level",
        "state_from": "Previous state",
        "state_to": "New state",
        "response": "Response action",
    })
    st.dataframe(audit_view, use_container_width=True)
    st.download_button("Export audit log (CSV)", a.to_csv(index=False), "audit_events.csv")

with tabs[6]:
    st.subheader("Evaluation results")
    st.caption(
        "Synthetic scenario benchmarks, detector comparisons and sensitivity analyses. "
        "Flow-level metrics and response-state epoch/window metrics are different quantities."
    )

    tdir = FINAL_DIR / "tables"
    table_labels = {
        "ablation_E2_low_intensity": "Low-intensity scenario",
        "ablation_E3_high_intensity": "High-intensity scenario",
        "ablation_E4_multi_device_5": "Multi-device scenario (5 devices)",
        "ablation_E10_recovery_quarantine": "Simulated response-state evaluation",
        "model_comparison": "Detector comparison",
        "per_attack_recall_E3": "Detection recall by attack type",
        "threshold_analysis_flow": "Flow-level threshold analysis",
        "threshold_analysis_mesh": "Mesh-level threshold analysis",
        "window_length_sweep": "Detection window-length analysis",
        "flow_detection_by_scenario": "Flow detection by scenario",
    }

    if tdir.exists():
        for name, label in table_labels.items():
            table_path = tdir / f"{name}.csv"
            if table_path.is_file():
                with st.expander(label, expanded=(name == "ablation_E3_high_intensity")):
                    st.dataframe(pd.read_csv(table_path), use_container_width=True)

        figures_dir = FINAL_DIR / "figures"
        if figures_dir.exists():
            with st.expander("Evaluation figures", expanded=True):
                for img in sorted(figures_dir.glob("*.png"))[:12]:
                    st.image(str(img), caption=img.stem.replace("_", " ").title())
    else:
        st.info("Evaluation tables are not available for this run.")

with tabs[7]:
    st.subheader("Packet-capture validation")
    st.caption("Recorded loopback self-test using locally generated TCP traffic. No physical camera or industrial device was connected during this run.")
    from immunomesh.integration.dashboard_live import LiveRunData
    live_dirs = {
        "results/hil": PROJECT_ROOT / "results/hil",
        "results/live": PROJECT_ROOT / "results/live",
    }
    live_choice = st.selectbox("Capture record", list(live_dirs), index=0)
    live_dir = live_dirs[live_choice]
    if not live_dir.is_dir():
        st.info(f"No recorded capture test found at {live_choice}.")
    else:
        ld = LiveRunData(live_dir)
        h = ld.health()
        m = ld.manifest
        st.caption(f"Mode: {h['mode']} · Interface: {m.get('interface', 'not recorded')}")
        cols = st.columns(4)
        cols[0].metric("Packets captured", m.get("packets_captured", 0))
        cols[1].metric("TCP connections generated", m.get("real_connections_generated", 0))
        cols[2].metric("Supervisor failures", h.get("supervisor_failures", 0))
        cols[3].metric("Dropped packets", h.get("dropped_packets", 0))
        st.markdown("#### Observed devices")
        st.dataframe(ld.devices().rename(columns={
            "ip": "IP address",
            "hostname": "Hostname",
            "device_type": "Device type",
            "confidence": "Classification confidence",
            "observed_ports": "Observed ports",
        }), use_container_width=True)
        st.markdown("#### Detection events")
        st.dataframe(ld.alerts().rename(columns={
            "ts": "Timestamp",
            "device": "Device",
            "event_type": "Event",
            "detection_score": "Detection score",
            "risk_level": "Risk level",
            "response": "Response action",
        }), use_container_width=True)
        perf = ld.performance()
        if len(perf):
            st.markdown("#### Capture performance")
            st.line_chart(perf.set_index("ts")[["packets_total"]] if "packets_total" in perf else perf)
