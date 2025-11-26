import streamlit as st
import sys
import os

# パス設定（環境に合わせて調整してください）
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import style
import auth_manager

def generate_bibtex(entry_type, key, fields):
    bibtex = f"@{entry_type}{{{key},\n"
    for field, value in fields.items():
        if value:
            if field == 'title': 
                bibtex += f"  {field} = {{{{{value}}}}},\n"
            elif field == 'howpublished' and value.startswith(('http', 'https')) and '\\url' not in value:
                bibtex += f"  {field} = {{\\url{{{value}}}}},\n"
            else: 
                bibtex += f"  {field} = {{{value}}},\n"
    bibtex += "}"
    return bibtex

def main():
    st.set_page_config(page_title="BibTeX Generator")
        
    style.apply_custom_style()
    st.title("BibTeX Generator")

    st.sidebar.header("設定")
    ENTRY_TYPES = {
        "article": "論文 (Article)", "book": "書籍 (Book)",
        "inproceedings": "会議録 (Inproceedings)", "phdthesis": "博士論文 (PhdThesis)",
        "techreport": "技術報告書 (TechReport)", "website": "ウェブサイト (Website)", "misc": "その他 (Misc)"
    }
    entry_type = st.sidebar.selectbox("文献タイプ", list(ENTRY_TYPES.keys()), format_func=lambda x: ENTRY_TYPES[x])
    citation_key = st.sidebar.text_input("引用ラベル", "ref_key")

    st.sidebar.markdown("---")
    bib_file_path = st.sidebar.text_input("保存先パス", "references.bib")

    # 1. 認証チェック
    auth_manager.check_auth()

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

    # --- 生成・保存ボタンの処理 ---
    if st.button("生成・保存", type="primary"):
        if not citation_key or not fields.get('title'):
            st.warning("引用キーとタイトルは必須です")
        elif not bib_file_path:
            st.error("保存先パスを指定してください")
        else:
            bib_output = generate_bibtex(entry_type, citation_key, fields)
            
            try:
                # ファイルが存在するか確認
                file_exists = os.path.exists(bib_file_path)
                
                if file_exists:
                    # 既にファイルがある場合：重複キーチェックを行う
                    with open(bib_file_path, "r", encoding='utf-8') as f:
                        existing_content = f.read()
                        # BibTeXのキー定義部分（例: @article{key,）を簡易チェック
                        if f"{{{citation_key}," in existing_content:
                            st.error(f"エラー: 引用キー '{citation_key}' は既にファイル内に存在します。別のキーを指定してください。")
                            st.stop() # 処理を中断
                    
                    mode = 'a' # 追記モード
                    write_content = "\n" + bib_output # 前のデータとくっつかないように改行を入れる
                    msg = "既存ファイルに追記しました"
                else:
                    # ファイルがない場合：新規作成
                    mode = 'w' # 書き込みモード
                    write_content = bib_output
                    msg = "新しいファイルを作成して保存しました"

                # ファイル書き込み実行
                with open(bib_file_path, mode, encoding='utf-8') as f:
                    f.write(write_content)

                st.success(msg)
                st.code(bib_output, language='latex')

            except Exception as e:
                st.error(f"ファイル保存エラー: {e}")

    # --- ダウンロードボタン ---
    if bib_file_path and os.path.exists(bib_file_path):
        st.divider()
        with open(bib_file_path, "r", encoding="utf-8") as f: content = f.read()
        st.download_button("📥 .bibファイルをダウンロード", content, os.path.basename(bib_file_path))

if __name__ == "__main__":
    main()
