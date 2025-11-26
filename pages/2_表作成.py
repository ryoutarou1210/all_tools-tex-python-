import streamlit as st
import pandas as pd
import numpy as np
import re
import sys
import os

# ---------------------------------------------------------
# 1. ページ設定
# ---------------------------------------------------------
st.set_page_config(page_title="LaTeX表作成ツール", layout="wide")

# ---------------------------------------------------------
# 2. 外部モジュール読み込み
# ---------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    import style
    try:
        import auth_manager
    except ImportError:
        import auth_maneger as auth_manager
except ImportError:
    st.error("必要なモジュール (style.py, auth_manager.py) が見つかりません。")
    st.stop()

auth_manager.check_auth()
style.apply_custom_style()

# ---------------------------------------------------------
# リサイズ関連
# ---------------------------------------------------------

def resize_dataframe(df, target_rows, target_cols):
    current_rows, current_cols = df.shape

    if target_rows < current_rows:
        df = df.iloc[:target_rows, :]
    elif target_rows > current_rows:
        rows_to_add = target_rows - current_rows
        new_rows = pd.DataFrame([[""] * current_cols] * rows_to_add, columns=df.columns)
        df = pd.concat([df, new_rows], ignore_index=True)

    current_rows, current_cols = df.shape

    if target_cols < current_cols:
        df = df.iloc[:, :target_cols]
    elif target_cols > current_cols:
        for _ in range(target_cols - current_cols):
            new_col_name = f"列 {len(df.columns) + 1}"
            base = new_col_name
            n = 1
            while new_col_name in df.columns:
                new_col_name = f"{base}_{n}"
                n += 1
            df[new_col_name] = ""

    return df


def clean_merges(merges, rows, cols):
    valid = []
    for m in merges:
        if m["r"] + m["rs"] <= rows and m["c"] + m["cs"] <= cols:
            valid.append(m)
    return valid


def on_shape_change():
    if "main_editor" in st.session_state and isinstance(st.session_state["main_editor"], pd.DataFrame):
        base_df = st.session_state["main_editor"]
    else:
        base_df = st.session_state.df

    tr = st.session_state.rows_input
    tc = st.session_state.cols_input

    new_df = resize_dataframe(base_df, tr, tc)

    fmt = st.session_state.get("column_format_input", "c" * len(new_df.columns))
    if len(fmt) < len(new_df.columns):
        st.session_state.column_format_input = fmt + fmt[-1] * (len(new_df.columns) - len(fmt))
    elif len(fmt) > len(new_df.columns):
        st.session_state.column_format_input = fmt[:len(new_df.columns)]

    if "merge_list" in st.session_state:
        st.session_state.merge_list = clean_merges(st.session_state.merge_list, tr, tc)

    st.session_state.df = new_df
    if "main_editor" in st.session_state:
        del st.session_state["main_editor"]


def update_input_vals(action, axis):
    r = st.session_state.rows_input
    c = st.session_state.cols_input

    if axis == "row":
        st.session_state.rows_input = r + 1 if action == "add" else max(1, r - 1)
    else:
        st.session_state.cols_input = c + 1 if action == "add" else max(1, c - 1)

    on_shape_change()

# ---------------------------------------------------------
# LaTeX生成（バックスラッシュ安全処理済み）
# ---------------------------------------------------------

