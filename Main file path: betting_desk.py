import streamlit as st
import pandas as pd
import math
from collections import defaultdict
from datetime import datetime
from PIL import Image
import pytesseract

# =================================================
# 🧠 CORE MODEL (YOUR ORIGINAL LOGIC - UNCHANGED)
# =================================================

def poisson(xg, k):
    return (xg ** k * math.exp(-xg)) / math.factorial(k)

def calculate_xg(ha, hc, aa, ac):
    return round((ha + ac) / 2, 2), round((aa + hc) / 2, 2)

def apply_match_modifiers(hxg, axg, home_adv=0.15):
    return round(max(hxg + home_adv, 0.1), 2), round(max(axg, 0.1), 2)

def poisson_matrix(hxg, axg, max_goals=5):
    data = []
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson(hxg, h) * poisson(axg, a)
            data.append({"score": f"{h}-{a}", "prob": p})
    return data

def result_probs(matrix):
    h = d = a = 0
    for i in matrix:
        x, y = map(int, i["score"].split("-"))
        if x > y:
            h += i["prob"]
        elif x == y:
            d += i["prob"]
        else:
            a += i["prob"]
    return {
        "home": round(h * 100, 2),
        "draw": round(d * 100, 2),
        "away": round(a * 100, 2)
    }

def implied(odds):
    return (1 / odds) * 100

# =================================================
# 🔵 DESK ENGINE (BETTING LAYER)
# =================================================

def edge(prob, odds):
    return prob - implied(odds)

def kelly(prob, odds):
    b = odds - 1
    p = prob / 100
    q = 1 - p
    if b == 0:
        return 0
    f = (b * p - q) / b
    return max(f, 0)

def stake(kelly_frac, bankroll, risk):
    risk_map = {"LOW": 0.5, "MEDIUM": 0.35, "HIGH": 0.2}
    return round(bankroll * kelly_frac * risk_map[risk], 2)

# =================================================
# 🔴 SIGNAL CLASSIFICATION SYSTEM
# =================================================

def classify_signal(your_edge, desk_edge):
    if your_edge > 2 and desk_edge > 2:
        return "🟢 STRONG AGREEMENT"
    elif your_edge > 0 and desk_edge > 0:
        return "🟡 WEAK AGREEMENT"
    elif your_edge > 0 and desk_edge < 0:
        return "🔴 CONFLICT (AVOID)"
    elif your_edge < 0 and desk_edge > 2:
        return "🟠 DESK OVERRIDE"
    else:
        return "⚪ NO BET"

# =================================================
# 📸 OCR SYSTEM (SCREENSHOT → MATCH DATA)
# =================================================

def extract_text(image):
    return pytesseract.image_to_string(image)

def parse_text(text):
    lines = text.split("\n")
    matches = []

    for line in lines:
        parts = line.split()
        if len(parts) >= 5:
            try:
                matches.append({
                    "home_team": parts[0],
                    "away_team": parts[1],
                    "home_odds": float(parts[-3]),
                    "draw_odds": float(parts[-2]),
                    "away_odds": float(parts[-1]),
                    "home_attack": 1.3,
                    "home_concede": 1.0,
                    "away_attack": 1.2,
                    "away_concede": 1.1
                })
            except:
                continue

    return matches

# =================================================
# 🧠 MAIN ANALYSIS ENGINE
# =================================================

def analyze(row, bankroll, risk):

    odds = {
        "home": float(row["home_odds"]),
        "draw": float(row["draw_odds"]),
        "away": float(row["away_odds"])
    }

    hxg, axg = calculate_xg(
        float(row["home_attack"]),
        float(row["home_concede"]),
        float(row["away_attack"]),
        float(row["away_concede"])
    )

    hxg, axg = apply_match_modifiers(hxg, axg)

    matrix = poisson_matrix(hxg, axg)
    res = result_probs(matrix)

    # 🟡 YOUR MODEL EDGE
    your_edges = {
        "home": edge(res["home"], odds["home"]),
        "draw": edge(res["draw"], odds["draw"]),
        "away": edge(res["away"], odds["away"])
    }

    your_best = max(your_edges, key=your_edges.get)

    # 🔵 DESK MODEL EDGE
    desk_best = max(res, key=lambda x: edge(res[x], odds[x]))
    desk_best_edge = edge(res[desk_best], odds[desk_best])

    # 🔴 SIGNAL
    signal = classify_signal(
        your_edges[your_best],
        desk_best_edge
    )

    # 💰 STAKING
    kelly_frac = kelly(res[desk_best], odds[desk_best])
    stake_value = stake(kelly_frac, bankroll, risk)

    return {
        "match": f"{row['home_team']} vs {row['away_team']}",

        # 🟡 YOUR MODEL
        "your_home": res["home"],
        "your_draw": res["draw"],
        "your_away": res["away"],

        # 🔵 DESK MODEL
        "desk_best": desk_best,
        "desk_edge": round(desk_best_edge, 2),

        # 🟡 YOUR BEST
        "your_best": your_best,
        "your_edge": round(your_edges[your_best], 2),

        # 🔴 SIGNAL
        "signal": signal,

        # 💰 MONEY MANAGEMENT
        "kelly": round(kelly_frac, 4),
        "stake": stake_value
    }

# =================================================
# 💼 STREAMLIT APP
# =================================================

st.set_page_config(page_title="Betting Desk SaaS", layout="wide")

st.title("💼 Betting Desk SaaS — Full Automation Engine")

bankroll = st.number_input("Bankroll", value=1000)
risk = st.selectbox("Risk Level", ["LOW", "MEDIUM", "HIGH"])

# =================================================
# 📸 SCREENSHOT INPUT
# =================================================

st.subheader("📸 Upload Screenshot OR CSV")

img_file = st.file_uploader("Upload Screenshot", type=["png", "jpg", "jpeg"])
csv_file = st.file_uploader("Upload CSV", type=["csv"])

data = []

if img_file:
    image = Image.open(img_file)
    text = extract_text(image)
    data = parse_text(text)
    st.success("Screenshot converted to data")

elif csv_file:
    df = pd.read_csv(csv_file)
    data = df.to_dict(orient="records")

# =================================================
# 📊 PROCESS ENGINE
# =================================================

if data:

    results = []
    for row in data:
        results.append(analyze(row, bankroll, risk))

    df_out = pd.DataFrame(results)

    # 🏆 BEST BETS
    st.subheader("🏆 Best Betting Opportunities")
    best = df_out[df_out["signal"] != "⚪ NO BET"]
    best = best.sort_values("your_edge", ascending=False)

    st.dataframe(best)

    # 📊 FULL ANALYSIS
    st.subheader("📊 Full Analysis")
    st.dataframe(df_out)

    # 💼 SIGNAL GUIDE
    st.subheader("📌 Signal Guide")
    st.write("🟢 Strong = High confidence")
    st.write("🟡 Weak = Small stake")
    st.write("🔴 Conflict = Avoid")
    st.write("🟠 Override = Desk disagrees")
    st.write("⚪ No Bet = Skip")
