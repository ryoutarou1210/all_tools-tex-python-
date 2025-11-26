import streamlit as st
import pandas as pd
import numpy as np
import re
import sys
import os

# ユーザー環境のパス設定
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    import style
    import auth_manager
except ImportError:
    # ローカル動作確認用
    class style:
        @staticmethod
        def apply_custom_style(): pass
    class auth_manager:
        @staticmethod
        def check_auth(): pass

st.set_page_config(page_title="LaTeX表作成ツール", layout="wide")

style.apply_custom_style()

# --- 共通ロジック: 列名の生成 ---
def generate_new_col_name(current_columns, use_math_header):
    base_count = len(current_columns) + 1
    if use_math_header:
        new_col = f"$x_{{{base_count}}}$"
    else:
        new_col = f"列 {base_count}"
    
    # 重複回避
    base_name = new_col
    counter = 1
    while new_col in current_columns:
        new_col = f"{base_name}_{counter}"
        counter += 1
    return new_col

# --- 共通ロジック: フォーマット文字列の調整 ---
def adjust_column_format(df):
    current_fmt = st.session_state.get("column_format_input", "c" * len(df.columns))
    target_len = len(df.columns)
    
    if len(current_fmt) < target_len:
        last_char = current_fmt[-1] if current_fmt else 'c'
        new_fmt = current_fmt + last_char * (target_len - len(current_fmt))
        st.session_state.column_format_input = new_fmt
    elif len(current_fmt) > target_len:
        st.session_state.column_format_input = current_fmt[:target_len]

# --- コールバック: 数値入力変更時 ---
def on_shape_input_change():
    """数値入力欄が変更されたときに発火"""
    target_rows = st.session_state.rows_input
    target_cols = st.session_state.cols_input
    df = st.session_state.df.copy()
    
    # 現在のエディタの内容を反映（サイズが変わる前のデータ確保）
    if "main_editor" in st.session_state and isinstance(st.session_state["main_editor"], pd.DataFrame):
        current_editor = st.session_state["main_editor"]
        if current_editor.shape == df.shape:
             df = current_editor

    # 行のリサイズ
    if target_rows < len(df):
        df = df.iloc[:target_rows]
    elif target_rows > len(df):
        rows_to_add = target_rows - len(df)
        new_rows = pd.DataFrame([[""] * len(df.columns)] * rows_to_add, columns=df.columns)
        df = pd.concat([df, new_rows], ignore_index=True)

    # 列のリサイズ
    if target_cols < len(df.columns):
        df = df.iloc[:, :target_cols]
    elif target_cols > len(df.columns):
        cols_to_add = target_cols - len(df.columns)
        use_math = st.session_state.get("use_math_header", False)
        for _ in range(cols_to_add):
            new_col = generate_new_col_name(df.columns, use_math)
            df[new_col] = ""

    st.session_state.df = df
    adjust_column_format(df)
    
    # エディタリセット
    if "main_editor" in st.session_state:
        del st.session_state["main_editor"]


# --- コールバック: ＋／ーボタン押下時 ---
def update_df_shape(action, axis):
    """ボタンが押されたときに発火"""
    # 数値入力の値を基準にする（同期ズレ防止）
    current_rows = st.session_state.rows_input
    current_cols = st.session_state.cols_input
    
    if axis == 'row':
        if action == 'add':
            st.session_state.rows_input = current_rows + 1
        elif action == 'del':
            st.session_state.rows_input = max(1, current_rows - 1)
    elif axis == 'col':
        if action == 'add':
            st.session_state.cols_input = current_cols + 1
        elif action == 'del':
            st.session_state.cols_input = max(1, current_cols - 1)
            
    # 値を更新した後、リサイズロジックを呼ぶ
    on_shape_input_change()

# ----------------------------------

# 初期化
if 'df' not in st.session_state:
    init_rows, init_cols = 5, 4
    data = np.full((init_rows, init_cols), "")
    columns = [f"列 {i+1}" for i in range(init_cols)]
    st.session_state.df = pd.DataFrame(data, columns=columns)

# DataFrameとSession Stateの整合性チェック
# (リロード時などに数値入力欄の初期値をDFサイズに合わせる)
if "rows_input" not in st.session_state:
    st.session_state.rows_input = len(st.session_state.df)
if "cols_input" not in st.session_state:
    st.session_state.cols_input = len(st.session_state.df.columns)

# エディタ同期
if "main_editor" in st.session_state:
    edited_data = st.session_state["main_editor"]
    if isinstance(edited_data, pd.DataFrame):
        if edited_data.shape == st.session_state.df.shape:
            st.session_state.df = edited_data

