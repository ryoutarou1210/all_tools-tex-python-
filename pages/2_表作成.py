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

# スタイルと認証（どちらも存在すれば実行）
try:
    style.apply_custom_style()
except Exception:
    # 無理に止めない（環境差でエラーが出る場合があるため）
    pass

try:
    auth_manager.check_auth()
except Exception:
    # 認証モジュール側でエラーがあれば無視またはログ出しでもよい
    pass

# ---------------------------------------------------------
# DataFrame リサイズ機能
# ---------------------------------------------------------

def resize_dataframe(df, target_rows, target_cols):
    # df を DataFrame に統一してから操作
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)

    current_rows, current_cols = df.shape

    # 行の調整
    if target_rows < current_rows:
        df = df.iloc[:target_rows, :].copy()
    elif target_rows > current_rows:
        rows_to_add = target_rows - current_rows
        new_rows = pd.DataFrame([[""] * current_cols] * rows_to_add, columns=df.columns)
        df = pd.concat([df, new_rows], ignore_index=True)

    # 列の調整（行調整後のサイズを使用）
    current_rows, current_cols = df.shape
    if target_cols < current_cols:
        df = df.iloc[:, :target_cols].copy()
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
    """範囲外の結合設定を削除して返す"""
    if not merges:
        return []
    valid = []
    for m in merges:
        try:
            if (0 <= m.get("r", 0) < rows) and (0 <= m.get("c", 0) < cols):
                if (m["r"] + m["rs"] <= rows) and (m["c"] + m["cs"] <= cols):
                    valid.append(m)
        except Exception:
            # フォーマットが不正なエントリは無視する
            continue
    return valid


def on_shape_change():
    """行・列数が変わったときに呼ぶ。editor の内容を優先してリサイズし、フォーマット文字列を調整する。"""
    if "main_editor" in st.session_state and isinstance(st.session_state["main_editor"], pd.DataFrame):
        base_df = st.session_state["main_editor"]
    else:
        base_df = st.session_state.df

    # 目標サイズを安全に取得（存在しない場合は現在のサイズを使う）
    target_rows = st.session_state.get("rows_input", len(st.session_state.df))
    target_cols = st.session_state.get("cols_input", len(st.session_state.df.columns))

    new_df = resize_dataframe(base_df, target_rows, target_cols)

    # column_format_input の安全な調整（空文字列や None を扱う）
    fmt = st.session_state.get("column_format_input", "")
    if not fmt:
        # デフォルト: 全列 'c'
        fmt = "c" * len(new_df.columns)

    if len(fmt) < len(new_df.columns):
        last_char = fmt[-1] if fmt else "c"
        st.session_state.column_format_input = fmt + last_char * (len(new_df.columns) - len(fmt))
    else:
        st.session_state.column_format_input = fmt[:len(new_df.columns)]

    # マージ設定のクリーンアップ
    if "merge_list" in st.session_state:
        st.session_state.merge_list = clean_merges(
            st.session_state.merge_list,
            len(new_df),
            len(new_df.columns)
        )

    st.session_state.df = new_df

    # data_editor をリフレッシュさせるために main_editor を消す
    if "main_editor" in st.session_state:
        try:
            del st.session_state["main_editor"]
        except Exception:
            pass


def update_input_vals(action, axis):
    """行・列ボタンのコールバック"""
    r = st.session_state.get("rows_input", len(st.session_state.df))
    c = st.session_state.get("cols_input", len(st.session_state.df.columns))

    if axis == "row":
        st.session_state.rows_input = r + 1 if action == "add" else max(1, r - 1)
    else:
        st.session_state.cols_input = c + 1 if action == "add" else max(1, c - 1)

    on_shape_change()

# ---------------------------------------------------------
# LaTeX 生成
# ---------------------------------------------------------

