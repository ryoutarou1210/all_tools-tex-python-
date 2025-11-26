import streamlit as st
import sys
import os

# Webアプリ用にパス調整（既存コードのまま）
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import style
import auth_manager

def generate_bibtex_entry(entry_type, key, fields):
    bibtex = f"@{entry_type}{{{key},\n"
    for field, value in fields.items():
        if value:
            if field == 'title': 
                bibtex += f"  {field} = {{{{{value}}}}},\n"
            elif field == 'howpublished' and value.startswith(('http', 'https')) and '\\url' not in value:
                bibtex += f"  {field} = {{\\url{{{value}}}}},\n"
            else: 
                bibtex += f"  {field} = {{{value}}},\n"
    bibtex += "}\n" # 末尾に改行を入れておく
    return bibtex

def main():
    st.set_page_config(page_title="BibTeX Generator (Web版)")
    style.apply_custom_style()
    st.title("BibTeX Generator (Web版)")

    # 1. 認証チェック
    auth_manager.check_auth()
    # --- サイドバー設定 ---
    st.sidebar.header("設定")
    ENTRY_TYPES = {
        "article": "論文 (Article)", "book": "書籍 (Book)",
        "inproceedings": "会議録 (Inproceedings)", "phdthesis": "博士論文 (PhdThesis)",
        "techreport": "技術報告書 (TechReport)", "website": "ウェブサイト (Website)", "misc": "その他 (Misc)"
    }
    entry_type = st.sidebar.selectbox("文献タイプ", list(ENTRY_TYPES.keys()), format_func=lambda x: ENTRY_TYPES[x])
    citation_key = st.sidebar.text_input("引用ラベル (ユニークなID)", "ref_key")

    # --- ファイルアップロード機能 ---
    st.markdown("### 1. 既存の.bibファイルをアップロード（追記したい場合）")
    uploaded_file = st.file_uploader("手元の .bib ファイルをここにドラッグ＆ドロップ", type=['bib'])
    
    existing_content = ""
    if uploaded_file is not None:
        # アップロードされたファイルを読み込む
        stringio = uploaded_file.getvalue().decode("utf-8")
        existing_content = stringio
        st.success(f"`{uploaded_file.name}` を読み込みました。ここに新しい文献を追記します。")
    else:
        st.warning("ファイルがアップロードされていない場合は、新規作成となります。")

    st.markdown("---")
    st.markdown("### 2. 文献情報の入力")
    
    st.header(f"{ENTRY_TYPES[entry_type]} 情報")
    fields = {}
    col1, col2 = st.columns(2)
    with col1:
        fields['author'] = st.text_input("著者")
        fields['title'] = st.text_input("タイトル")
        fields['year'] = st.text_input("発行年")
    with col2:
        if entry_type == 'article':
            fields['journal'] = st.text_input("ジャーナル")
            fields['volume'] = st.text_input("巻")
            fields['number'] = st.text_input("号")
            fields['pages'] = st.text_input("ページ")
        elif entry_type == 'book':
            fields['publisher'] = st.text_input("出版社")
            fields['address'] = st.text_input("出版地")
        elif entry_type == 'inproceedings':
            fields['booktitle'] = st.text_input("会議名")
        elif entry_type in ['website', 'misc']:
            fields['howpublished'] = st.text_input("URL/公開方法")
            fields['note'] = st.text_input("備考")
        if 'month' not in fields: fields['month'] = st.text_input("月")

    with st.expander("その他"):
        fields['doi'] = st.text_input("DOI")
        fields['url'] = st.text_input("URL")
        fields['abstract'] = st.text_area("概要")

    # --- 生成処理 ---
    new_bib_entry = ""
    combined_content = ""
    
    # プレビュー用のコンテナ
    result_container = st.container()

    if st.button("生成する", type="primary"):
        if not citation_key or not fields.get('title'):
            st.warning("引用キーとタイトルは必須です")
        else:
            # 重複チェック
            if f"{{{citation_key}," in existing_content:
                st.error(f"エラー: 引用キー '{citation_key}' はアップロードされたファイル内に既に存在します。")
            else:
                # 新しいエントリを作成
                new_bib_entry = generate_bibtex_entry(entry_type, citation_key, fields)
                
                # 結合処理（改行を綺麗に入れる）
                if existing_content:
                    if not existing_content.endswith("\n"):
                        combined_content = existing_content + "\n\n" + new_bib_entry
                    elif not existing_content.endswith("\n\n"):
                        combined_content = existing_content + "\n" + new_bib_entry
                    else:
                        combined_content = existing_content + new_bib_entry
                else:
                    combined_content = new_bib_entry

                # 結果表示とダウンロードボタン
                with result_container:
                    st.success("生成完了！以下のボタンからダウンロードしてください。")
                    
                    st.text("今回追加される内容:")
                    st.code(new_bib_entry, language='latex')
                    
                    # ダウンロードファイル名の決定
                    dl_filename = uploaded_file.name if uploaded_file else "references.bib"
                    
                    st.download_button(
                        label=f"更新された {dl_filename} をダウンロード",
                        data=combined_content,
                        file_name=dl_filename,
                        mime="text/plain"
                    )

if __name__ == "__main__":
    main()
