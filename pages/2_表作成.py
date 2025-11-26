import streamlit as st
import pandas as pd
import numpy as np
import re
import sys
import os

# ---------------------------------------------------------
# 1. ページ設定 (Streamlitコマンドの最初でなければならない)
# ---------------------------------------------------------
st.set_page_config(page_title="LaTeX表作成ツール", layout="wide")

# ---------------------------------------------------------
# 2. 外部モジュール読み込み (パス解決ロジック)
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

# 3. 認証チェック & スタイル適用
auth_manager.check_auth()
style.apply_custom_style()

# ---------------------------------------------------------
# ロジック関数定義
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
        cols_to_add = target_cols - current_cols
        for _ in range(cols_to_add):
            new_col_name = f"列 {len(df.columns) + 1}"
            base_name = new_col_name
            counter = 1
            while new_col_name in df.columns:
                new_col_name = f"{base_name}_{counter}"
                counter += 1
            df[new_col_name] = ""

    return df


def clean_merges(merges, rows, cols):
    valid_merges = []
    for m in merges:
        r_end = m['r'] + m['rs']
        c_end = m['c'] + m['cs']
        if r_end <= rows and c_end <= cols:
            valid_merges.append(m)
    return valid_merges


def on_shape_change():
    if "main_editor" in st.session_state and isinstance(st.session_state["main_editor"], pd.DataFrame):
        current_df = st.session_state["main_editor"]
    else:
        current_df = st.session_state.df

    target_rows = st.session_state.rows_input
    target_cols = st.session_state.cols_input

    new_df = resize_dataframe(current_df, target_rows, target_cols)

    current_fmt = st.session_state.get("column_format_input", "c" * len(new_df.columns))
    if len(current_fmt) < len(new_df.columns):
        last_char = current_fmt[-1] if current_fmt else 'c'
        st.session_state.column_format_input = current_fmt + last_char * (len(new_df.columns) - len(current_fmt))
    elif len(current_fmt) > len(new_df.columns):
        st.session_state.column_format_input = current_fmt[:len(new_df.columns)]

    if "merge_list" in st.session_state:
        st.session_state.merge_list = clean_merges(st.session_state.merge_list, target_rows, target_cols)

    st.session_state.df = new_df

    if "main_editor" in st.session_state:
        del st.session_state["main_editor"]


def update_input_vals(action, axis):
    current_r = st.session_state.rows_input
    current_c = st.session_state.cols_input

    if axis == 'row':
        if action == 'add':
            st.session_state.rows_input = current_r + 1
        elif action == 'del':
            st.session_state.rows_input = max(1, current_r - 1)
    elif axis == 'col':
        if action == 'add':
            st.session_state.cols_input = current_c + 1
        elif action == 'del':
            st.session_state.cols_input = max(1, current_c - 1)

    on_shape_change()


