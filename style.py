# style.py
import streamlit as st

def apply_custom_style():
    """
    ダークモード専用のサイバー・モダンなスタイル定義
    """
    st.markdown("""
        <style>
        /* --------------------------------------------------------- */
        /* 1. フォントとカラー定義 (Dark Mode)                          */
        /* --------------------------------------------------------- */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+JP:wght@400;500;700&family=JetBrains+Mono&display=swap');

        :root {
            --primary-color: #8B5CF6; /* Violet */
            --accent-gradient: linear-gradient(135deg, #8B5CF6 0%, #3B82F6 100%);
            --card-bg: #1F2937;       /* 少し明るいダークグレー */
            --input-bg: #111827;      /* 入力欄は暗く */
            --text-main: #F3F4F6;
            --text-sub: #9CA3AF;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', 'Noto Sans JP', sans-serif;
            color: var(--text-main);
        }
        
        /* --------------------------------------------------------- */
        /* 2. タイトル装飾 (光るグラデーション)                          */
        /* --------------------------------------------------------- */
        h1 {
            font-weight: 800 !important;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            padding-bottom: 10px;
        }
        
        /* サイドバーのタイトルなどは白く */
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: var(--primary-color) !important;
        }

        /* --------------------------------------------------------- */
        /* 3. カードデザイン (ダークな枠)                                */
        /* --------------------------------------------------------- */
        div[data-testid="stVerticalBlock"] > div[style*="background-color"] {
            background-color: var(--card-bg) !important;
            border: 1px solid #374151;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); /* 影を濃く */
        }

        /* --------------------------------------------------------- */
        /* 4. UIパーツ（入力フォーム・ボタン）                           */
        /* --------------------------------------------------------- */
        
        /* 入力欄（黒背景・白文字・枠線あり） */
        .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextArea textarea {
            background-color: var(--input-bg) !important;
            color: var(--text-main) !important;
            border: 1px solid #4B5563 !important;
            border-radius: 8px;
        }
        
        /* フォーカス時に光らせる */
        .stTextInput input:focus, .stNumberInput input:focus {
            border-color: #8B5CF6 !important;
            box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.3);
        }

        /* メインボタン (グラデーション) */
        div.stButton > button {
            background: var(--accent-gradient);
            color: white !important;
            font-weight: 600;
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4); /* 発光感 */
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(139, 92, 246, 0.6);
        }

        /* Expander (折りたたみ) のスタイル調整 */
        .streamlit-expanderHeader {
            background-color: var(--card-bg);
            border-radius: 8px;
        }

        /* コードブロックのフォント (JetBrains Monoなど) */
        code {
            font-family: 'JetBrains Mono', monospace !important;
        }
        </style>
    """, unsafe_allow_html=True)