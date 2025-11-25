import streamlit as st
import pandas as pd
import numpy as np
import re
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import style

st.set_page_config(page_title="LaTeX表作成ツール", layout="wide")
style.apply_custom_style()

# =========================================================
# 1. 初期化処理 & データ同期
# =========================================================
# 初回起動時の初期化
if 'df' not in st.session_state:
    init_rows, init_cols = 5, 4
    data = np.full((init_rows, init_cols), "")
    columns = [f"列 {i+1}" for i in range(init_cols)]
    st.session_state.df = pd.DataFrame(data, columns=columns)

# 【重要】ボタン操作より前に、手動編集の内容を反映させます。
if "main_editor" in st.session_state:
    edited_data = st.session_state["main_editor"]
    
    if isinstance(edited_data, pd.DataFrame):
        st.session_state.df = edited_data
    elif isinstance(edited_data, (dict, list)):
        try:
            st.session_state.df = pd.DataFrame(edited_data)
        except Exception:
            pass

# 万が一 df が DataFrame 以外になっていた場合の強制修復
if not isinstance(st.session_state.df, pd.DataFrame):
    st.session_state.df = pd.DataFrame(st.session_state.df)

# =========================================================
# 2. サイドバー（設定エリア）
# =========================================================
st.sidebar.title("出力設定")

st.sidebar.subheader("1. スタイル")
use_booktabs = st.sidebar.checkbox("Booktabs (きれいな罫線)", value=True)
center_table = st.sidebar.checkbox("Center (中央揃え)", value=True)

st.sidebar.subheader("2. メタデータ")
caption = st.sidebar.text_input("キャプション (Caption)", "", placeholder="表の説明を入力")
label = st.sidebar.text_input("ラベル (Label)", "tab:mytable")

st.sidebar.subheader("3. 列フォーマット")
# 現在の列数に合わせてデフォルト値を生成
current_cols_count = len(st.session_state.df.columns)
default_fmt = "c" * current_cols_count
column_format = st.sidebar.text_input(
    "フォーマット指定", 
    value=default_fmt, 
    help="例: lcr (左中右), |c|c| (縦線あり)"
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **使い方**\n\n表を編集した後、**「行を追加」**や**「コード生成」**などのボタンを押すと、自動的に内容が保存・反映されます。")

# =========================================================
# 3. メインエリア
# =========================================================
st.title("LaTeX表作成ツール")

# ---------------------------------------------------------
# A. 行列操作 (一括リサイズ & 増減ボタン)
# ---------------------------------------------------------
st.markdown("##### ▼ サイズ調整")

# --- 1. サイズ一括指定エリア (常時表示) ---
r_col, c_col, btn_col = st.columns([1, 1, 1])

current_rows = len(st.session_state.df)
current_cols = len(st.session_state.df.columns)

with r_col:
    target_rows = st.number_input("行数 (一括指定)", min_value=1, value=current_rows, step=1, key="target_rows")
with c_col:
    target_cols = st.number_input("列数 (一括指定)", min_value=1, value=current_cols, step=1, key="target_cols")
with btn_col:
    st.write("") # レイアウト調整用 (ラベル分の高さ確保)
    st.write("")
    if st.button("サイズを適用", use_container_width=True):
        df = st.session_state.df.copy()
        
        # 行数の調整
        if target_rows < len(df):
            df = df.iloc[:target_rows]
        elif target_rows > len(df):
            rows_to_add = target_rows - len(df)
            new_data = pd.DataFrame([[""] * len(df.columns)] * rows_to_add, columns=df.columns)
            df = pd.concat([df, new_data], ignore_index=True)
        
        # 列数の調整
        if target_cols < len(df.columns):
            df = df.iloc[:, :target_cols]
        elif target_cols > len(df.columns):
            cols_to_add = target_cols - len(df.columns)
            current_col_names = list(df.columns)
            for _ in range(cols_to_add):
                new_idx = len(current_col_names) + 1
                while f"列 {new_idx}" in current_col_names:
                    new_idx += 1
                new_name = f"列 {new_idx}"
                current_col_names.append(new_name)
                df[new_name] = ""

        st.session_state.df = df
        st.rerun()

# --- 2. 従来の増減ボタン ---
st.caption("微調整")
col_add_r, col_del_r, col_add_c, col_del_c = st.columns(4)

# 行追加
if col_add_r.button("＋ 行を追加", use_container_width=True):
    new_row = pd.DataFrame([[""] * len(st.session_state.df.columns)], columns=st.session_state.df.columns)
    st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
    st.rerun()

# 行削除
if col_del_r.button("－ 行を削除", use_container_width=True):
    if len(st.session_state.df) > 1:
        st.session_state.df = st.session_state.df.iloc[:-1]
        st.rerun()
    else:
        st.warning("これ以上削除できません")

# 列追加
if col_add_c.button("＋ 列を追加", use_container_width=True):
    curr_cols = len(st.session_state.df.columns)
    new_col_name = f"列 {curr_cols + 1}"
    while new_col_name in st.session_state.df.columns:
        curr_cols += 1
        new_col_name = f"列 {curr_cols + 1}"
    st.session_state.df[new_col_name] = ""
    st.rerun()

# 列削除
if col_del_c.button("－ 列を削除", use_container_width=True):
    if len(st.session_state.df.columns) > 1:
        st.session_state.df = st.session_state.df.iloc[:, :-1]
        st.rerun()
    else:
        st.warning("これ以上削除できません")

# ---------------------------------------------------------
# B. データエディタ (表)
# ---------------------------------------------------------
st.markdown("######") 

edited_df = st.data_editor(
    st.session_state.df,
    num_rows="fixed", 
    use_container_width=True,
    key="main_editor"
)

st.divider()

# ---------------------------------------------------------
# C. 列名の変更エリア (表の下・常に表示)
# ---------------------------------------------------------
st.subheader("列名の編集")
cols = list(edited_df.columns)
new_names = []
cols_ui = st.columns(4)

for i, c in enumerate(cols):
    val = cols_ui[i % 4].text_input(f"列 {i+1} の名前", value=c, key=f"rename_{i}")
    new_names.append(val)

if st.button("列名を更新して保存", key="btn_rename"):
    st.session_state.df = edited_df 
    st.session_state.df.columns = new_names 
    st.rerun()


# =========================================================
# 4. コード生成エリア
# =========================================================
st.divider()

if st.button("LaTeXコードを生成する", type="primary", use_container_width=True):
    st.session_state.df = edited_df 
    
    try:
        # to_latex で基本コード生成
        latex_code = st.session_state.df.to_latex(
            index=False,
            header=True,
            escape=False,
            column_format=column_format,
            caption=caption if caption else None,
            label=label if label else None,
            position="htbp"
        )

        final_code = latex_code
        
        # Booktabs加工 (\hline -> \toprule, \midrule, \bottomrule)
        if use_booktabs:
            lines = final_code.splitlines()
            hlines = [i for i, l in enumerate(lines) if "\\hline" in l]
            if len(hlines) >= 2:
                lines[hlines[0]] = lines[hlines[0]].replace("\\hline", "\\toprule")
                lines[hlines[1]] = lines[hlines[1]].replace("\\hline", "\\midrule")
                lines[hlines[-1]] = lines[hlines[-1]].replace("\\hline", "\\bottomrule")
            final_code = "\n".join(lines)
        
        # 中央揃え加工
        if center_table:
            final_code = re.sub(r'(\\begin\{table\}(?:\[.*?\])?)', r'\1\n\\centering', final_code)

        st.code(final_code, language="latex")
        
    except Exception as e:
        st.error(f"エラー: {e}")