import streamlit as st
import random
import re
import json
import os
from mendeleev import element
import pubchempy as pcp
from rdkit import Chem
from rdkit.Chem import Draw
from rdkit.Chem import AllChem
from chempy import balance_stoichiometry

# --- CẤU HÌNH GIAO DIỆN & STYLE ---
st.set_page_config(page_title="ChemAssist Elite", layout="wide")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .element-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 30px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
        margin-bottom: 25px;
    }
    .equation-box {
        background: #1e293b;
        color: #38bdf8;
        padding: 25px;
        border-radius: 15px;
        font-family: 'Courier New', monospace;
        font-size: 28px;
        text-align: center;
        box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
        margin: 20px 0;
    }
    .stButton>button {
        border-radius: 12px;
        height: 3em;
        transition: all 0.3s;
        border: none;
        background: linear-gradient(45deg, #007bff, #00d4ff);
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- QUẢN LÝ NGƯỜI DÙNG ---
USER_DB = "chem_users.json"


def load_db(): return json.load(open(USER_DB)) if os.path.exists(USER_DB) else {}


def save_db(data): json.dump(data, open(USER_DB, "w"))


if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'score' not in st.session_state: st.session_state.score = 0

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3655/3655580.png", width=100)
    st.title("User Portal")
    db = load_db()
    if not st.session_state.logged_in:
        mode = st.radio("Thao tác", ["Đăng nhập", "Đăng ký"])
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Xác nhận"):
            if mode == "Đăng ký":
                if u in db:
                    st.error("Tên đã tồn tại!")
                else:
                    db[u] = {"p": p, "s": 0}; save_db(db); st.success("Đã tạo tài khoản!")
            else:
                if u in db and db[u]["p"] == p:
                    st.session_state.logged_in = True;
                    st.session_state.user = u;
                    st.session_state.score = db[u]["s"];
                    st.rerun()
                else:
                    st.error("Sai tài khoản!")
    else:
        st.markdown(f"### Chào, **{st.session_state.user}** 👋")
        st.metric("Điểm tích lũy", st.session_state.score)
        if st.button("Đăng xuất"):
            db[st.session_state.user]["s"] = st.session_state.score;
            save_db(db);
            st.session_state.logged_in = False;
            st.rerun()


def add_points(n):
    st.session_state.score += n
    if st.session_state.logged_in:
        db = load_db();
        db[st.session_state.user]["s"] = st.session_state.score;
        save_db(db)


# --- NỘI DUNG CHÍNH ---
st.title("🧪 ChemAssist Elite")
tabs = st.tabs(["🔍 Tra cứu", "🏗️ Vẽ cấu tạo", "📝 Luyện tập E", "⚡ Cân bằng", "🎯 Bài tập Oxh-Khử"])

# --- TAB 1: TRA CỨU ---
with tabs[0]:
    sym = st.text_input("Nhập nguyên tố:", "Au").strip().capitalize()
    if sym:
        try:
            el = element(sym)
            en = f"{el.electronegativity:.2f}" if isinstance(el.electronegativity, float) else "N/A"
            st.markdown(f"""<div class="element-card"><h1 style='color: #1e40af;'>{el.name} ({el.symbol})</h1>
                <p>Số hiệu Z: <b>{el.atomic_number}</b> | Cấu hình: <b>{el.ec}</b></p>
                <p>Độ âm điện: <b>{en}</b> | E hóa trị: <b>{el.nvalence()}</b> | NTK: <b>{el.atomic_weight:.2f}</b></p></div>""",
                        unsafe_allow_html=True)
        except:
            st.error("Lỗi dữ liệu!")

# --- TAB 2: VẼ CẤU TẠO ---
with tabs[1]:
    query = st.text_input("Công thức phân tử:", "CH4")
    if query:
        res = pcp.get_compounds(query, 'name') or pcp.get_compounds(query, 'formula')
        if res:
            mol = Chem.MolFromSmiles(res[0].canonical_smiles)
            mol = Chem.AddHs(mol);
            AllChem.Compute2DCoords(mol)
            for atom in mol.GetAtoms(): atom.SetProp("atomLabel", atom.GetSymbol())
            d = Draw.MolDraw2DCairo(500, 400);
            d.drawOptions().bondLineWidth = 5;
            d.drawOptions().minFontSize = 26
            d.DrawMolecule(mol);
            d.FinishDrawing();
            st.image(d.GetDrawingText())

# --- TAB 3: LUYỆN TẬP E (ĐÃ KHÔI PHỤC) ---
with tabs[2]:
    st.header("📝 Thử thách Cấu hình Electron")
    if 'q_e' not in st.session_state or st.button("Câu hỏi E mới 🔄"):
        z_random = random.randint(1, 20)
        el_target = element(z_random)
        st.session_state.q_e = {"q": f"Cấu hình electron `{el_target.ec}` là của nguyên tố nào?", "a": el_target.symbol}

    st.info(st.session_state.q_e['q'])
    ans_e = st.text_input("Nhập kí hiệu (VD: Fe, Mg):", key="input_e").strip()
    if st.button("Kiểm tra E"):
        if ans_e.lower() == st.session_state.q_e['a'].lower():
            st.success("🎉 Chính xác! +10 điểm");
            add_points(10);
            st.balloons()
        else:
            st.error("Sai rồi, hãy thử lại nhé!")

# --- TAB 4: CÂN BẰNG ---
with tabs[3]:
    c1, c2 = st.columns(2)
    with c1:
        r_in = st.text_input("Tham gia:", "Fe + H2SO4")
    with c2:
        p_in = st.text_input("Sản phẩm:", "Fe2(SO4)3 + SO2 + H2O")
    if st.button("Cân bằng"):
        try:
            reac, prod = balance_stoichiometry(set(r_in.split(" + ")), set(p_in.split(" + ")))
            r_t = " + ".join([f"{v if v > 1 else ''}{k}" for k, v in reac.items()])
            p_t = " + ".join([f"{v if v > 1 else ''}{k}" for k, v in prod.items()])
            st.markdown(f'<div class="equation-box">{r_t} &rarr; {p_t}</div>', unsafe_allow_html=True)
        except:
            st.error("Kiểm tra lại công thức!")

# --- TAB 5: BÀI TẬP OXH-KHỬ ---
with tabs[4]:
    redo_list = [
        {"pt": "2Mg + O2 -> 2MgO", "h": "Chất khử?", "a": "Mg"},
        {"pt": "Fe + CuSO4 -> FeSO4 + Cu", "h": "Bị oxi hóa?", "a": "Fe"},
        {"pt": "Zn + H2SO4 -> ZnSO4 + H2", "h": "H từ +1 xuống mấy?", "a": "0"},
        {"pt": "4Al + 3O2 -> 2Al2O3", "h": "Chất oxi hóa?", "a": "O2"},
        {"pt": "MnO2 + 4HCl -> MnCl2 + Cl2 + 2H2O", "h": "Mn từ +4 xuống mấy?", "a": "+2"},
        {"pt": "2FeCl2 + Cl2 -> 2FeCl3", "h": "Chất khử?", "a": "FeCl2"},
        {"pt": "Cu + 2H2SO4 -> CuSO4 + SO2 + 2H2O", "h": "S từ +6 xuống?", "a": "+4"},
        {"pt": "H2S + 4Cl2 + 4H2O -> H2SO4 + 8HCl", "h": "Chất khử?", "a": "H2S"},
        {"pt": "2KMnO4 + 16HCl -> 2KCl + 2MnCl2 + 5Cl2 + 8H2O", "h": "Clo đóng vai trò gì?", "a": "Chất khử"},
        {"pt": "NH3 + 5O2 -> 4NO + 6H2O", "h": "N từ -3 lên?", "a": "+2"},
        {"pt": "2NO2 + 2NaOH -> NaNO3 + NaNO2 + H2O", "h": "NO2 là chất gì?", "a": "Vừa oxi hóa vừa khử"},
        {"pt": "Fe3O4 + 4CO -> 3Fe + 4CO2", "h": "Chất khử?", "a": "CO"},
        {"pt": "Cl2 + 2KOH -> KCl + KClO + H2O", "h": "Cl từ 0 lên?", "a": "+1"},
        {"pt": "2Na + 2H2O -> 2NaOH + H2", "h": "Bị khử?", "a": "H"},
        {"pt": "C + 2H2SO4 -> CO2 + 2SO2 + 2H2O", "h": "C là chất gì?", "a": "Chất khử"},
        {"pt": "AgNO3 + Cu -> Cu(NO3)2 + 2Ag", "h": "Chất oxi hóa?", "a": "AgNO3"},
        {"pt": "2H2O2 -> 2H2O + O2", "h": "O từ -1 lên?", "a": "0"}
    ]
    if 'rd_q' not in st.session_state: st.session_state.rd_q = random.choice(redo_list)
    st.markdown(
        f"<div class='element-card'><h3>Phản ứng: {st.session_state.rd_q['pt']}</h3><p>{st.session_state.rd_q['h']}</p></div>",
        unsafe_allow_html=True)
    ans = st.text_input("Trả lời:", key="ans_rd").strip()
    if st.button("Kiểm tra Oxh-Khử"):
        if ans.lower() == st.session_state.rd_q['a'].lower():
            st.balloons();
            add_points(20)
            st.session_state.rd_q = random.choice(redo_list);
            st.rerun()
        else:
            st.error("Sai rồi!")