# =============================================================================
#  DERIV BOT DASHBOARD — Streamlit
#  Controla o bot no Railway via Redis (Upstash)
# =============================================================================

import streamlit as st
import httpx
import json
import os
import time
import pandas as pd
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
#  REDIS CLIENT
# ─────────────────────────────────────────────────────────────────────────────

REDIS_URL   = os.environ.get("UPSTASH_REDIS_REST_URL","").strip()
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","").strip()

def redis_set(key: str, value, ex: int = None):
    # Upstash REST API: POST /set/key/value — valor vai directo na URL
    data = json.dumps(value) if not isinstance(value, str) else value
    headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
    try:
        url = f"{REDIS_URL}/set/{key}/{data}"
        if ex: url += f"/ex/{ex}"
        httpx.post(url, headers=headers, timeout=5)
    except: pass

def redis_get(key: str):
    headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
    try:
        r = httpx.get(f"{REDIS_URL}/get/{key}", headers=headers, timeout=5)
        result = r.json().get("result")
        if result is None: return None
        try: return json.loads(result)
        except: return result
    except: return None

def redis_lrange(key: str, start: int, stop: int):
    headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
    try:
        r = httpx.get(f"{REDIS_URL}/lrange/{key}/{start}/{stop}", headers=headers, timeout=5)
        items = r.json().get("result", [])
        out = []
        for i in items:
            try: out.append(json.loads(i))
            except: out.append(i)
        return out
    except: return []

def redis_del(*keys):
    headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
    for key in keys:
        try: httpx.post(f"{REDIS_URL}/del/{key}", headers=headers, timeout=5)
        except: pass

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────────────

ESTRATEGIAS = {
    "🎯 Precisão Máxima":       ("Baixo",   "Triple confirm: Trend + Candle + S/R. Poucos trades, alta qualidade."),
    "📊 Suporte & Resistência": ("Médio",   "Entra em zonas S/R com candle de reversão."),
    "🕯️ Candles Puros":        ("Médio",   "Só padrões premium: 3 Soldiers, Engulfing, Stars."),
    "🌀 Fibonacci":             ("Médio",   "Retracções 38.2%, 50%, 61.8% com confirmação."),
    "🧠 Smart Money (SMC)":    ("Alto ⚠️", "Order Blocks + BOS + Liquidity Sweeps. Só demo!"),
}

