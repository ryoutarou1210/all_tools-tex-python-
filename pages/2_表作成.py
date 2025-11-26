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
    # ローカル動作確認用ダミー
    class style:
        @staticmethod
        def apply_custom_style(): pass
    class auth_manager:
        @staticmethod
        def check_auth(): pass

st.set_page_config(page_title="LaTeX表作成ツール (結合対応版)", layout="wide")

style.apply_custom_style()

# --- リサイズ処理ロジック ---
def resize_dataframe(df, target_rows, target_cols):
    """
    データフレームを指定のサイズにリサイズします。
    """
    current_rows, current_cols = df.shape

    # 1. 行の調整
    if target_rows < current_rows:
        df = df.iloc[:target_rows, :]
    elif target_rows > current_rows:
        rows_to_add = target_rows - current_rows
        new_rows = pd.DataFrame([[""] * current_cols] * rows_to_add, columns=df.columns)
        df = pd.concat([df, new_rows], ignore_index=True)

    # 2. 列の調整
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

# --- 結合情報のクリーンアップ ---
def clean_merges(merges, rows, cols):
    """
    テーブルサイズが縮小された際、範囲外になった結合設定を削除します。
    """
    valid_merges = []
    for m in merges:
        # 開始位置が範囲内 かつ 終了位置も範囲内であるものだけ残す
        r_end = m['r'] + m['rs']
        c_end = m['c'] + m['cs']
        if r_end <= rows and c_end <= cols:
            valid_merges.append(m)
    return valid_merges

# --- コールバック: サイズ変更時 ---
def on_shape_change():
    """
    数値入力やボタン操作でサイズが変わったときに呼ばれます。
    """
    if "main_editor" in st.session_state and isinstance(st.session_state["main_editor"], pd.DataFrame):
        current_df = st.session_state["main_editor"]
    else:
        current_df = st.session_state.df

    target_rows = st.session_state.rows_input
    target_cols = st.session_state.cols_input

    new_df = resize_dataframe(current_df, target_rows, target_cols)

    # フォーマット調整
    current_fmt = st.session_state.get("column_format_input", "c" * len(new_df.columns))
    if len(current_fmt) < len(new_df.columns):
        last_char = current_fmt[-1] if current_fmt else 'c'
        st.session_state.column_format_input = current_fmt + last_char * (len(new_df.columns) - len(current_fmt))
    elif len(current_fmt) > len(new_df.columns):
        st.session_state.column_format_input = current_fmt[:len(new_df.columns)]

    # 結合設定のクリーンアップ
    if "merge_list" in st.session_state:
        st.session_state.merge_list = clean_merges(st.session_state.merge_list, target_rows, target_cols)

    st.session_state.df = new_df
    if "main_editor" in st.session_state:
        del st.session_state["main_editor"]

# --- コールバック: ボタン操作用 ---
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

# --- カスタムLaTeX生成関数（結合対応） ---
def generate_custom_latex(df, merges, caption, label, col_fmt, use_booktabs, center):
    """
    Pandasのto_latexを使わず、結合情報を反映してLaTeXコードを生成します。
    """
    rows, cols = df.shape
    
    # マスクを作成（Trueならそのセルは結合されて隠れているので出力しない）
    skip_mask = np.zeros((rows, cols), dtype=bool)
    
    # 結合情報のマップを作成 {(r, c): (rs, cs)}
    merge_map = {}
    for m in merges:
        r, c, rs, cs = m['r'], m['c'], m['rs'], m['cs']
        merge_map[(r, c)] = (rs, cs)
        # 範囲をスキップ対象にする（左上以外）
        for i in range(r, r + rs):
            for j in range(c, c + cs):
                if i == r and j == c:
                    continue
                skip_mask[i, j] = True

    lines = []
    
    # プリアンブル系
    lines.append(f"\\begin{{table}}[htbp]")
    if center:
        lines.append(f"  \\centering")
    
    # キャプション位置（上）
    if caption:
        lines.append(f"  \\caption{{{caption}}}")
    if label:
        lines.append(f"  \\label{{{label}}}")
        
    lines.append(f"  \\begin{{tabular}}{{{col_fmt}}}")
    lines.append(f"    {'\\toprule' if use_booktabs else '\\hline'}")

    # ヘッダー行
    header_cells = []
    for col in df.columns:
        header_cells.append(f"\\textbf{{{col}}}")
    lines.append(f"    {' & '.join(header_cells)} \\\\")
    lines.append(f"    {'\\midrule' if use_booktabs else '\\hline'}")

    # データ行
    for i in range(rows):
        row_cells = []
        for j in range(cols):
            if skip_mask[i, j]:
                continue
            
            content = str(df.iloc[i, j])
            
            # 結合の開始地点かチェック
            if (i, j) in merge_map:
                rs, cs = merge_map[(i, j)]
                
                # LaTeXの作成: \multicolumn{cs}{c}{\multirow{rs}{*}{Content}}
                # ※配置は簡易的に 'c' 固定、あるいは 'l' など調整可能ですが、
                #   ここでは中央揃えをデフォルトにします。
                
                # multirowだけの場合
                if cs == 1 and rs > 1:
                    cell_latex = f"\\multirow{{{rs}}}{{*}}{{{content}}}"
                # multicolumnだけの場合
                elif rs == 1 and cs > 1:
                    cell_latex = f"\\multicolumn{{{cs}}}{{c}}{{{content}}}"
                # 両方の場合
                elif rs > 1 and cs > 1:
                    cell_latex = f"\\multicolumn{{{cs}}}{{c}}{{\\multirow{{{rs}}}{{*}}{{{content}}}}}"
                else:
                    cell_latex = content
                
                row_cells.append(cell_latex)
            else:
                row_cells.append(content)
        
        lines.append(f"    {' & '.join(row_cells)} \\\\")
        
        # 罫線の処理（multirowがある場合は \cline を使うのが丁寧だが、簡易的に \hline/\bottomrule を出力）
        # 行ごとの罫線は booktabs利用時は通常データ行間には引かないことが多いですが、
        # 従来のコードに合わせて最終行以外には何もせず、最後にbottomrule
    
    lines.append(f"    {'\\bottomrule' if use_booktabs else '\\hline'}")
    lines.append(f"  \\end{{tabular}}")
    lines.append(f"\\end{{table}}")
    
    return "\n".join(lines)