# ---------------------------------------------------------
# ★ LaTeX生成（f-stringの式内にバックスラッシュを置かない安全版）★
# ---------------------------------------------------------
def generate_custom_latex(df, merges, caption, label, col_fmt, use_booktabs, center):

    rows, cols = df.shape
    skip_mask = np.zeros((rows, cols), dtype=bool)

    # 結合マップ
    merge_map = {}
    for m in merges:
        r, c, rs, cs = m['r'], m['c'], m['rs'], m['cs']
        merge_map[(r, c)] = (rs, cs)
        for i in range(r, r + rs):
            for j in range(c, c + cs):
                if (i, j) != (r, c):
                    skip_mask[i, j] = True

    lines = []

    lines.append("\\begin{table}[htbp]")
    if center:
        lines.append("  \\centering")

    if caption:
        lines.append(f"  \\caption{{{caption}}}")
    if label:
        lines.append(f"  \\label{{{label}}}")

    lines.append(f"  \\begin{{tabular}}{{{col_fmt}}}")

    # --- 罫線設定 ---
    top_rule = "\\toprule" if use_booktabs else "\\hline"
    mid_rule = "\\midrule" if use_booktabs else "\\hline"
    bottom_rule = "\\bottomrule" if use_booktabs else "\\hline"

    lines.append(f"    {top_rule}")

    # --- ヘッダー行 ---
    header_cells = [f"\\textbf{{{col}}}" for col in df.columns]
    header_line = " & ".join(header_cells) + " \\\\"
    lines.append(f"    {header_line}")
    lines.append(f"    {mid_rule}")

    # --- データ部分 ---
    for i in range(rows):
        row_cells = []

        for j in range(cols):
            if skip_mask[i, j]:
                continue

            content = str(df.iloc[i, j])

            if (i, j) in merge_map:
                rs, cs = merge_map[(i, j)]

                if rs > 1 and cs > 1:
                    cell_latex = "\\multicolumn{" + str(cs) + "}{c}{\\multirow{" + str(rs) + "}{*}{" + content + "}}"
                elif rs > 1 and cs == 1:
                    cell_latex = "\\multirow{" + str(rs) + "}{*}{" + content + "}"
                elif rs == 1 and cs > 1:
                    cell_latex = "\\multicolumn{" + str(cs) + "}{c}{" + content + "}"
                else:
                    cell_latex = content
            else:
                cell_latex = content

            row_cells.append(cell_latex)

        line = " & ".join(row_cells) + " \\\\"
        lines.append(f"    {line}")

    lines.append(f"    {bottom_rule}")
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

    new_merge = {'r': r, 'c': c, 'rs': rs, 'cs': cs}

    if "merge_list" not in st.session_state:
        st.session_state.merge_list = []

    st.session_state.merge_list.append(new_merge)


def remove_merge(index):
    if "merge_list" in st.session_state:
        st.session_state.merge_list.pop(index)


# ---------------------------------------------------------
# 初期化
# ---------------------------------------------------------

if 'df' not in st.session_state:
    init_rows, init_cols = 5, 4
    data = np.full((init_rows, init_cols), "")
    columns = [f"列 {i+1}" for i in range(init_cols)]
    st.session_state.df = pd.DataFrame(data, columns=columns)

if 'merge_list' not in st.session_state:
    st.session_state.merge_list = []

if "rows_input" not in st.session_state:
    st.session_state.rows_input = len(st.session_state.df)
if "cols_input" not in st.session_state:
    st.session_state.cols_input = len(st.session_state.df.columns)

if "main_editor" in st.session_state:
    edited_data = st.session_state["main_editor"]
    if isinstance(edited_data, pd.DataFrame):
        if edited_data.shape == st.session_state.df.shape:
            st.session_state.df = edited_data

if not isinstance(st.session_state.df, pd.DataFrame):
    st.session_state.df = pd.DataFrame(st.session_state.df)

# ---------------------------------------------------------
# UI
# ---------------------------------------------------------

st.sidebar.title("出力設定")

st.sidebar.subheader("1. スタイル")
use_booktabs = st.sidebar.checkbox("Booktabs (きれいな罫線)", value=True)
center_table = st.sidebar.checkbox("Center (中央揃え)", value=True)

st.sidebar.subheader("2. メタデータ")
caption = st.sidebar.text_input("キャプション", "")
label = st.sidebar.text_input("ラベル", "tab:mytable")

st.sidebar.subheader("3. 列フォーマット")
if "column_format_input" not in st.session_state:
    st.session_state.column_format_input = "c" * len(st.session_state.df.columns)
column_format = st.sidebar.text_input("フォーマット指定", key="column_format_input")

st.sidebar.info("結合を使用する場合は、LaTeXファイルのプリアンブルに `\\usepackage{multirow}` を追加してください。")

# --- メイン ---
st.title("LaTeX表作成ツール (結合対応)")

