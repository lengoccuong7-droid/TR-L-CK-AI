import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import hashlib
import sqlite3
import datetime

from config import APP_NAME, APP_VERSION, DB_PATH
from modules.indicators import add_indicators
from modules.technical_analysis import evaluate_technical
from modules.money_flow import evaluate_money_flow
from modules.support_resistance import find_support_resistance
from modules.stock_scoring import score_description
from modules.ai_analyzer import run_ai_analysis
from modules.decision_engine import make_trading_decision
from modules.database import save_analysis, get_recent_history

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH GIAO DIỆN & KHỞI TẠO CƠ SỞ DỮ LIỆU CHUẨN (USERS & HISTORY)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title=f"{APP_NAME} ULTIMATE PRO", 
    layout="wide", 
    page_icon="📈",
    initial_sidebar_state="expanded"
)

# Hàm khởi tạo database chuẩn bảo mật đa người dùng
def init_system_db():
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        cursor = conn.cursor()
        # Bảng lịch sử phân tích
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                timestamp TEXT,
                last_close REAL,
                score INTEGER,
                decision TEXT,
                buy_zone TEXT,
                target_price TEXT,
                stop_loss TEXT,
                summary TEXT
            )
        ''')
        
        # Bảng quản lý người dùng & phân quyền (Admin / User)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT,
                role TEXT,
                recovery_code TEXT
            )
        ''')
        
        # Tạo sẵn tài khoản Admin mặc định (Pass: 123456, Mã khôi phục: admin)
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            admin_pass_hash = hashlib.sha256(str.encode("123456")).hexdigest()
            cursor.execute("INSERT INTO users (username, password_hash, role, recovery_code) VALUES (?, ?, ?, ?)", 
                           ("admin", admin_pass_hash, "admin", "admin"))
        conn.commit()

init_system_db()

if "logged_in_user" not in st.session_state:
    st.session_state["logged_in_user"] = None
if "user_role" not in st.session_state:
    st.session_state["user_role"] = "user"

def init_user_data(username):
    if f"portfolio_{username}" not in st.session_state:
        st.session_state[f"portfolio_{username}"] = pd.DataFrame([
            {"Mã": "HPG", "Khối Lượng": 10000, "Giá Vốn": 25.0, "Giá Hiện Tại": 27.5},
            {"Mã": "FPT", "Khối Lượng": 5000, "Giá Vốn": 49.5, "Giá Hiện Tại": 51.0}
        ])