# --- コールバック: 結合追加 ---
def add_merge():
    r = st.session_state.merge_r_input - 1 # 0-indexedに変換
    c = st.session_state.merge_c_input - 1
    rs = st.session_state.merge_rs_input
    cs = st.session_state.merge_cs_input
    
    # 既存の結合と重複チェック（簡易的）
    # 完全な重複チェックは複雑になるため、ここでは単純追加
    new_merge = {'r': r, 'c': c, 'rs': rs, 'cs': cs}
    
    if "merge_list" not in st.session_state:
        st.session_state.merge_list = []
        
    st.session_state.merge_list.append(new_merge)

def remove_merge(index):
    if "merge_list" in st.session_state:
        st.session_state.merge_list.pop(index)

# ----------------------------------

# 初期化
if 'df' not in st.session_state:
    init_rows, init_cols = 5, 4
    data = np.full((init_rows, init_cols), "")
    columns = [f"列 {i+1}" for i in range(init_cols)]
    st.session_state.df = pd.DataFrame(data, columns=columns)

if 'merge_list' not in st.session_state:
    st.session_state.merge_list = []

# 行数・列数の初期値を同期
if "rows_input" not in st.session_state:
    st.session_state.rows_input = len(st.session_state.df)
if "cols_input" not in st.session_state:
    st.session_state.cols_input = len(st.session_state.df.columns)

# エディタの内容をdfに同期
if "main_editor" in st.session_state:
    edited_data = st.session_state["main_editor"]
    if isinstance(edited_data, pd.DataFrame):
        if edited_data.shape == st.session_state.df.shape:
            st.session_state.df = edited_data

if not isinstance(st.session_state.df, pd.DataFrame):
    st.session_state.df = pd.DataFrame(st.session_state.df)


# --- サイドバー設定 ---
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

# --- プロフィール表示（最後）---
auth_manager.check_auth()
# ----------------------------

st.title("LaTeX表作成ツール (結合対応)")

# --- 直感的な行列操作パネル ---
st.write("##### 1. テーブルサイズの変更")
ctrl_col1, ctrl_col2 = st.columns(2)

# 行操作
with ctrl_col1:
    st.caption("行数 (Rows)")
    r_c1, r_c2, r_c3 = st.columns([1, 2, 1])
    with r_c1:
        st.button("➖", key="del_row", on_click=update_input_vals, args=('del', 'row'), use_container_width=True)
    with r_c2:
        st.number_input(
            "Rows", 
            min_value=1, 
            key="rows_input", 
            on_change=on_shape_change, 
            label_visibility="collapsed"
        )
    with r_c3:
        st.button("➕", key="add_row", on_click=update_input_vals, args=('add', 'row'), type="primary", use_container_width=True)

# 列操作
with ctrl_col2:
    st.caption("列数 (Cols)")
    c_c1, c_c2, c_c3 = st.columns([1, 2, 1])
    with c_c1:
        st.button("➖", key="del_col", on_click=update_input_vals, args=('del', 'col'), use_container_width=True)
    with c_c2:
        st.number_input(
            "Cols", 
            min_value=1, 
            key="cols_input", 
            on_change=on_shape_change, 
            label_visibility="collapsed"
        )
    with c_c3:
        st.button("➕", key="add_col", on_click=update_input_vals, args=('add', 'col'), type="primary", use_container_width=True)

st.divider()

# --- 結合マネージャー ---
with st.expander("🔗 セルの結合設定 (Merge Cells)", expanded=False):
    st.caption("結合したい範囲を指定してください。結合後のセルの内容は、左上のセルの値が使用されます。")
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
        st.write("") # Spacer
        st.write("")
        st.button("結合を追加", on_click=add_merge, use_container_width=True)

    # 現在の結合リスト表示
    if st.session_state.merge_list:
        st.write("現在の結合リスト:")
        for idx, m in enumerate(st.session_state.merge_list):
            cols_disp = st.columns([4, 1])
            with cols_disp[0]:
                st.text(f"行:{m['r']+1}, 列:{m['c']+1} から 縦:{m['rs']} x 横:{m['cs']}")
            with cols_disp[1]:
                st.button("削除", key=f"del_merge_{idx}", on_click=remove_merge, args=(idx,))
    else:
        st.info("結合設定はありません")

st.divider()

# データエディタ
st.write("##### 2. データの編集")
edited_df = st.data_editor(st.session_state.df, num_rows="fixed", use_container_width=True, key="main_editor")
st.caption("※結合設定をしたエリアも、ここでは通常のグリッドとして表示されます。左上のセルに文字を入力してください。")

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
        # フォーマット文字列の長さチェック（結合があると一概には言えませんが、基本チェックとして残す）
        if len(active_format) != len(edited_df.columns):
             st.warning(f"注意: 列数({len(edited_df.columns)})とフォーマット指定({len(active_format)})の長さが一致していません。")
        
        # カスタム生成関数を使用
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
            st.info("ヒント: `\\multirow`を使用しているため、ドキュメントのヘッダーに `\\usepackage{multirow}` を記述してください。")
            
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
