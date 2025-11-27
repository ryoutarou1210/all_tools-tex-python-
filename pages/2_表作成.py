import streamlit as st
import pandas as pd
import numpy as np
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

style.apply_custom_style()

# ---------------------------------------------------------
# DataFrame リサイズ機能
# ---------------------------------------------------------

def resize_dataframe(df, target_rows, target_cols):
    current_rows, current_cols = df.shape

    # 行の調整
    if target_rows < current_rows:
        df = df.iloc[:target_rows, :]
    elif target_rows > current_rows:
        rows_to_add = target_rows - current_rows
        new_rows = pd.DataFrame([[""] * current_cols] * rows_to_add, columns=df.columns)
        df = pd.concat([df, new_rows], ignore_index=True)

    # 列の調整
    current_rows, current_cols = df.shape
    if target_cols < current_cols:
        df = df.iloc[:, :target_cols]
    elif target_cols > current_cols:
        for _ in range(target_cols - current_cols):
            new_col = f"列 {len(df.columns) + 1}"
            base = new_col
            n = 1
            while new_col in df.columns:
                new_col = f"{base}_{n}"
                n += 1
            df[new_col] = ""

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

    new_df = resize_dataframe(
        base_df,
        st.session_state.rows_input,
        st.session_state.cols_input
    )

    fmt = st.session_state.get("column_format_input", "c" * len(new_df.columns))
    if len(fmt) < len(new_df.columns):
        st.session_state.column_format_input = fmt + fmt[-1] * (len(new_df.columns) - len(fmt))
    else:
        st.session_state.column_format_input = fmt[:len(new_df.columns)]

    st.session_state.df = new_df

    if "merge_list" in st.session_state:
        st.session_state.merge_list = clean_merges(
            st.session_state.merge_list,
            st.session_state.rows_input,
            st.session_state.cols_input
        )

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
# UIハイライト用関数 (Pandas Styler)
# ---------------------------------------------------------
def highlight_merges(df):
    """
    結合されているセルに対して背景色を設定するスタイル関数
    """
    # 全て空文字（スタイルなし）で初期化
    style_df = pd.DataFrame('', index=df.index, columns=df.columns)
    
    if "merge_list" in st.session_state:
        for m in st.session_state.merge_list:
            r, c, rs, cs = m["r"], m["c"], m["rs"], m["cs"]
            # 結合範囲に色（薄いオレンジ）を適用
            style_df.iloc[r:r+rs, c:c+cs] = 'background-color: #ffeeba; color: black;'
            
    return style_df