# -----------------------------------------------------------------------------
# 2. XÁC THỰC ĐĂNG NHẬP / ĐĂNG KÝ & QUÊN MẬT KHẨU (LƯU TRỰC TIẾP VÀO SQLITE)
# -----------------------------------------------------------------------------
if st.session_state["logged_in_user"] is None:
    st.title(f"📈 {APP_NAME} (v{APP_VERSION} ULTIMATE PRO)")
    st.caption("Hệ thống Trợ lý Phân tích Chứng khoán Thực chiến - Đăng nhập bảo mật đa người dùng")
    
    tab_login, tab_reg, tab_forgot = st.tabs(["🔑 Đăng Nhập", "📝 Đăng Ký Tài Khoản", "🔄 Quên Mật Khẩu"])
    
    # 1. Tab Đăng nhập
    with tab_login:
        l_user = st.text_input("Tên tài khoản", key="l_u").strip()
        l_pass = st.text_input("Mật khẩu", type="password", key="l_p")
        if st.button("🚀 Đăng Nhập Hệ Thống", use_container_width=True):
            if not l_user or not l_pass:
                st.warning("⚠️ Vui lòng nhập đầy đủ tên tài khoản và mật khẩu!")
            else:
                pass_hash = hashlib.sha256(str.encode(l_pass)).hexdigest()
                try:
                    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT role, password_hash FROM users WHERE username = ?", (l_user,))
                        user_row = cursor.fetchone()
                        
                    if user_row and user_row[1] == pass_hash:
                        st.session_state["logged_in_user"] = l_user
                        st.session_state["user_role"] = user_row[0]
                        init_user_data(l_user)
                        st.success(f"🎉 Chào mừng sếp {l_user} trở lại!")
                        st.rerun()
                    else:
                        st.error("❌ Sai tên đăng nhập hoặc mật khẩu!")
                except Exception as e:
                    st.error(f"Lỗi kết nối cơ sở dữ liệu: {e}")

    # 2. Tab Đăng ký tài khoản cho khách
    with tab_reg:
        r_user = st.text_input("Chọn tên đăng ký", key="r_u").strip()
        r_pass = st.text_input("Tạo mật khẩu", type="password", key="r_p")
        r_pass_c = st.text_input("Xác nhận mật khẩu", type="password", key="r_pc")
        r_code = st.text_input("Mã khôi phục bí mật (Dùng khi quên mật khẩu):", type="password", key="r_c")
        
        if st.button("✨ Đăng Ký Tài Khoản Mới", use_container_width=True):
            if not r_user or not r_pass or not r_code:
                st.warning("⚠️ Vui lòng điền đầy đủ tất cả các thông tin!")
            elif r_pass != r_pass_c:
                st.error("❌ Mật khẩu xác nhận không khớp!")
            else:
                try:
                    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (r_user,))
                        if cursor.fetchone()[0] > 0:
                            st.error("❌ Tên tài khoản này đã tồn tại, vui lòng chọn tên khác!")
                        else:
                            new_pass_hash = hashlib.sha256(str.encode(r_pass)).hexdigest()
                            cursor.execute("INSERT INTO users (username, password_hash, role, recovery_code) VALUES (?, ?, ?, ?)",
                                           (r_user, new_pass_hash, "user", r_code))
                            conn.commit()
                            st.success("✅ Đăng ký thành công! Vui lòng chuyển sang tab Đăng Nhập để vào hệ thống.")
                except Exception as e:
                    st.error(f"Lỗi đăng ký: {e}")

    # 3. Tab Quên mật khẩu / Lấy lại mật khẩu
    with tab_forgot:
        st.info("💡 Nhập tên tài khoản và mã khôi phục bí mật đã đăng ký để đặt lại mật khẩu mới.")
        f_user = st.text_input("Tên tài khoản cần lấy lại mật khẩu", key="f_u").strip()
        f_code = st.text_input("Mã khôi phục bí mật", type="password", key="f_c")
        f_new_pass = st.text_input("Mật khẩu mới", type="password", key="f_np")
        
        if st.button("🔄 Đặt Lại Mật Khẩu Mới", use_container_width=True):
            if not f_user or not f_code or not f_new_pass:
                st.warning("⚠️ Vui lòng điền đầy đủ thông tin!")
            else:
                try:
                    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT recovery_code FROM users WHERE username = ?", (f_user,))
                        row = cursor.fetchone()
                        
                    if row and row[0] == f_code:
                        new_hash = hashlib.sha256(str.encode(f_new_pass)).hexdigest()
                        with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, f_user))
                            conn.commit()
                        st.success("✅ Đặt lại mật khẩu thành công! Hãy sang tab Đăng Nhập để truy cập.")
                    else:
                        st.error("❌ Tên tài khoản hoặc Mã khôi phục không chính xác!")
                except Exception as e:
                    st.error(f"Lỗi khôi phục: {e}")
                    
    st.stop()

# -----------------------------------------------------------------------------
# 3. GIAO DIỆN CHÍNH SAU KHI ĐĂNG NHẬP
# -----------------------------------------------------------------------------
current_user = st.session_state["logged_in_user"]
init_user_data(current_user)
user_portfolio = st.session_state[f"portfolio_{current_user}"]

h_col1, h_col2 = st.columns([4, 1])
with h_col1:
    st.title(f"📈 {APP_NAME} (v{APP_VERSION} ULTIMATE PRO)")
    st.caption(f"Tài khoản đang hoạt động: **{current_user}** ({'Admin' if st.session_state.get('user_role')=='admin' else 'Khách'}) | Mô hình Cố vấn Thực chiến")