# テーブルサイズ変更
st.write("##### 1. テーブルサイズの変更")
ctrl_col1, ctrl_col2 = st.columns(2)

# 行操作
with ctrl_col1:
    st.caption("行数 (Rows)")
    r_c1, r_c2, r_c3 = st.columns([1, 2, 1])
    with r_c1:
        st.button("➖", key="del_row", on_click=update_input_vals, args=('del', 'row'), use_container_width=True)
    with r_c2:
        st.number_input("Rows", min_value=1, key="rows_input",
                        on_change=on_shape_change, label_visibility="collapsed")
    with r_c3:
        st.button("➕", key="add_row", on_click=update_input_vals,
                  args=('add', 'row'), type="primary", use_container_width=True)

# 列操作
with ctrl_col2:
    st.caption("列数 (Cols)")
    c_c1, c_c2, c_c3 = st.columns([1, 2, 1])
    with c_c1:
        st.button("➖", key="del_col", on_click=update_input_vals, args=('del', 'col'), use_container_width=True)
    with c_c2:
        st.number_input("Cols", min_value=1, key="cols_input",
                        on_change=on_shape_change, label_visibility="collapsed")
    with c_c3:
        st.button("➕", key="add_col", on_click=update_input_vals,
                  args=('add', 'col'), type="primary", use_container_width=True)

st.divider()

# --- 結合設定 ---
with st.expander("🔗 セルの結合設定 (Merge Cells)", expanded=False):
    st.caption("結合したい範囲を指定してください。内容は左上のセルの値が使用されます。")
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns([1, 1, 1, 1, 1])

    max_r = st.session_state.rows_input
    max_c = st.session_state.cols_input

    with m_col1:
        st.number_input("開始 行", 1, max_r, 1, key="merge_r_input")
    with m_col2:
        st.number_input("開始 列", 1, max_c, 1, key="merge_c_input")
    with m_col3:
        st.number_input("縦幅 (RowSpan)", 1, 10, 1, key="merge_rs_input")
    with m_col4:
        st.number_input("横幅 (ColSpan)", 1, 10, 1, key="merge_cs_input")
    with m_col5:
        st.write("")
        st.write("")
        st.button("結合を追加", on_click=add_merge, use_container_width=True)

    if st.session_state.merge_list:
        st.write("現在の結合リスト:")
        for idx, m in enumerate(st.session_state.merge_list):
            cols_disp = st.columns([4, 1])
            with cols_disp[0]:
                st.text(f"行:{m['r']+1}, 列:{m['c']+1} から 縦:{m['rs']} x 横:{m['cs']}")
            with cols_disp[1]:
                st.button("削除", key=f"del_merge_{idx}",
                          on_click=remove_merge, args=(idx,))
    else:
        st.info("結合設定はありません")

st.divider()

# --- データ編集 ---
st.write("##### 2. データの編集")
edited_df = st.data_editor(
    st.session_state.df,
    num_rows="fixed",
    use_container_width=True,
    key="main_editor"
)
st.caption("※結合設定をしたエリアも、ここでは通常のグリッドとして表示されます。左上のセルに文字を入力してください。")

st.divider()

# --- 列名編集 ---
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

# --- LaTeX生成 ---
if st.button("LaTeXコードを生成", type="primary", use_container_width=True):
    st.session_state.df = edited_df
    try:
        active_format = column_format
        if len(active_format) != len(edited_df.columns):
            st.warning(f"注意: 列数({len(edited_df.columns)})とフォーマット指定({len(active_format)})の長さが一致していません。")

        final_code = generate_custom_latex(
            st.session_state.df,
            st.session_state.merge_list,
            caption,
            label,
            active_format,
            use_booktabs,
            center_table
        )

        st.code(final_code, language="latex")

        if st.session_state.merge_list:
            st.info("ヒント: `\\multirow` を使用しているため、LaTeX のプリアンブルに `\\usepackage{multirow}` を追加してください。")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
