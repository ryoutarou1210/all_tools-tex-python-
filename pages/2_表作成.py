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

st.set_page_config(page_title="LaTeX表作成ツール", layout="wide")

style.apply_custom_style()

# --- リサイズ処理ロジック ---
def resize_dataframe(df, target_rows, target_cols):
    """
    データフレームを指定のサイズにリサイズします。
    - 縮小: 右・下を削除（左上のデータを保持）
    - 拡大: 右・下に空の行/列を追加
    """
    current_rows, current_cols = df.shape

    # 1. 行の調整
    if target_rows < current_rows:
        # 縮小: 下をカット
        df = df.iloc[:target_rows, :]
    elif target_rows > current_rows:
        # 拡大: 下に追加
        rows_to_add = target_rows - current_rows
        # 列構造を維持して空行を作成
        new_rows = pd.DataFrame([[""] * current_cols] * rows_to_add, columns=df.columns)
        df = pd.concat([df, new_rows], ignore_index=True)

    # 2. 列の調整
    current_rows, current_cols = df.shape # 行変更後のサイズで再取得
    
    if target_cols < current_cols:
        # 縮小: 右をカット
        df = df.iloc[:, :target_cols]
    elif target_cols > current_cols:
        # 拡大: 右に追加
        cols_to_add = target_cols - current_cols
        for _ in range(cols_to_add):
            # 新しい列名を作成 (列 N)
            new_col_name = f"列 {len(df.columns) + 1}"
            # 重複回避
            base_name = new_col_name
            counter = 1
            while new_col_name in df.columns:
                new_col_name = f"{base_name}_{counter}"
                counter += 1
            df[new_col_name] = ""
            
    return df

# --- コールバック: サイズ変更時 ---
def on_shape_change():
    """
    数値入力やボタン操作でサイズが変わったときに呼ばれます。
    エディタの最新内容を取り込んでからリサイズします。
    """
    # 1. 現在の編集内容を確保 (これがデータ消失防止の鍵)
    # session_stateにeditorの内容があればそれを正とする
    if "main_editor" in st.session_state and isinstance(st.session_state["main_editor"], pd.DataFrame):
        current_df = st.session_state["main_editor"]
    else:
        current_df = st.session_state.df

    # 2. 目標サイズの取得
    target_rows = st.session_state.rows_input
    target_cols = st.session_state.cols_input

    # 3. リサイズ実行 (右下追加・削除ロジック)
    new_df = resize_dataframe(current_df, target_rows, target_cols)

    # 4. フォーマット調整 (列数に合わせて cccc... を調整)
    current_fmt = st.session_state.get("column_format_input", "c" * len(new_df.columns))
    if len(current_fmt) < len(new_df.columns):
        last_char = current_fmt[-1] if current_fmt else 'c'
        st.session_state.column_format_input = current_fmt + last_char * (len(new_df.columns) - len(current_fmt))
    elif len(current_fmt) > len(new_df.columns):
        st.session_state.column_format_input = current_fmt[:len(new_df.columns)]

    # 5. 保存とリセット
    st.session_state.df = new_df
    # データエディタを強制リフレッシュさせるためにキーを削除
    if "main_editor" in st.session_state:
        del st.session_state["main_editor"]

# --- コールバック: ボタン操作用 ---
def update_input_vals(action, axis):
    """
    ボタンが押されたら数値入力用の変数を更新し、
    その後にリサイズ処理(on_shape_change)を呼び出す
    """
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
    
    # 値更新後にリサイズロジックを実行
    on_shape_change()

# ----------------------------------

# 初期化
if 'df' not in st.session_state:
    init_rows, init_cols = 5, 4
    data = np.full((init_rows, init_cols), "")
    columns = [f"列 {i+1}" for i in range(init_cols)]
    st.session_state.df = pd.DataFrame(data, columns=columns)

# 行数・列数の初期値を同期
if "rows_input" not in st.session_state:
    st.session_state.rows_input = len(st.session_state.df)
if "cols_input" not in st.session_state:
    st.session_state.cols_input = len(st.session_state.df.columns)

# エディタの内容をdfに同期 (リサイズ操作以外での更新用)
if "main_editor" in st.session_state:
    edited_data = st.session_state["main_editor"]
    if isinstance(edited_data, pd.DataFrame):
        # 形状が変わっていない＝ただのセル編集の時はそのまま反映
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

# --- プロフィール表示（最後）---
auth_manager.check_auth()
# ----------------------------

st.title("LaTeX表作成ツール")

# --- 直感的な行列操作パネル ---
st.write("##### テーブルサイズの変更")
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

# データエディタ
# num_rows="fixed" でUI上での行追加・削除は禁止し、ボタン操作に一本化
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