with h_col2:
    if st.button("🚪 Đăng Xuất", use_container_width=True):
        st.session_state["logged_in_user"] = None
        st.rerun()

# -----------------------------------------------------------------------------
# SIDEBAR: CỔNG NẠP DỮ LIỆU FILE & XỬ LÝ THÔNG MINH
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ 1. Nguồn Dữ Liệu Lịch Sử")
uploaded_file = st.sidebar.file_uploader("Nạp tệp CSV hoặc Excel (Lần cuối, KL, % Thay đổi...)", type=["csv", "xlsx", "xls"])

df_raw = None
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df_raw = pd.read_excel(uploaded_file, engine='openpyxl')
            
        df_raw.columns = [str(c).strip().lower() for c in df_raw.columns]
        
        rename_dict = {
            "ngày": "date", "thời gian": "date", "ngay": "date",
            "lần cuối": "close", "lan cuoi": "close",
            "mở": "open", "mo": "open", "giá mở": "open", "o": "open",
            "cao": "high", "giá cao": "high", "h": "high",
            "thấp": "low", "giá thấp": "low", "l": "low",
            "đóng": "close", "dong": "close", "giá đóng": "close", "c": "close",
            "khối lượng": "volume", "khoi luong": "volume", "kl": "volume", "v": "volume",
            "% thay đổi": "pct_change", "thay đổi": "pct_change", "thay doi": "pct_change"
        }
        df_raw = df_raw.rename(columns=rename_dict)
        
        for col in ["open", "high", "low", "close"]:
            if col in df_raw.columns:
                if df_raw[col].dtype == object:
                    df_raw[col] = df_raw[col].astype(str).str.replace(",", "").str.strip()
                df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce")
                
        if "volume" in df_raw.columns:
            def parse_volume(val):
                if pd.isna(val): return 0.0
                val_str = str(val).replace(",", "").strip().upper()
                if 'M' in val_str:
                    return float(val_str.replace('M', '')) * 1_000_000
                elif 'K' in val_str:
                    return float(val_str.replace('K', '')) * 1_000
                try:
                    return float(val_str)
                except:
                    return 0.0
            df_raw["volume"] = df_raw["volume"].apply(parse_volume)

        if "pct_change" in df_raw.columns:
            def parse_pct(val):
                if pd.isna(val): return 0.0
                val_str = str(val).replace("%", "").replace("+", "").replace(",", ".").strip()
                try:
                    return float(val_str)
                except:
                    return 0.0
            df_raw["pct_change"] = df_raw["pct_change"].apply(parse_pct)
            
        if "date" in df_raw.columns:
            if pd.api.types.is_numeric_dtype(df_raw["date"]):
                df_raw["date"] = pd.to_datetime(df_raw["date"], unit='D', origin='1899-12-30')
            else:
                df_raw["date"] = pd.to_datetime(df_raw["date"], errors="coerce", dayfirst=True)
            
            df_raw = df_raw.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
            
    except Exception as e:
        st.sidebar.error(f"Lỗi đọc tệp: {e}")

symbol_input = st.sidebar.text_input("Mã cổ phiếu phân tích", value="FPT").upper()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 2. Cập Nhật Giá Đầu Phiên (ATO)")
col_a1, col_a2 = st.sidebar.columns(2)
with col_a1: ato_open_in = st.text_input("Giá ATO", value="")
with col_a2: ato_vol_in = st.text_input("KL ATO", value="")

ato_data = {"open": None, "volume": None}
if ato_open_in.strip():
    try: ato_data["open"] = float(ato_open_in.replace(",", "").strip())
    except: pass
if ato_vol_in.strip():
    try: ato_data["volume"] = float(ato_vol_in.replace(",", "").strip())
    except: pass

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 3. Báo Cáo Tài Chính Cơ Bản")
fin_roe = st.sidebar.text_input("ROE (%)", value="")
fin_pe = st.sidebar.text_input("P/E", value="")
fin_debt = st.sidebar.text_input("Nợ/VCSH", value="")