def generate_custom_latex(df, merges, caption, label, col_fmt, use_booktabs, center):
    rows, cols = df.shape
    skip = np.zeros((rows, cols), dtype=bool)

    merge_map = {}
    for m in merges:
        r, c, rs, cs = m["r"], m["c"], m["rs"], m["cs"]
        merge_map[(r, c)] = (rs, cs)
        for i in range(r, r + rs):
            for j in range(c, c + cs):
                if (i, j) != (r, c):
                    skip[i, j] = True

    lines = []
    lines.append("\\begin{table}[htbp]")
    if center:
        lines.append("  \\centering")

    if caption:
        lines.append(f"  \\caption{{{caption}}}")
    if label:
        lines.append(f"  \\label{{{label}}}")

    lines.append(f"  \\begin{{tabular}}{{{col_fmt}}}")

    top = "\\toprule" if use_booktabs else "\\hline"
    mid = "\\midrule" if use_booktabs else "\\hline"
    bottom = "\\bottomrule" if use_booktabs else "\\hline"

    lines.append(f"    {top}")

    headers = [f"\\textbf{{{col}}}" for col in df.columns]
    lines.append("    " + " & ".join(headers) + " \\\\")
    lines.append(f"    {mid}")

    for i in range(rows):
        row_list = []
        for j in range(cols):
            if skip[i, j]:
                continue

            text = str(df.iloc[i, j])

            if (i, j) in merge_map:
                rs, cs = merge_map[(i, j)]
                if rs > 1 and cs > 1:
                    cell = (
                        "\\multicolumn{" + str(cs) +
                        "}{c}{\\multirow{" + str(rs) +
                        "}{*}{" + text + "}}"
                    )
                elif rs > 1:
                    cell = "\\multirow{" + str(rs) + "}{*}{" + text + "}"
                elif cs > 1:
                    cell = "\\multicolumn{" + str(cs) + "}{c}{" + text + "}"
                else:
                    cell = text
            else:
                cell = text

            row_list.append(cell)

        lines.append("    " + " & ".join(row_list) + " \\\\")

    lines.append(f"    {bottom}")
    lines.append("  \\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)

# ---------------------------------------------------------
# Merge 管理
# ---------------------------------------------------------

def add_merge():
    r = st.session_state.merge_r_input - 1
    c = st.session_state.merge_c_input - 1
    rs = st.session_state.merge_rs_input
    cs = st.session_state.merge_cs_input

    if "merge_list" not in st.session_state:
        st.session_state.merge_list = []

    st.session_state.merge_list.append({"r": r, "c": c, "rs": rs, "cs": cs})


def remove_merge(i):
    if "merge_list" in st.session_state:
        st.session_state.merge_list.pop(i)

# ---------------------------------------------------------
# 初期化
# ---------------------------------------------------------

if "df" not in st.session_state:
    data = np.full((5, 4), "")
    st.session_state.df = pd.DataFrame(data, columns=[f"列 {i+1}" for i in range(4)])

if "merge_list" not in st.session_state:
    st.session_state.merge_list = []

if "rows_input" not in st.session_state:
    st.session_state.rows_input = len(st.session_state.df)

if "cols_input" not in st.session_state:
    st.session_state.cols_input = len(st.session_state.df.columns)

# Editor の同期
if "main_editor" in st.session_state:
    if isinstance(st.session_state.main_editor, pd.DataFrame):
        if st.session_state.main_editor.shape == st.session_state.df.shape:
            st.session_state.df = st.session_state.main_editor

# ---------------------------------------------------------
# UI サイドバー
# ---------------------------------------------------------

st.sidebar.title("出力設定")
use_booktabs = st.sidebar.checkbox("Booktabs", value=True)
center_table = st.sidebar.checkbox("Centralize", value=True)

caption = st.sidebar.text_input("キャプション", "")
label = st.sidebar.text_input("ラベル", "tab:mytable")

if "column_format_input" not in st.session_state:
    st.session_state.column_format_input = "c" * len(st.session_state.df.columns)

column_format = st.sidebar.text_input("列フォーマット", key="column_format_input")

# ---------------------------------------------------------
# UI 本体
# ---------------------------------------------------------

st.title("LaTeX表作成ツール（結合対応）")

# ---------------------------------------------------------
# 1. テーブルサイズ設定
# ---------------------------------------------------------

st.write("### 1. テーブルサイズの変更")
c1, c2 = st.columns(2)

with c1:
    st.caption("行数")
    b1, b2, b3 = st.columns([1, 2, 1])
    with b1:
        st.button("➖", on_click=update_input_vals, args=("del", "row"))
    with b2:
        st.number_input("Rows", min_value=1, key="rows_input",
                        on_change=on_shape_change, label_visibility="collapsed")
    with b3:
        st.button("➕", on_click=update_input_vals, args=("add", "row"))

with c2:
    st.caption("列数")
    b1, b2, b3 = st.columns([1, 2, 1])
    with b1:
        st.button("➖", on_click=update_input_vals, args=("del", "col"))
    with b2:
        st.number_input("Cols", min_value=1, key="cols_input",
                        on_change=on_shape_change, label_visibility="collapsed")
    with b3:
        st.button("➕", on_click=update_input_vals, args=("add", "col"))

st.divider()

# ---------------------------------------------------------
# 2. 列名編集（順序を前に移動）
# ---------------------------------------------------------

st.write("### 2. 列名の編集（先に設定）")

cols = st.columns(min(4, len(st.session_state.df.columns)))
new_names = []

for i, c in enumerate(st.session_state.df.columns):
    col_ui = cols[i % len(cols)]
    new_names.append(col_ui.text_input(f"列 {i+1}", value=c, key=f"rename_{i}_before"))

if st.button("列名を更新", use_container_width=True, key="rename_btn_before"):
    st.session_state.df.columns = new_names
    if "main_editor" in st.session_state:
        del st.session_state["main_editor"]
    st.rerun()

st.divider()

# ---------------------------------------------------------
# 3. セル結合設定
# ---------------------------------------------------------

with st.expander("🔗 セル結合設定"):
    st.caption("左上セルの値が使用されます。")

    r, c, rs, cs, s = st.columns([1, 1, 1, 1, 1])
    max_r = st.session_state.rows_input
    max_c = st.session_state.cols_input

    with r:
        st.number_input("行", 1, max_r, 1, key="merge_r_input")
    with c:
        st.number_input("列", 1, max_c, 1, key="merge_c_input")
    with rs:
        st.number_input("高さ", 1, 10, 1, key="merge_rs_input")
    with cs:
        st.number_input("幅", 1, 10, 1, key="merge_cs_input")
    with s:
        st.write(""); st.write("")
        st.button("追加", on_click=add_merge)

    if st.session_state.merge_list:
        for idx, m in enumerate(st.session_state.merge_list):
            rr = st.columns([4, 1])
            with rr[0]:
                st.text(f"行:{m['r']+1}, 列:{m['c']+1} → {m['rs']}×{m['cs']}")
            with rr[1]:
                st.button("削除", key=f"del_merge_{idx}", on_click=remove_merge, args=(idx,))
    else:
        st.info("結合なし")

st.divider()

# ---------------------------------------------------------
# 4. データ編集
# ---------------------------------------------------------

st.write("### 3. データの編集")
edited_df = st.data_editor(
    st.session_state.df,
    num_rows="fixed",
    use_container_width=True,
    key="main_editor"
)

st.divider()

# ---------------------------------------------------------
# 5. LaTeX生成
# ---------------------------------------------------------

if st.button("LaTeXコードを生成", type="primary"):
    st.session_state.df = edited_df
    try:
        latex = generate_custom_latex(
            st.session_state.df,
            st.session_state.merge_list,
            caption,
            label,
            column_format,
            use_booktabs,
            center_table
        )
        st.code(latex, language="latex")

        if st.session_state.merge_list:
            st.info("multirow を使うので `\\usepackage{multirow}` を追加してください。")

    except Exception as e:
        st.error(f"エラー: {e}")