# ---------------------------------------------------------
# LaTeX 生成 (色なしバージョンに戻しました)
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

    top = "\\toprule" if use_booktabs else "\\hline"
    mid = "\\midrule" if use_booktabs else "\\hline"
    bottom = "\\bottomrule" if use_booktabs else "\\hline"

    lines = []
    lines.append("\\begin{table}[htbp]")
    if center:
        lines.append("  \\centering")

    if caption:
        lines.append(f"  \\caption{{{caption}}}")
    if label:
        lines.append(f"  \\label{{{label}}}")

    lines.append(f"  \\begin{{tabular}}{{{col_fmt}}}")
    lines.append(f"    {top}")

    # header
    header = " & ".join([f"\\textbf{{{c}}}" for c in df.columns]) + " \\\\"
    lines.append("    " + header)
    lines.append(f"    {mid}")

    # body
    for i in range(rows):
        row_cells = []
        for j in range(cols):
            if skip[i, j]:
                continue

            text = str(df.iloc[i, j])

            if (i, j) in merge_map:
                rs, cs = merge_map[(i, j)]
                if rs > 1 and cs > 1:
                    cell = "\\multicolumn{" + str(cs) + "}{c}{\\multirow{" + str(rs) + "}{*}{" + text + "}}"
                elif rs > 1:
                    cell = "\\multirow{" + str(rs) + "}{*}{" + text + "}"
                elif cs > 1:
                    cell = "\\multicolumn{" + str(cs) + "}{c}{" + text + "}"
                else:
                    cell = text
            else:
                cell = text

            row_cells.append(cell)

        lines.append("    " + " & ".join(row_cells) + " \\\\")

    lines.append(f"    {bottom}")
    lines.append("  \\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)

# ---------------------------------------------------------
# Merge 管理
# ---------------------------------------------------------

def add_merge():
    if "merge_list" not in st.session_state:
        st.session_state.merge_list = []

    st.session_state.merge_list.append({
        "r": st.session_state.merge_r_input - 1,
        "c": st.session_state.merge_c_input - 1,
        "rs": st.session_state.merge_rs_input,
        "cs": st.session_state.merge_cs_input
    })


def remove_merge(i):
    st.session_state.merge_list.pop(i)

# ---------------------------------------------------------
# 初期化
# ---------------------------------------------------------

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(
        np.full((5, 4), ""),
        columns=[f"列 {i+1}" for i in range(4)]
    )

if "merge_list" not in st.session_state:
    st.session_state.merge_list = []

if "rows_input" not in st.session_state:
    st.session_state.rows_input = len(st.session_state.df)

if "cols_input" not in st.session_state:
    st.session_state.cols_input = len(st.session_state.df.columns)

# ---------------------------------------------------------
# サイドバー
# ---------------------------------------------------------

st.sidebar.title("出力設定")

use_booktabs = st.sidebar.checkbox("Booktabs（きれいな罫線）", value=True)
center_table = st.sidebar.checkbox("中央揃え", value=True)

caption = st.sidebar.text_input("キャプション")
label = st.sidebar.text_input("ラベル", "tab:mytable")

if "column_format_input" not in st.session_state:
    st.session_state.column_format_input = "c" * len(st.session_state.df.columns)

column_format = st.sidebar.text_input("列フォーマット", key="column_format_input")

auth_manager.check_auth()

# ---------------------------------------------------------
# UI
# ---------------------------------------------------------

st.title("LaTeX表作成ツール")

# ---------------------------------------------------------
# 1. テーブルサイズ変更
# ---------------------------------------------------------

st.write("### 1. テーブルサイズの変更")
c1, c2 = st.columns(2)

with c1:
    st.caption("行数")
    b1, b2, b3 = st.columns([1, 2, 1])
    with b1:
        st.button("➖", key="row_minus", on_click=update_input_vals, args=("del", "row"))
    with b2:
        st.number_input("Rows", min_value=1, key="rows_input",
                        on_change=on_shape_change, label_visibility="collapsed")
    with b3:
        st.button("➕", key="row_plus", on_click=update_input_vals, args=("add", "row"))

with c2:
    st.caption("列数")
    b1, b2, b3 = st.columns([1, 2, 1])
    with b1:
        st.button("➖", key="col_minus", on_click=update_input_vals, args=("del", "col"))
    with b2:
        st.number_input("Cols", min_value=1, key="cols_input",
                        on_change=on_shape_change, label_visibility="collapsed")
    with b3:
        st.button("➕", key="col_plus", on_click=update_input_vals, args=("add", "col"))


# ---------------------------------------------------------
# 3. セル結合設定
# ---------------------------------------------------------

with st.expander("セルの結合設定", expanded=False):

    r, c, rs, cs, add = st.columns([1, 1, 1, 1, 1])

    with r:
        st.number_input("行", 1, st.session_state.rows_input, 1, key="merge_r_input")
    with c:
        st.number_input("列", 1, st.session_state.cols_input, 1, key="merge_c_input")
    with rs:
        st.number_input("高さ (RowSpan)", 1, 20, 1, key="merge_rs_input")
    with cs:
        st.number_input("幅 (ColSpan)", 1, 20, 1, key="merge_cs_input")
    with add:
        st.write(""); st.write("")
        st.button("追加", key="merge_add", on_click=add_merge)
    
    # --- 結合確認用プレビュー (色付き) ---
    st.write("▼ **結合状態プレビュー**（黄色いエリアが結合されます）")
    st.dataframe(
        st.session_state.df.style.apply(lambda _: highlight_merges(st.session_state.df), axis=None),
        use_container_width=True,
        height=200 # 高さを制限
    )

    st.write("現在の結合リスト")
    if st.session_state.merge_list:
        for idx, m in enumerate(st.session_state.merge_list):
            a, b = st.columns([4, 1])
            with a:
                st.text(f"行{m['r']+1}, 列{m['c']+1} → {m['rs']}×{m['cs']}")
            with b:
                st.button("削除", key=f"merge_del_{idx}", on_click=remove_merge, args=(idx,))
    else:
        st.info("結合なし")

st.divider()



# ---------------------------------------------------------
# 2. 列名編集（前に移動）
# ---------------------------------------------------------

st.write("### 2. 列名の編集")

cols = st.columns(min(4, len(st.session_state.df.columns)))
new_names = []

for i, name in enumerate(st.session_state.df.columns):
    ui = cols[i % len(cols)]
    new_names.append(ui.text_input(f"列 {i+1}", value=name, key=f"rename_col_{i}"))

if st.button("列名を更新", key="rename_btn"):
    st.session_state.df.columns = new_names
    if "main_editor" in st.session_state:
        del st.session_state["main_editor"]
    st.rerun()

st.divider()

# ---------------------------------------------------------
# 4. データ編集
# ---------------------------------------------------------

st.write("### 3. データの編集")
st.caption("※ここで値を入力してください。結合は反映されませんが、出力時には適用されます。")

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

st.write("### 4. LaTeXコード生成")

if st.button("LaTeXコードを生成", key="generate_latex", type="primary"):
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
            st.info("結合を使用しているため、LaTeX のプリアンブルに `\\usepackage{multirow}` を追加してください。")

    except Exception as e:
        st.error(f"エラー: {e}")


