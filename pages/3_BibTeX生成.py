import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import style
import auth_manager

def generate_bibtex(entry_type, key, fields):
    """BibTeXエントリを生成する関数"""
    bibtex = f"@{entry_type}{{{key},\n"
    for field, value in fields.items():
        if value:
            # タイトルはLaTeXで勝手に小文字化されるのを防ぐため二重括弧で囲む
            if field == 'title':
                bibtex += f"  {field} = {{{{{value}}}}},\n"
            elif field == 'howpublished' and value.startswith(('http://', 'https://')) and '\\url' not in value:
                bibtex += f"  {field} = {{\\url{{{value}}}}},\n"
            else:
                bibtex += f"  {field} = {{{value}}},\n"
    bibtex += "}"
    return bibtex

def main():
    # ページ設定は各ファイルの先頭で行います
    st.set_page_config(page_title="BibTeX Generator")
    
    # --- 認証 & アナリティクス ---
    auth_manager.check_auth()
    # -------------------------
    
    style.apply_custom_style()
    
    st.title("BibTeX Generator")
    st.markdown("文献情報を入力して、LaTeX用のBibTeXコードを自動生成します。")

    # サイドバーで設定
    st.sidebar.header("設定")
    # エントリータイプの定義（表示名とのマッピング）
    ENTRY_TYPES = {
        "article": "論文 (Article)",
        "book": "書籍 (Book)",
        "inproceedings": "会議録 (Inproceedings)",
        "phdthesis": "博士論文 (PhdThesis)",
        "techreport": "技術報告書 (TechReport)",
        "website": "ウェブサイト (Website)",
        "misc": "その他 (Misc)"
    }

    entry_type = st.sidebar.selectbox(
        "文献タイプを選択",
        options=list(ENTRY_TYPES.keys()),
        format_func=lambda x: ENTRY_TYPES[x]
    )
    
    citation_key = st.sidebar.text_input("引用するときのラベル", value="ref_key", help="文献を一意に識別するためのIDです (例: author2023)")

    # 出力設定
    st.sidebar.markdown("---")
    st.sidebar.header("出力設定")
    bib_file_path = st.sidebar.text_input("保存先ファイルパス(.bib)を入力してください。(新しいファイルを作成する場合、保存ファイル名)", value="references.bib", help="絶対パスまたは相対パスを入力してください。ファイルがない場合は新規作成されます。")

    st.header(f"{ENTRY_TYPES[entry_type]} の情報を入力")

    # 共通フィールドと固有フィールドの定義
    fields = {}
    
    # よく使われるフィールドを優先的に表示
    col1, col2 = st.columns(2)
    
    with col1:
        fields['author'] = st.text_input("著者 (Author)", help="例: Yamada, Taro and Smith, John")
        fields['title'] = st.text_input("タイトル (Title)")
        fields['year'] = st.text_input("発行年 (Year)")

    with col2:
        if entry_type == 'article':
            fields['journal'] = st.text_input("ジャーナル名 (Journal)")
            fields['volume'] = st.text_input("巻 (Volume)")
            fields['number'] = st.text_input("号 (Number)")
            fields['pages'] = st.text_input("ページ (Pages)")
        elif entry_type == 'book':
            fields['publisher'] = st.text_input("出版社 (Publisher)")
            fields['address'] = st.text_input("出版地 (Address)")
            fields['edition'] = st.text_input("版 (Edition)")
        elif entry_type == 'inproceedings':
            fields['booktitle'] = st.text_input("会議名/書籍名 (Booktitle)")
            fields['editor'] = st.text_input("編集者 (Editor)")
            fields['organization'] = st.text_input("組織 (Organization)")
            fields['pages'] = st.text_input("ページ (Pages)")
        elif entry_type == 'website' or entry_type == 'misc':
            fields['howpublished'] = st.text_input("公開方法/URL (Howpublished)", help="\\url{...} 形式推奨")
            fields['note'] = st.text_input("備考 (Note)", help="アクセス日など")
        
        # 共通の追加フィールド
        if 'month' not in fields:
            fields['month'] = st.text_input("月 (Month)")
        
    # その他のフィールド（エキスパンダーで隠す）
    with st.expander("その他のフィールドを追加"):
        fields['doi'] = st.text_input("DOI")
        fields['url'] = st.text_input("URL")
        fields['abstract'] = st.text_area("概要 (Abstract)")

    # 生成ボタン
    if st.button("BibTeXを生成して保存", type="primary"):
        if not citation_key:
            st.error("引用キーを入力してください。")
        elif not fields.get('title'):
            st.warning("タイトルは必須項目です（推奨）。")
        else:
            bib_output = generate_bibtex(entry_type, citation_key, fields)
            
            if not bib_file_path:
                st.error("保存先ファイルパスを入力してください。")
            else:
                try:
                    import os
                    # ファイルが存在するか確認して、改行を入れるか判断
                    mode = 'a' if os.path.exists(bib_file_path) else 'w'
                    prefix = "\n" if os.path.exists(bib_file_path) else ""
                    
                    with open(bib_file_path, mode, encoding='utf-8') as f:
                        f.write(prefix + bib_output)
                    
                    st.success(f"保存しました: {bib_file_path}")
                    st.code(bib_output, language='latex')
                except Exception as e:
                    st.error(f"ファイルの保存中にエラーが発生しました: {e}")

    # --- 本番環境（Cloud）用のダウンロード機能 ---
    # Streamlit Cloudなどのサーバー環境では、ローカルに保存したファイルに直接アクセスできないため
    # ダウンロードボタンを提供する必要があります。
    if bib_file_path and os.path.exists(bib_file_path):
        st.divider()
        st.subheader("📁 ファイルのダウンロード")
        st.caption("サーバー上に保存されたBibTeXファイルをダウンロードします。（これまでに追記された内容を含む）")
        
        with open(bib_file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
            
        st.download_button(
            label="📥 references.bib をダウンロード",
            data=file_content,
            file_name=os.path.basename(bib_file_path),
            mime="text/plain",
            type="secondary",
            use_container_width=True
        )

if __name__ == "__main__":
    main()