if not isinstance(st.session_state.df, pd.DataFrame):
    st.session_state.df = pd.DataFrame(st.session_state.df)


# --- サイドバー設定 ---
st.sidebar.title("出力設定")

st.sidebar.subheader("1. 編集オプション")
st.sidebar.checkbox("列追加時に数式名にする ($x_n$)", value=False, key="use_math_header")

st.sidebar.subheader("2. スタイル")
use_booktabs = st.sidebar.checkbox("Booktabs (きれいな罫線)", value=True)
center_table = st.sidebar.checkbox("Center (中央揃え)", value=True)

st.sidebar.subheader("3. メタデータ")
caption = st.sidebar.text_input("キャプション", "")
label = st.sidebar.text_input("ラベル", "tab:mytable")

st.sidebar.subheader("4. 列フォーマット")
if "column_format_input" not in st.session_state:
    st.session_state.column_format_input = "c" * len(st.session_state.df.columns)
column_format = st.sidebar.text_input("フォーマット指定", key="column_format_input")

# --- プロフィール表示（最後）---
auth_manager.check_auth()
# ----------------------------

st.title("LaTeX表作成ツール")

# --- 直感的な行列操作パネル (ボタン + 数値入力) ---
st.write("##### テーブルサイズの変更")
ctrl_col1, ctrl_col2 = st.columns(2)

# 行操作
with ctrl_col1:
    st.caption("行数 (Rows)")
    r_c1, r_c2, r_c3 = st.columns([1, 2, 1])
    with r_c1:
        st.button("➖", key="del_row", on_click=update_df_shape, args=('del', 'row'), use_container_width=True)
    with r_c2:
        # 数値入力 (変更時にon_change発火)
        st.number_input(
            "Rows", 
            min_value=1, 
            key="rows_input", 
            on_change=on_shape_input_change, 
            label_visibility="collapsed"
        )
    with r_c3:
        st.button("➕", key="add_row", on_click=update_df_shape, args=('add', 'row'), type="primary", use_container_width=True)

# 列操作
with ctrl_col2:
    st.caption("列数 (Cols)")
    c_c1, c_c2, c_c3 = st.columns([1, 2, 1])
    with c_c1:
        st.button("➖", key="del_col", on_click=update_df_shape, args=('del', 'col'), use_container_width=True)
    with c_c2:
        # 数値入力 (変更時にon_change発火)
        st.number_input(
            "Cols", 
            min_value=1, 
            key="cols_input", 
            on_change=on_shape_input_change, 
            label_visibility="collapsed"
        )
    with c_c3:
        st.button("➕", key="add_col", on_click=update_df_shape, args=('add', 'col'), type="primary", use_container_width=True)

st.divider()

# データエディタ
edited_df = st.data_editor(st.session_state.df, num_rows="fixed", use_container_width=True, key="main_editor")
st.divider()

# 列名編集
st.subheader("列名の編集")
cols = st.columns(min(4, len(edited_df.columns)))
new_names = []
for i, c in enumerate(edited_df.columns):
    col_ui = cols[i % len(cols)]
    new_names.append(col_ui.text_input(f"列 {i+1}", value=c, key=f"rename_{i}"))

if st.button("列名を更新", use_container_width=True):
    st.session_state.df = edited_df
    st.session_state.df.columns = new_names
    if "main_editor" in st.session_state:
        del st.session_state["main_editor"]
    st.rerun()

st.divider()

# LaTeX生成
if st.button("LaTeXコードを生成", type="primary", use_container_width=True):
    st.session_state.df = edited_df 
    try:
        active_format = column_format
        if len(active_format) != len(edited_df.columns):
             st.warning(f"注意: 列数({len(edited_df.columns)})とフォーマット指定({len(active_format)})の長さが一致していません。")
        
        latex_code = st.session_state.df.to_latex(
            index=False, header=True, escape=False,
            column_format=active_format,
            caption=caption if caption else None,
            label=label if label else None,
            position="htbp"
        )
        final_code = latex_code
        if use_booktabs:
            final_code = final_code.replace("\\hline", "\\toprule", 1)
            final_code = final_code[::-1].replace("enilh\\", "elurmottob\\", 1)[::-1] 
            
            lines = final_code.splitlines()
            hlines_idx = [i for i, l in enumerate(lines) if "\\hline" in l]
            if len(hlines_idx) > 0:
                for idx in hlines_idx:
                    lines[idx] = lines[idx].replace("\\hline", "\\midrule")
            final_code = "\n".join(lines)
            
        if center_table:
            final_code = re.sub(r'(\\begin\{table\}(?:\[.*?\])?)', r'\1\n\\centering', final_code)
        
        st.code(final_code, language="latex")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
