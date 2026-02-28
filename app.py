import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# 1. BPL ROYAL THEME CSS
st.set_page_config(page_title="BPL PRO HUB", page_icon="🏀", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    div[data-testid="stToolbar"] {visibility: hidden;} [data-testid="stStatusWidget"] {display: none;}
    .block-container { padding: 0rem !important; margin: 0rem !important; }
    
    /* Royal Blue Gradient Background */
    .stApp { background: radial-gradient(circle at top, #002366 0%, #000000 100%); color: #e0e0e0; }
    
    /* Metric Cards */
    div[data-testid="stMetric"] { 
        background: rgba(0, 35, 102, 0.3) !important; 
        backdrop-filter: blur(10px);
        border: 2px solid #4169E1 !important; 
        border-radius: 15px !important; padding: 15px !important;
    }
    
    /* BPL Header Banner */
    .header-banner { 
        padding: 25px; text-align: center; 
        background: linear-gradient(90deg, #002366 0%, #4169E1 50%, #002366 100%);
        color: white; font-family: 'Impact', sans-serif; font-size: 42px;
        letter-spacing: 3px; border-bottom: 3px solid #ffffff;
    }

    /* Top Tier Selector Styling */
    .stRadio [data-testid="stWidgetLabel"] { display: none; }
    div[data-testid="stHorizontalBlock"] { background: rgba(0,0,0,0.3); padding: 10px; border-radius: 10px; }
    
    /* News Ticker */
    @keyframes ticker { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    .ticker-wrap { width: 100%; overflow: hidden; background: #000; color: #4169E1; padding: 8px 0; border-bottom: 1px solid #1e90ff; }
    .ticker-content { display: inline-block; white-space: nowrap; animation: ticker 45s linear infinite; }
    .ticker-item { display: inline-block; margin-right: 100px; font-weight: bold; font-size: 16px; }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 15px; padding-left: 20px; border-bottom: 1px solid #333; }
    .stTabs [data-baseweb="tab"] { 
        background-color: transparent; 
        color: #888; padding: 10px 25px; font-size: 18px; font-weight: bold;
    }
    .stTabs [aria-selected="true"] { color: #4169E1 !important; border-bottom: 3px solid #4169E1 !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. DATA ENGINE
@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet="https://docs.google.com/spreadsheets/d/1Q5Q7_bk2RyNqJMbrYY5_VzDaPYhlEbQxqXA3BnYFBJU/edit#gid=0", ttl="1m")
        df.columns = df.columns.str.strip()
        
        num_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FGA', 'FGM', '3PM', '3PA', 'Game_ID', 'Win']
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            else:
                df[c] = 0
        
        df['is_ff'] = (df['PTS'] == 0) & (df['FGA'] == 0)
        df['PIE_Raw'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5)
        return df
    except Exception as e:
        return str(e)

full_df = load_data()

# 3. STATS LOGIC
def get_stats(dataframe, group_col):
    if dataframe.empty: return pd.DataFrame()
    played_df = dataframe[dataframe['is_ff'] == False]
    gp = dataframe.groupby(group_col).size().reset_index(name='GP')
    played_gp = played_df.groupby(group_col).size().reset_index(name='Played_GP')
    
    sums = dataframe.groupby(group_col).sum(numeric_only=True).reset_index()
    m = pd.merge(sums, gp, on=group_col)
    m = pd.merge(m, played_gp, on=group_col, how='left').fillna(0)
    
    divisor = m['Played_GP'].replace(0, 1)
    for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'PIE_Raw', '3PM']:
        m[f'{col}/G'] = (m[col] / divisor).round(2)
        
    m['FG%'] = (m['FGM'] / m['FGA'].replace(0, 1) * 100).round(1)
    m['PIE'] = m['PIE_Raw/G']
    return m

# 4. SCOUTING DIALOG
@st.dialog("🏀 BPL SCOUTING REPORT", width="large")
def show_card(name, stats_df):
    row = stats_df.set_index(stats_df.columns[0]).loc[name]
    st.subheader(f"📊 {name}")
    st.divider()
    c = st.columns(4)
    c[0].metric("PPG", row['PTS/G'])
    c[1].metric("RPG", row['REB/G'])
    c[2].metric("APG", row['AST/G'])
    c[3].metric("PIE", row['PIE'])
    if st.button("CLOSE REPORT", use_container_width=True): st.rerun()

# 5. MAIN INTERFACE
if isinstance(full_df, str):
    st.error(f"SYSTEM ERROR: {full_df}")
else:
    # --- TOP HEADER ---
    st.markdown('<div class="header-banner">BPL PRO DATA HUB</div>', unsafe_allow_html=True)
    
    # --- TOP TIER SELECTOR ---
    _, selector_col, _ = st.columns([1, 2, 1])
    with selector_col:
        tier = st.radio(
            "Select Tier", 
            ["HIGH SCHOOL", "COLLEGE", "PRO"], 
            index=2, 
            horizontal=True, 
            label_visibility="collapsed"
        )

    # Filtering Logic based on Game_ID ranges
    if tier == "HIGH SCHOOL":
        df_tier = full_df[full_df['Game_ID'].between(1, 999)]
    elif tier == "COLLEGE":
        df_tier = full_df[full_df['Game_ID'].between(1000, 2999)]
    else:
        df_tier = full_df[full_df['Game_ID'].between(3000, 5000)]

    p_stats = get_stats(df_tier[df_tier['Type'].str.lower() == 'player'], 'Player/Team')
    t_stats = get_stats(df_tier[df_tier['Type'].str.lower() == 'team'], 'Team Name')

    # News Ticker
    if not p_stats.empty:
        leads = [f"🏆 {c}: {p_stats.nlargest(1, f'{c}/G').iloc[0]['Player/Team']} ({p_stats.nlargest(1, f'{c}/G').iloc[0][f'{c}/G']})" for c in ['PTS', 'AST', 'REB']]
        st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)

    # --- MAIN TABS ---
    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS"])

    with tabs[0]:
        if not p_stats.empty:
            p_disp = p_stats[['Player/Team', 'GP', 'PTS/G', 'AST/G', 'REB/G', 'FG%', 'PIE']].sort_values('PIE', ascending=False)
            sel_p = st.dataframe(p_disp, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key=f"p_tab_{tier}")
            if len(sel_p.selection.rows) > 0:
                show_card(p_disp.iloc[sel_p.selection.rows[0]]['Player/Team'], p_stats)
        else:
            st.info(f"No player records for {tier}.")

    with tabs[1]:
        if not t_stats.empty:
            t_stats['Record'] = t_stats['Win'].astype(int).astype(str) + "-" + (t_stats['GP'] - t_stats['Win']).astype(int).astype(str)
            t_disp = t_stats[['Team Name', 'Record', 'PTS/G', 'REB/G', 'AST/G', 'PIE']].sort_values('PIE', ascending=False)
            sel_t = st.dataframe(t_disp, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key=f"t_tab_{tier}")
            if len(sel_t.selection.rows) > 0:
                show_card(t_disp.iloc[sel_t.selection.rows[0]]['Team Name'], t_stats)
        else:
            st.info(f"No team records for {tier}.")

    with tabs[2]:
        if not p_stats.empty:
            l_cat = st.selectbox("STAT CATEGORY", ["PTS/G", "REB/G", "AST/G", "3PM/G", "PIE"])
            t10 = p_stats.nlargest(10, l_cat)
            st.plotly_chart(px.bar(t10, x=l_cat, y='Player/Team', orientation='h', template="plotly_dark", color_discrete_sequence=['#4169E1']), use_container_width=True)

    with tabs[3]:
        if not p_stats.empty and len(p_stats) >= 2:
            v1, v2 = st.columns(2)
            s1 = v1.selectbox("P1", p_stats['Player/Team'], index=0)
            s2 = v2.selectbox("P2", p_stats['Player/Team'], index=1)
            d1, d2 = p_stats[p_stats['Player/Team'] == s1].iloc[0], p_stats[p_stats['Player/Team'] == s2].iloc[0]
            for m in ['PTS/G', 'AST/G', 'REB/G', 'PIE']:
                val1, val2 = d1[m], d2[m]
                c1, mid, c2 = st.columns([2,1,2])
                c1.metric(s1, val1, round(val1-val2, 2))
                mid.markdown(f"<div style='text-align:center; padding-top:10px; color:#4169E1;'>{m}</div>", unsafe_allow_html=True)
                c2.metric(s2, val2, round(val2-val1, 2))

    st.markdown(f'<div style="text-align: center; color: #555; padding: 25px;">© 2026 BPL PRO | {tier} DIV</div>', unsafe_allow_html=True)