financial_metrics = {"roe": None, "pe": None, "debt_equity": None}
if fin_roe.strip():
    try: financial_metrics["roe"] = float(fin_roe.strip())
    except: pass
if fin_pe.strip():
    try: financial_metrics["pe"] = float(fin_pe.strip())
    except: pass
if fin_debt.strip():
    try: financial_metrics["debt_equity"] = float(fin_debt.strip())
    except: pass

# -----------------------------------------------------------------------------
# GIAO DIỆN CHÍNH: 4 TABS THỰC CHIẾN
# -----------------------------------------------------------------------------
main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
    "📊 TAB 1: KỸ THUẬT & TÀI CHÍNH", 
    "🗣️ TAB 2: KỊCH BẢN THẦY - TRÒ",
    "💼 TAB 3: QUẢN TRỊ VỐN & NAV",
    "📜 TAB 4: LỊCH SỬ & QUẢN LÝ MÃ"
])

# --- TAB 1: KỸ THUẬT & TÀI CHÍNH ---
with main_tab1:
    if df_raw is None or df_raw.empty:
        st.warning("⚠️ CHƯA CÓ DỮ LIỆU LỊCH SỬ: Vui lòng tải tệp CSV/Excel từ bảng giá ở thanh bên trái để tiến hành phân tích.")
        st.info("💡 Hướng dẫn: Tải file dữ liệu lịch sử của mã cổ phiếu vào mục tải tệp ở sidebar.")
    else:
        try:
            df = add_indicators(df_raw)
            ai_res = run_ai_analysis(df, symbol_input, ato_data=ato_data, financial_metrics=financial_metrics)
            decision_res = make_trading_decision(df, ai_res)
            tech_res = evaluate_technical(df)
            sr_res = find_support_resistance(df)

            st.subheader(f"🎯 TÍN HIỆU & VÙNG GIAO DỊCH MÃ {symbol_input}")
            
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("QUYẾT ĐỊNH", decision_res["decision"])
            m2.metric("VÙNG MUA CHUẨN", decision_res["buy_zone"])
            m3.metric("GIÁ XÁC NHẬN", decision_res["confirm_price"])
            m4.metric("CHỐT LỜI (TP)", decision_res["target_price"])
            m5.metric("CẮT LỖ (SL)", decision_res["stop_loss"])

            st.markdown("---")
            col_save1, col_save2 = st.columns([3, 1])
            with col_save1:
                st.info(f"💡 Sếp có thể bấm nút bên phải để lưu kết quả phân tích mã **{symbol_input}** này vào Nhật ký (Tab 4).")
            with col_save2:
                if st.button("💾 Lưu Phân Tích Này", use_container_width=True, type="primary"):
                    try:
                        save_analysis(
                            symbol=symbol_input,
                            last_close=float(df['close'].iloc[-1]),
                            score=int(tech_res['score']),
                            decision=decision_res['decision'],
                            buy_zone=decision_res['buy_zone'],
                            target_price=decision_res['target_price'],
                            stop_loss=decision_res['stop_loss'],
                            summary=ai_res['summary']
                        )
                        st.success("Đã lưu thành công vào Nhật ký!")
                    except Exception as e:
                        st.error(f"Lỗi khi lưu: {e}")

            sub_t1, sub_t2, sub_t3 = st.tabs(["📈 Biểu Đồ Kỹ Thuật", "🔍 AI Phản Biện & Tài Chính", "📋 Chi Tiết Chỉ Báo"])
            
            with sub_t1:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Giá'), row=1, col=1)
                if 'MA20' in df.columns: fig.add_trace(go.Scatter(x=df['date'], y=df['MA20'], name='MA20', line=dict(color='orange', width=1)), row=1, col=1)
                if 'MA50' in df.columns: fig.add_trace(go.Scatter(x=df['date'], y=df['MA50'], name='MA50', line=dict(color='blue', width=1)), row=1, col=1)
                colors = ['green' if df['close'].iloc[i] >= df['open'].iloc[i] else 'red' for i in range(len(df))]
                fig.add_trace(go.Bar(x=df['date'], y=df['volume'], name='Khối lượng', marker_color=colors), row=2, col=1)
                fig.update_layout(title=f"Biểu đồ kỹ thuật mã {symbol_input}", xaxis_rangeslider_visible=False, height=480)
                st.plotly_chart(fig, use_container_width=True)

            with sub_t2:
                st.subheader("🔍 Sức Khỏe Tài Chính & Phản Biện Rủi Ro")
                st.info(f"**Chỉ số tài chính cơ bản:** {ai_res['fin_summary']}")
                st.markdown("**Các điểm phản biện & Cảnh báo bẫy giá từ AI:**")
                for arg in ai_res["counter_arguments"]:
                    st.warning(arg)

            with sub_t3:
                st.subheader(f"📄 Thông Số Kỹ Thuật Chi Tiết Mã {symbol_input}")
                st.write(f"- **Điểm số kỹ thuật:** {tech_res['score']} điểm ({score_description(tech_res['score'])})")
                st.write(f"- **Trạng thái dòng tiền:** {ai_res['flow_summary']}")
                st.write(f"- **Khoảng cách tới hỗ trợ:** {sr_res['dist_to_support_pct']}% (Ngưỡng hỗ trợ: {sr_res['support']})")
                st.write(f"- **Khoảng cách tới kháng cự:** {sr_res['dist_to_resistance_pct']}% (Ngưỡng kháng cự: {sr_res['resistance']})")

        except Exception as e:
            st.error(f"⚠️ Lỗi khi xử lý tính toán kỹ thuật hoặc AI: {e}")
            st.info("💡 Vui lòng kiểm tra lại tệp dữ liệu nạp vào xem có đủ các cột Giá và Khối lượng hay không.")

