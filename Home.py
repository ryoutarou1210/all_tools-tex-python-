import streamlit as st
import style

# ページ設定
st.set_page_config(
    page_title="Science Tools",
    layout="wide"
)

# スタイル適用
style.apply_custom_style()

# --- ヘッダーエリア ---
col1, col2 = st.columns([3, 1])
with col1:
    st.title("Science Tools Hub")
    st.markdown("""
    <div style='color: #6B7280; font-size: 1.1em; margin-bottom: 20px;'>
    レポート作成、データ分析、文献管理を簡単に。
    </div>
    """, unsafe_allow_html=True)

# --- ツール選択エリア（カードデザイン） ---
st.markdown("### Tools(サイドバーから選択)")

# 3カラムレイアウトでツールを並べる
col_tool1, col_tool2, col_tool3 = st.columns(3)

with col_tool1:
    with st.container():
        st.success("データ可視化")
        st.markdown("**散布図 & 近似直線**")
        st.caption("実験データをアップロードして、美しいグラフと近似直線を描画・保存します。")

with col_tool2:
    with st.container():
        st.warning("表作成")
        st.markdown("**LaTeX Table Maker**")
        st.caption("Excelライクな操作でLaTeXの表コードを出力。Booktabs記法に完全対応。")

with col_tool3:
    with st.container():
        st.info("文献管理")
        st.markdown("**BibTeX Generator**")
        st.caption("論文情報を入力してBibTeXコードを即座に生成。フォーマットミスを防ぎます。")

st.divider()

# --- 更新情報やTips ---
with st.expander("Tips: 使いこなしのヒント", expanded=True):
    st.markdown("""
    - **グラフツール**: エクセルファイル(.xlsx)をそのままドラッグ&ドロップできます。
    - **表ツール**: 列名はダブルクリックで変更できませんが、下部の入力欄で変更可能です。
    - **BibTeX**: Google Scholarの引用ボタンからコピーするより、ここで整形した方が統一感が出ます。

    """)