# ─────────────────────────────────────────────────────────────────────────────
#  LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Deriv Bot Dashboard", page_icon="⚡",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif;}
.stApp{background:#0a0e1a;color:#e0e6f5;}
.metric-card{background:#111827;border:1px solid #1e3a5f;border-radius:12px;padding:18px;text-align:center;}
.profit {color:#00d4aa;font-family:'JetBrains Mono',monospace;font-size:1.8rem;font-weight:700;}
.loss   {color:#ff4d6d;font-family:'JetBrains Mono',monospace;font-size:1.8rem;font-weight:700;}
.neutral{color:#7c9cbf;font-family:'JetBrains Mono',monospace;font-size:1.8rem;font-weight:700;}
.signal-box     {background:#111827;border-left:4px solid #00d4aa;border-radius:8px;padding:10px 14px;margin:5px 0;font-family:'JetBrains Mono',monospace;font-size:.82rem;}
.signal-sell    {border-left-color:#ff4d6d;}
.signal-wait    {border-left-color:#f59e0b;}
.strat-card     {background:#111827;border:1px solid #1e3a5f;border-radius:10px;padding:12px 16px;margin:8px 0;}
.dot-green      {width:10px;height:10px;background:#00d4aa;border-radius:50%;display:inline-block;margin-right:6px;}
.dot-red        {width:10px;height:10px;background:#ff4d6d;border-radius:50%;display:inline-block;margin-right:6px;}
.dot-yellow     {width:10px;height:10px;background:#f59e0b;border-radius:50%;display:inline-block;margin-right:6px;}
.stButton>button{background:linear-gradient(135deg,#00d4aa,#0099ff);color:#0a0e1a;font-weight:700;border:none;border-radius:8px;}
.risk-low {color:#00d4aa;font-weight:700;}
.risk-med {color:#f59e0b;font-weight:700;}
.risk-high{color:#ff4d6d;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR — Configurações e Controlo
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚡ Deriv Bot Pro")
    st.markdown("---")

    api_key = st.text_input("🔑 PAT Token", type="password",
                             value=os.environ.get("DERIV_API_TOKEN",""))
    app_id  = st.text_input("🆔 App ID",
                             value=os.environ.get("DERIV_APP_ID",""))

    st.markdown("---")
    st.markdown("### 🎮 Estratégia")
    estrategia = st.selectbox("Modo", list(ESTRATEGIAS.keys()))
    risco, desc = ESTRATEGIAS[estrategia]
    rc = "risk-high" if "Alto" in risco else ("risk-med" if "Médio" in risco else "risk-low")
    st.markdown(f'<div class="strat-card"><span class="{rc}">{risco}</span><br><span style="font-size:.8rem;color:#a0b0c8">{desc}</span></div>',
                unsafe_allow_html=True)

    st.markdown("---")
    account_type = st.selectbox("Conta", ["demo","real"])
    symbol       = st.selectbox("Ativo", ["R_100","R_75","R_50","R_25","R_10",
                                           "1HZ100V","1HZ75V","frxEURUSD","frxGBPUSD","frxUSDJPY"])
    duration     = st.selectbox("Duração", ["1 tique","5 tiques","10 tiques","15s","30s","1m","5m"])
    stake        = st.number_input("Aposta (USD)", min_value=0.35, max_value=100.0, value=1.0, step=0.5)
    daily_goal   = st.number_input("Meta Diária (USD)", value=5.0, step=0.5)
    max_loss     = st.number_input("Stop Loss (USD)", value=2.0, step=0.5)
    martingale   = st.toggle("Martingale", value=False)
    mult         = st.slider("Multiplicador", 1.5, 3.0, 2.0, 0.5) if martingale else 1.0

    st.markdown("---")
    c1, c2 = st.columns(2)
    start_btn = c1.button("▶ Iniciar", use_container_width=True)
    stop_btn  = c2.button("⏹ Parar",  use_container_width=True)

    if st.button("🗑️ Limpar dados", use_container_width=True):
        redis_del("bot:trades","bot:logs","bot:signals","bot:stats")
        st.success("Dados limpos!")

# ─────────────────────────────────────────────────────────────────────────────
#  LÓGICA DE CONTROLO
# ─────────────────────────────────────────────────────────────────────────────

if start_btn:
    if not api_key:
        st.error("❌ Insere o PAT Token!")
    elif not app_id:
        st.error("❌ Insere o App ID!")
    elif not REDIS_URL or not REDIS_TOKEN:
        st.error("❌ Redis não configurado! Verifica os Secrets do Streamlit.")
    else:
        cfg = {"api_token": api_key, "app_id": app_id,
               "account_type": account_type, "estrategia": estrategia,
               "symbol": symbol, "duration": duration, "stake": stake,
               "daily_goal": daily_goal, "max_loss": max_loss,
               "martingale": martingale, "mult": mult}
        redis_set("bot:config", cfg)
        redis_set("bot:command", "START")
        st.success(f"✅ Comando START enviado! Bot inicia em segundos.")

if stop_btn:
    redis_set("bot:command", "STOP")
    st.warning("⏹ Comando STOP enviado!")

# ─────────────────────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────────────────────

bot_status = redis_get("bot:status") or "STOPPED"
col_t, col_s = st.columns([3,1])
with col_t:
    st.markdown("# ⚡ Deriv Bot Dashboard")
    st.markdown(f"*Estratégia: **{estrategia}** | Bot corre no Railway 24/7*")
with col_s:
    if bot_status == "RUNNING":
        st.markdown('<div style="padding:12px 0"><span class="dot-green"></span><b>BOT ONLINE</b></div>', unsafe_allow_html=True)
    elif bot_status == "STOPPED":
        st.markdown('<div style="padding:12px 0"><span class="dot-red"></span><b>BOT PARADO</b></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="padding:12px 0"><span class="dot-yellow"></span><b>AGUARDANDO</b></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  MÉTRICAS
# ─────────────────────────────────────────────────────────────────────────────

stats = redis_get("bot:stats") or {"pnl":0,"trades":0,"wins":0,"losses":0,"winrate":0}

m1,m2,m3,m4,m5 = st.columns(5)
with m1:
    cls = "profit" if stats["pnl"]>=0 else "loss"
    st.markdown(f'<div class="metric-card"><div style="font-size:.75rem;color:#7c9cbf">P&L HOJE</div><div class="{cls}">${stats["pnl"]:.2f}</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card"><div style="font-size:.75rem;color:#7c9cbf">TRADES</div><div class="neutral">{stats["trades"]}</div></div>', unsafe_allow_html=True)
with m3:
    wr = stats["winrate"]
    wc = "profit" if wr>=60 else ("neutral" if wr>=50 else "loss")
    st.markdown(f'<div class="metric-card"><div style="font-size:.75rem;color:#7c9cbf">WIN RATE</div><div class="{wc}">{wr:.1f}%</div></div>', unsafe_allow_html=True)
with m4:
    gp = min(100, stats["pnl"]/daily_goal*100) if stats["pnl"]>0 and daily_goal>0 else 0
    st.markdown(f'<div class="metric-card"><div style="font-size:.75rem;color:#7c9cbf">META ({gp:.0f}%)</div><div class="profit">${daily_goal:.2f}</div></div>', unsafe_allow_html=True)
with m5:
    lv = abs(min(0, stats["pnl"]))
    lc = "loss" if max_loss>0 and lv/max_loss>0.7 else ("neutral" if max_loss>0 and lv/max_loss>0.4 else "profit")
    st.markdown(f'<div class="metric-card"><div style="font-size:.75rem;color:#7c9cbf">STOP LOSS</div><div class="{lc}">${max_loss:.2f}</div></div>', unsafe_allow_html=True)

st.markdown("")

# ─────────────────────────────────────────────────────────────────────────────
#  LAYOUT PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

left, right = st.columns([2,1])

with left:
    st.markdown("### 📊 Histórico de Trades")
    trades = redis_lrange("bot:trades", 0, 19)
    if trades:
        df = pd.DataFrame(trades)
        if "profit" in df.columns:
            df["resultado"] = df["profit"].apply(lambda x: f"✅ +${float(x):.2f}" if float(x)>0 else f"❌ ${float(x):.2f}")
            cols = [c for c in ["time","symbol","direction","stake","resultado","signal"] if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum trade ainda. Clica ▶ Iniciar para começar.")

    cp, cl = st.columns(2)
    with cp:
        pp = min(1.0, max(0,stats["pnl"])/daily_goal) if daily_goal>0 else 0
        pnl_val = max(0, stats["pnl"])
        st.markdown(f"**Meta: {pnl_val:.2f} USD / {daily_goal:.2f} USD**")
        st.progress(pp)
    with cl:
        lp = min(1.0, abs(min(0,stats["pnl"]))/max_loss) if max_loss>0 else 0
        loss_val = abs(min(0, stats["pnl"]))
        st.markdown(f"**Stop: {loss_val:.2f} USD / {max_loss:.2f} USD**")
        st.progress(lp)

with right:
    st.markdown("### 🔍 Sinais ao Vivo")
    signals = redis_lrange("bot:signals", 0, 7)
    if signals:
        for s in signals:
            d   = s.get("dir","WAIT")
            bc  = "signal-box" if d=="CALL" else ("signal-box signal-sell" if d=="PUT" else "signal-box signal-wait")
            ico = "🟢" if d=="CALL" else ("🔴" if d=="PUT" else "🟡")
            st.markdown(f'<div class="{bc}">{ico} <b>{d}</b> &nbsp; {s.get("time","")}<br><span style="color:#7c9cbf">{s.get("reason","")}</span></div>',
                        unsafe_allow_html=True)
    else:
        st.info("Aguardando sinais...")

    st.markdown("### 📋 Log do Railway")
    logs = redis_lrange("bot:logs", 0, 11)
    html = ""
    for e in logs:
        # limpa lista ou string
        if isinstance(e, list): e = e[0] if e else ""
        e = str(e).strip("[]\'\"")
        cor = "#00d4aa" if "✅" in e else ("#ff4d6d" if "❌" in e or "💥" in e else "#7c9cbf")
        html += f'<div style="font-family:JetBrains Mono,monospace;font-size:.74rem;color:{cor};padding:2px 0">{e}</div>'
    st.markdown(f'<div style="background:#111827;border-radius:8px;padding:12px;max-height:260px;overflow-y:auto">{html}</div>',
                unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  AUTO-REFRESH a cada 5 segundos
# ─────────────────────────────────────────────────────────────────────────────

time.sleep(5)
st.rerun()