# --- TAB 2: KỊCH BẢN THẦY - TRÒ ---
with main_tab2:
    st.subheader(f"🗣️ KỊCH BẢN LỜI KHUYÊN TỪ CHUYÊN GIA CHO MÃ {symbol_input}")
    
    if df_raw is None or df_raw.empty:
        st.warning("⚠️ Vui lòng nạp tệp dữ liệu ở thanh bên trái để Thầy có cơ sở phân tích và đưa ra lời khuyên chiến lược.")
    else:
        try:
            df = add_indicators(df_raw)
            ai_res = run_ai_analysis(df, symbol_input, ato_data=ato_data, financial_metrics=financial_metrics)
            decision_res = make_trading_decision(df, ai_res)

            st.markdown(f"""
            <div style="background-color: #1e293b; color: #f8fafc; padding: 1.8rem; border-radius: 12px; border-left: 6px solid #3b82f6; margin-top: 1rem;">
                <div style="font-weight: bold; font-size: 1.3rem; color: #60a5fa; margin-bottom: 1rem;">🎯 LỜI THẦY DẶN TRÒ (GÓC NHÌN CHUYÊN GIA THỰC CHIẾN)</div>
                <div style="line-height: 1.8; font-size: 1.05rem;">
                    "Trò chú ý! Đối với mã <b>{symbol_input}</b>, hệ thống xác nhận trạng thái là: <b style="color: #38bdf8;">{decision_res['decision']}</b>.<br/><br/>
                    <b>1. Đánh giá tổng quan cốt lõi:</b> {ai_res['summary']}<br/><br/>
                    <b>2. Chiến lược hành động chi tiết:</b><br/>
                    &nbsp;&nbsp;&nbsp;&nbsp;🎯 <b>Dành cho TRÒ CHƯA CÓ HÀNG:</b><br/>
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- Tuyệt đối không mua đuổi hưng phấn khi giá xanh mạnh.<br/>
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- Kiên nhẫn chờ nhịp chỉnh về đúng vùng mua chuẩn <code style="color: #facc15; font-size: 1.1rem;">{decision_res['buy_zone']}</code> để lấy vị thế thăm dò 30-50%.<br/><br/>
                    &nbsp;&nbsp;&nbsp;&nbsp;🛡️ <b>Dành cho TRÒ ĐÃ CÓ HÀNG:</b><br/>
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- Tiếp tục nắm giữ gồng lãi theo xu hướng nếu dòng tiền khỏe.<br/>
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- Canh chốt lời từng phần khi tiến sát mục tiêu <code style="color: #facc15; font-size: 1.1rem;">{decision_res['target_price']}</code>.<br/>
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- Tuân thủ tuyệt đối kỷ luật cắt lỗ hạ tỷ trọng ngay lập tức nếu thủng vùng <code style="color: #f87171; font-size: 1.1rem;">{decision_res['stop_loss']}</code>!"
                </div>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"⚠️ Lỗi hiển thị kịch bản Thầy - Trò: {e}")

# --- TAB 3: QUẢN TRỊ VỐN & NAV ---
with main_tab3:
    st.subheader(f"💼 QUẢN TRỊ VỐN & DÒNG TIỀN TƯƠNG TÁC ({current_user})")
    st.caption("👇 Trò có thể thêm bớt mã, chỉnh sửa khối lượng, giá vốn trực tiếp trên bảng bên dưới như Excel:")
    
    edited_portfolio = st.data_editor(user_portfolio, num_rows="dynamic", key="pf_editor_main", use_container_width=True)
    
    if st.button("⚡ Lưu & Cập Nhật Dòng Tiền Danh Mục", use_container_width=True):
        st.session_state[f"portfolio_{current_user}"] = edited_portfolio
        st.success("Đã cập nhật danh mục vốn và dòng tiền thành công!")
        st.rerun()

    if not edited_portfolio.empty:
        pf = edited_portfolio.copy()
        pf["Khối Lượng"] = pd.to_numeric(pf["Khối Lượng"], errors="coerce").fillna(0)
        pf["Giá Vốn"] = pd.to_numeric(pf["Giá Vốn"], errors="coerce").fillna(0)
        pf["Giá Hiện Tại"] = pd.to_numeric(pf["Giá Hiện Tại"], errors="coerce").fillna(0)
        
        pf["Giá Trị Hiện Tại"] = pf["Khối Lượng"] * pf["Giá Hiện Tại"]
        pf["Vốn Gốc"] = pf["Khối Lượng"] * pf["Giá Vốn"]
        pf["Lãi/Lỗ (VNĐ)"] = pf["Giá Trị Hiện Tại"] - pf["Vốn Gốc"]
        pf["Lãi/Lỗ (%)"] = np.where(pf["Vốn Gốc"] > 0, (pf["Lãi/Lỗ (VNĐ)"] / pf["Vốn Gốc"]) * 100, 0)
        
        total_nav = pf["Giá Trị Hiện Tại"].sum()
        total_cost = pf["Vốn Gốc"].sum()
        total_pnl = pf["Lãi/Lỗ (VNĐ)"].sum()
        total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0
        
        st.markdown("---")
        v1, v2, v3, v4 = st.columns(4)
        v1.metric("Tổng Vốn Gốc", f"{total_cost:,.0f} VNĐ")
        v2.metric("Tổng NAV Hiện Tại", f"{total_nav:,.0f} VNĐ")
        v3.metric("Tổng Lãi/Lỗ Thực Tế", f"{total_pnl:,.0f} VNĐ", f"{total_pnl_pct:.2f}%")
        v4.metric("Trạng Thái Dòng Tiền", "Đang Sinh Lời" if total_pnl >= 0 else "Đang Âm Vốn")

        st.markdown("---")
        st.dataframe(pf.style.format({
            "Giá Vốn": "{:,.2f}", "Giá Hiện Tại": "{:,.2f}",
            "Vốn Gốc": "{:,.0f}", "Giá Trị Hiện Tại": "{:,.0f}",
            "Lãi/Lỗ (VNĐ)": "{:,.0f}", "Lãi/Lỗ (%)": "{:.2f}%"
        }), use_container_width=True)

# --- TAB 4: LỊCH SỬ & QUẢN LÝ MÃ (GỌN GÀNG & XÓA TOÀN BỘ) ---
with main_tab4:
    st.subheader("📜 Nhật Ký & Quản Lý Lịch Sử Phân Tích")
    st.caption("Tra cứu lại toàn bộ lịch sử phân tích đã lưu trong hệ thống:")
    
    filter_symbol = st.text_input("🔍 Lọc theo mã cổ phiếu (Để trống nếu xem tất cả):", value="").upper()
    
    history_list = []
    try:
        with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    timestamp TEXT,
                    last_close REAL,
                    score INTEGER,
                    decision TEXT,
                    buy_zone TEXT,
                    target_price TEXT,
                    stop_loss TEXT,
                    summary TEXT
                )
            ''')
            
            cursor.execute("PRAGMA table_info(analysis_history)")
            cols = [col[1] for col in cursor.fetchall()]
            
            time_col = "timestamp" if "timestamp" in cols else ("date" if "date" in cols else (cols[2] if len(cols) > 2 else "id"))
            sym_col = "symbol" if "symbol" in cols else (cols[1] if len(cols) > 1 else "id")
            close_col = "last_close" if "last_close" in cols else ("close" if "close" in cols else (cols[3] if len(cols) > 3 else "0"))
            dec_col = "decision" if "decision" in cols else "N/A"
            buy_col = "buy_zone" if "buy_zone" in cols else "N/A"
            tp_col = "target_price" if "target_price" in cols else "N/A"
            sl_col = "stop_loss" if "stop_loss" in cols else "N/A"
            
            if filter_symbol:
                query = f"SELECT id, {sym_col}, {time_col}, {close_col}, {dec_col}, {buy_col}, {tp_col}, {sl_col} FROM analysis_history WHERE {sym_col} = ? ORDER BY id DESC LIMIT 100"
                cursor.execute(query, (filter_symbol,))
            else:
                query = f"SELECT id, {sym_col}, {time_col}, {close_col}, {dec_col}, {buy_col}, {tp_col}, {sl_col} FROM analysis_history ORDER BY id DESC LIMIT 100"
                cursor.execute(query)
            history_list = cursor.fetchall()
    except Exception as e:
        st.error(f"Lỗi cơ sở dữ liệu: {e}")
    
    if history_list:
        col_top1, col_top2 = st.columns([2, 2])
        with col_top1:
            st.info(f"Tìm thấy **{len(history_list)}** bản ghi trong nhật ký.")
        with col_top2:
            if st.button("🔥 XÓA TOÀN BỘ LỊCH SỬ", use_container_width=True, type="primary"):
                with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
                    conn.execute("DELETE FROM analysis_history")
                    conn.commit()
                st.success("Đã xóa sạch toàn bộ lịch sử phân tích trong hệ thống!")
                st.rerun()
                
        st.markdown("---")
        
        cleaned_history = []
        for row in history_list:
            r_id = row[0]
            r_symbol = row[1] if len(row) > 1 else "N/A"
            r_time = row[2] if len(row) > 2 else "N/A"
            try:
                r_close = float(row[3]) if len(row) > 3 and row[3] is not None else 0.0
            except:
                r_close = 0.0
            r_decision = row[4] if len(row) > 4 else "N/A"
            r_buy = row[5] if len(row) > 5 else "N/A"
            r_tp = row[6] if len(row) > 6 else "N/A"
            r_sl = row[7] if len(row) > 7 else "N/A"
            
            cleaned_history.append({
                "ID": r_id,
                "Mã": r_symbol,
                "Thời Gian": r_time,
                "Giá Đóng": r_close,
                "Quyết Định": r_decision,
                "Vùng Mua": r_buy,
                "Chốt Lời": r_tp,
                "Cắt Lỗ": r_sl
            })

        hist_df = pd.DataFrame(cleaned_history)
        st.dataframe(hist_df, hide_index=True, use_container_width=True)
        
    else:
        st.info("Chưa có lịch sử phân tích nào được ghi nhận. Sếp hãy sang Tab 1 bấm nút 'Lưu Phân Tích Này' để ghi dữ liệu mới nhé!")