def generate_custom_latex(df, merges, caption, label, col_fmt, use_booktabs, center):
    """結合情報を反映した LaTeX を生成して返す"""
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)

    rows, cols = df.shape

    # マージが空でも空リストにする
    merges = merges or []

    skip = np.zeros((rows, cols), dtype=bool)
    merge_map = {}

    for m in merges:
        r, c, rs, cs = m["r"], m["c"], m["rs"], m["cs"]
        # 範囲チェック（越境を無視）
        if r < 0 or c < 0 or r >= rows or c >= cols:
            continue
        merge_map[(r, c)] = (rs, cs)
        for i in range(r, min(r + rs, rows)):
            for j in range(c, min(c + cs, cols)):
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

    # column format が空なら安全なデフォルトを入れる
    if not col_fmt:
        col_fmt = "c" * cols

    lines.append(f"  \\begin{{tabular}}{{{col_fmt}}}")
    lines.append("    " + top)

    # header
    header_cells = [f"\\textbf{{{col}}}" for col in df.columns]
    header_line = " & ".join(header_cells) + " \\\\"
    lines.append("    " + header_line)
    lines.append("    " + mid)

    # body
    for i in range(rows):
        row_cells = []
        for j in range(cols):
            if skip[i, j]:
                continue

            text = str(df.iat[i, j]) if (i < df.shape[0] and j < df.shape[1]) else ""

            if (i, j) in merge_map:
                rs, cs = merge_map[(i, j)]
                # 範囲外にならないように min を取る
                rs_safe = max(1, int(rs))
                cs_safe = max(1, int(cs))
                if rs_safe > 1 and cs_safe > 1:
                    cell = "\\multicolumn{" + str(cs_safe) + "}{c}{\\multirow{" + str(rs_safe) + "}{*}{" + text + "}}"
                elif rs_safe > 1:
                    cell = "\\multirow{" + str(rs_safe) + "}{*}{" + text + "}"
                elif cs_safe > 1:
                    cell = "\\multicolumn{" + str(cs_safe) + "}{c}{" + text + "}"
                else:
                    cell = text
            else:
                cell = text

            row_cells.append(cell)

        lines.append("    " + " & ".join(row_cells) + " \\\\")

    lines.append("    " + bottom)
    lines.append("  \\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)

# ---------------------------------------------------------
# Merge 管理
# ---------------------------------------------------------

def add_merge():
    if "merge_list" not in st.session_state:
        st.session_state.merge_list = []

    try:
        r = int(st.session_state.get("merge_r_input", 1)) - 1
        c = int(st.session_state.get("merge_c_input", 1)) - 1
        rs = int(st.session_state.get("merge_rs_input", 1))
        cs = int(st.session_state.get("merge_cs_input", 1))
    except Exception:
        st.error("結合パラメータが不正です。整数を指定してください。")
        return

    # 範囲チェック（越境は追加しない）
    rows = len(st.session_state.df)
    cols = len(st.session_state.df.columns)
    if r < 0 or c < 0 or r >= rows or c >= cols:
        st.error("結合開始位置が範囲外です。")
        return
    if r + rs > rows or c + cs > cols:
        st.error("結合範囲が表の範囲を超えています。")
        return

    st.session_state.merge_list.append({"r": r, "c": c, "rs": rs, "cs": cs})


def remove_merge(i):
    if "merge_list" not in st.session_state or not st.session_state.merge_list:
        return
    if 0 <= i < len(st.session_state.merge_list):
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

# column format の初期化（空や None を回避）
if "column_format_input" not in st.session_state:
    st.session_state.column_format_input = "c" * len(st.session_state.df.columns)

# ---------------------------------------------------------
# サイドバー
# ---------------------------------------------------------

st.sidebar.title("出力設定")

use_booktabs = st.sidebar.checkbox("Booktabs（きれいな罫線）", value=True)
center_table = st.sidebar.checkbox("中央揃え", value=True)

caption = st.sidebar.text_input("キャプション", "")
label = st.sidebar.text_input("ラベル", "tab:mytable")

column_format = st.sidebar.text_input("列フォーマット", key="column_format_input")

# ---------------------------------------------------------
# UI
# ---------------------------------------------------------

st.title("LaTeX表作成ツール（結合対応）")

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

st.divider()

# ---------------------------------------------------------
# 2. 列名編集（前に移動）
# ---------------------------------------------------------

st.write("### 2. 列名の編集")

cols_ui = st.columns(min(4, len(st.session_state.df.columns)))
new_names = []
for i, name in enumerate(st.session_state.df.columns):
    ui = cols_ui[i % len(cols_ui)]
    new_names.append(ui.text_input(f"列 {i+1}", value=name, key=f"rename_col_{i}"))

if st.button("列名を更新", key="rename_btn"):
    # 空欄防止: 空文字列が入っていたら既存名前を保持
    safe_names = []
    for i, n in enumerate(new_names):
        safe_names.append(n if n else st.session_state.df.columns[i])
    st.session_state.df.columns = safe_names
    if "main_editor" in st.session_state:
        try:
            del st.session_state["main_editor"]
        except Exception:
            pass
    st.experimental_rerun()

st.divider()

# ---------------------------------------------------------
# 3. セル結合設定
# ---------------------------------------------------------

with st.expander("🔗 セルの結合設定"):

    r_col, c_col, rs_col, cs_col, add_col = st.columns([1, 1, 1, 1, 1])

    with r_col:
        st.number_input("行", 1, st.session_state.rows_input, 1, key="merge_r_input")
    with c_col:
        st.number_input("列", 1, st.session_state.cols_input, 1, key="merge_c_input")
    with rs_col:
        st.number_input("高さ (RowSpan)", 1, 20, 1, key="merge_rs_input")
    with cs_col:
        st.number_input("幅 (ColSpan)", 1, 20, 1, key="merge_cs_input")
    with add_col:
        st.write(""); st.write("")
        st.button("追加", key="merge_add", on_click=add_merge)

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
# 4.5 結合の可視化（色付き表示）
# ---------------------------------------------------------

st.write("### 🔍 セル結合の可視化")

def visualize_merges(df, merges):
    """pandas.Styler を作り、HTML を出力する（Streamlit で安全に表示するため）"""
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)

    rows, cols = df.shape
    # デフォルトは空文字列（スタイル無し）
    color_map = [["" for _ in range(cols)] for _ in range(rows)]

    # 範囲外の merge を無視するためにクリーンアップ
    merges = clean_merges(merges, rows, cols)

    for idx, m in enumerate(merges):
        r, c, rs, cs = m["r"], m["c"], m["rs"], m["cs"]

        # 範囲内に切り詰めて色付け
        for i in range(r, min(r + rs, rows)):
            for j in range(c, min(c + cs, cols)):
                color_map[i][j] = "background-color: #fff7b3"  # 薄黄色
        # 起点はやや濃い色
        if 0 <= r < rows and 0 <= c < cols:
            color_map[r][c] = "background-color: #ffe86e"

    # pandas Styler 用の関数：axis=None で全セルに配列を返す
    styler = df.style
    styler = styler.apply(lambda _: color_map, axis=None)
    # 既定の CSS を調整したい場合は .set_table_styles なども使える

    return styler

if st.session_state.merge_list:
    try:
        styled = visualize_merges(st.session_state.df, st.session_state.merge_list)
        # Streamlit は Styler の HTML を直接表示できるので unsafe_allow_html を使用
        st.write(styled.to_html(), unsafe_allow_html=True)
    except Exception as e:
        # 失敗時は通常の DataFrame を出す
        st.warning("可視化のレンダリングに失敗しました。以下は通常表示です。")
        st.dataframe(st.session_state.df, use_container_width=True)
else:
    st.info("結合が設定されていません。")

st.divider()

# ---------------------------------------------------------
# 5. LaTeX生成
# ---------------------------------------------------------

st.write("### 4. LaTeXコード生成")

if st.button("LaTeXコードを生成", key="generate_latex", type="primary"):
    # data_editor の編集結果を保存
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
