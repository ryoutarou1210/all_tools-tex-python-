import streamlit as st
import pandas as pd
import numpy as np
import re
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import style
import auth_manager

st.set_page_config(page_title="LaTeX表作成ツール", layout="wide")

style.apply_custom_style()

# 初期化 & データ同期
if 'df' not in st.session_state:
    init_rows, init_cols = 5, 4
    data = np.full((init_rows, init_cols), "")
    columns = [f"列 {i+1}" for i in range(init_cols)]
    st.session_state.df = pd.DataFrame(data, columns=columns)

if "main_editor" in st.session_state:
    edited_data = st.session_state["main_editor"]
    if isinstance(edited_data, pd.DataFrame):
        st.session_state.df = edited_data
    elif isinstance(edited_data, (dict, list)):
        try:
            st.session_state.df = pd.DataFrame(edited_data)
        except: pass

if not isinstance(st.session_state.df, pd.DataFrame):
    st.session_state.df = pd.DataFrame(st.session_state.df)

# サイドバー設定
st.sidebar.title("出力設定")
st.sidebar.subheader("1. スタイル")
use_booktabs = st.sidebar.checkbox("Booktabs (きれいな罫線)", value=True)
center_table = st.sidebar.checkbox("Center (中央揃え)", value=True)

st.sidebar.subheader("2. メタデータ")
caption = st.sidebar.text_input("キャプション", "")
label = st.sidebar.text_input("ラベル", "tab:mytable")

st.sidebar.subheader("3. 列フォーマット")
current_cols_count = len(st.session_state.df.columns)
column_format = st.sidebar.text_input("フォーマット指定", value="c" * current_cols_count)

# --- 2. プロフィール表示（最後）---
auth_manager.check_auth()
# ----------------------------


st.title("LaTeX表作成ツール")

# 行列操作
r_col, c_col, btn_col = st.columns([1, 1, 1])
current_rows, current_cols = st.session_state.df.shape
with r_col: target_rows = st.number_input("行数", min_value=1, value=current_rows)
with c_col: target_cols = st.number_input("列数", min_value=1, value=current_cols)
with btn_col:
    st.write(""); st.write("")
    if st.button("サイズ適用", use_container_width=True):
        df = st.session_state.df.copy()
        # Resize Logic
        if target_rows < len(df): df = df.iloc[:target_rows]
        else: df = pd.concat([df, pd.DataFrame([[""]*len(df.columns)]*(target_rows-len(df)), columns=df.columns)], ignore_index=True)
        if target_cols < len(df.columns): df = df.iloc[:, :target_cols]
        else:
            for _ in range(target_cols - len(df.columns)):
                new_col = f"列 {len(df.columns)+1}"
                while new_col in df.columns: new_col += "_"
                df[new_col] = ""
        st.session_state.df = df
        st.rerun()

edited_df = st.data_editor(st.session_state.df, num_rows="fixed", use_container_width=True, key="main_editor")
st.divider()

# 列名編集
st.subheader("列名の編集")
new_names = []
cols_ui = st.columns(4)
for i, c in enumerate(edited_df.columns):
    new_names.append(cols_ui[i % 4].text_input(f"列 {i+1}", value=c, key=f"rename_{i}"))
if st.button("列名を更新"):
    st.session_state.df = edited_df
    st.session_state.df.columns = new_names
    st.rerun()

st.divider()
if st.button("LaTeXコードを生成", type="primary", use_container_width=True):
    st.session_state.df = edited_df 
    try:
        latex_code = st.session_state.df.to_latex(
            index=False, header=True, escape=False,
            column_format=column_format,
            caption=caption if caption else None,
            label=label if label else None,
            position="htbp"
        )
        final_code = latex_code
        if use_booktabs:
            final_code = final_code.replace("\\hline", "\\toprule", 1)
            final_code = final_code.replace("\\hline", "\\bottomrule")[::-1].replace("elurmottob\\", "elurdim\\", 1)[::-1] # Cheap hack for midrule, better to use regex logic in production but keeping simple
            # Re-implementing robust logic from previous version
            lines = latex_code.splitlines()
            hlines = [i for i, l in enumerate(lines) if "\\hline" in l]
            if len(hlines) >= 2:
                lines[hlines[0]] = lines[hlines[0]].replace("\\hline", "\\toprule")
                lines[hlines[1]] = lines[hlines[1]].replace("\\hline", "\\midrule")
                lines[hlines[-1]] = lines[hlines[-1]].replace("\\hline", "\\bottomrule")
            final_code = "\n".join(lines)
            
        if center_table:
            final_code = re.sub(r'(\\begin\{table\}(?:\[.*?\])?)', r'\1\n\\centering', final_code)
        st.code(final_code, language="latex")
    except Exception as e:
        st.error(f"Error: {e}")

auth_manager.show_profile()







