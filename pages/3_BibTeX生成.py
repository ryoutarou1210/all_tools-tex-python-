import streamlit as st
import sys
import os

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
    
    citation_key = st.sidebar.text_input("引用ラベル (ユニークなID)", "")

    st.sidebar.markdown("---")
    
    # パス入力（Windowsのパスをそのまま貼り付けても大丈夫なようにします）
    raw_path = st.sidebar.text_input("保存先パス", r"C:\Users\ryout\OneDrive\ドキュメント\専攻実験レポート\テーマF\テーマF最終レポ\references2.bib")
    
    # 【改良】パスの前後の引用符（"や'）を削除し、余計なスペースも消す
    bib_file_path = raw_path.strip('"').strip("'").strip()

    # デバッグ表示：実際にどこに保存しようとしているか確認
    st.sidebar.caption(f"📂 保存予定地:\n{bib_file_path}")

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

    if st.button("生成・保存", type="primary"):
        if not citation_key or not fields.get('title'):
            st.warning("⚠️ 引用キーとタイトルは必須です")
        elif not bib_file_path:
            st.error("⚠️ 保存先パスを指定してください")
        else:
            bib_output = generate_bibtex(entry_type, citation_key, fields)
            
            try:
                # 【改良】保存先のフォルダが存在しない場合、自動的に作成する
                directory = os.path.dirname(bib_file_path)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                    st.info(f"フォルダが存在しなかったため作成しました: {directory}")

                # ファイルが存在するか確認
                if os.path.exists(bib_file_path):
                    # 読み込んで重複チェック
                    with open(bib_file_path, "r", encoding='utf-8') as f:
                        existing_content = f.read()
                    
                    if f"{{{citation_key}," in existing_content:
                        st.error(f"⛔ エラー: 引用キー '{citation_key}' は既にファイル内に存在します。別のキーに変更してください。")
                        st.stop()
                    
                    # 追記モード
                    mode = 'a'
                    prefix = ""
                    # 改行処理を丁寧に行う
                    if existing_content and not existing_content.endswith("\n"):
                        prefix = "\n\n"
                    elif existing_content and not existing_content.endswith("\n\n"):
                        prefix = "\n"
                    
                    write_content = prefix + bib_output
                    msg = f"✅ {os.path.basename(bib_file_path)} に追記しました"
                else:
                    # 新規作成モード
                    mode = 'w'
                    write_content = bib_output
                    msg = f"✅ 新しく {os.path.basename(bib_file_path)} を作成して保存しました"

                # 書き込み実行
                with open(bib_file_path, mode, encoding='utf-8') as f:
                    f.write(write_content)

                st.success(msg)
                st.code(bib_output, language='latex')

            except Exception as e:
                st.error(f"保存エラー: {e}")

    # ダウンロードボタン
    if bib_file_path and os.path.exists(bib_file_path):
        st.divider()
        with open(bib_file_path, "r", encoding="utf-8") as f: content = f.read()
        st.download_button("📥 .bibファイルをダウンロード", content, os.path.basename(bib_file_path))

if __name__ == "__main__":
    main()
