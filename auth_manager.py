import streamlit as st
import requests
import time
import streamlit.components.v1 as components

# ==========================================
# 設定 (提供された情報を設定)
# ==========================================
# セキュリティ推奨: 本番環境ではこれらを st.secrets に移動してください
DEFAULT_CONFIG = {
    "apiKey": "AIzaSyD21t2dnXcjsPlG3RaEGJxltRBF7wEjti8",
    "authDomain": "python-tex-tools.firebaseapp.com",
    "projectId": "python-tex-tools",
    "storageBucket": "python-tex-tools.firebasestorage.app",
    "messagingSenderId": "880041264852",
    "appId": "1:880041264852:web:01788528e2dd29eb8c5d41",
    "measurementId": "G-BBHB6JC0DN"
}

# Firebase Auth REST API URLs
# ログイン用
FIREBASE_AUTH_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={}"
# 新規登録用
FIREBASE_SIGNUP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={}"

def get_config():
    """設定を取得 (st.secretsがあればそれを優先)"""
    if "firebase" in st.secrets:
        return st.secrets["firebase"]
    return DEFAULT_CONFIG

def inject_analytics():
    """
    Firebase Analytics (GA4) タグを埋め込む
    """
    config = get_config()
    ga_id = config.get("measurementId")
    
    if ga_id:
        # Google Analytics 4 Tag
        analytics_js = f"""
        <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){{dataLayer.push(arguments);}}
          gtag('js', new Date());
          gtag('config', '{ga_id}');
        </script>
        """
        # 画面に見えない形でHTMLヘッダー的に埋め込む
        components.html(analytics_js, height=0, width=0)

def _handle_auth_response(response_json):
    """
    ログインまたは登録成功時のセッション保存処理
    """
    st.session_state['is_logged_in'] = True
    st.session_state['user_email'] = response_json['email']
    st.session_state['localId'] = response_json['localId']
    st.session_state['idToken'] = response_json['idToken']
    
    st.success("認証成功！ リダイレクトします...")
    time.sleep(0.5)
    st.rerun()

def login_form():
    """
    ログインフォームおよび新規登録フォームを表示し、認証処理を行う関数
    認証されていない場合、以降の処理をブロック(st.stop)する
    """
    if 'is_logged_in' not in st.session_state:
        st.session_state['is_logged_in'] = False

    if not st.session_state['is_logged_in']:
        # 画面レイアウト
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("## 🔒 Auth Required")
            
            # タブで「ログイン」と「新規登録」を切り替え
            tab_login, tab_signup = st.tabs(["ログイン", "新規登録"])
            
            config = get_config()
            api_key = config.get("apiKey")

            # --- 既存ユーザーログイン ---
            with tab_login:
                st.caption("登録済みのアカウントでログイン")
                with st.form("login_form"):
                    email = st.text_input("Email", key="login_email")
                    password = st.text_input("Password", type="password", key="login_pass")
                    submit_login = st.form_submit_button("Sign In", type="primary", use_container_width=True)

                if submit_login:
                    auth_url = FIREBASE_AUTH_URL.format(api_key)
                    payload = {
                        "email": email,
                        "password": password,
                        "returnSecureToken": True
                    }
                    try:
                        with st.spinner("Authenticating..."):
                            r = requests.post(auth_url, json=payload)
                            r.raise_for_status()
                            _handle_auth_response(r.json())
                    
                    except requests.exceptions.HTTPError as err:
                        error_json = err.response.json()
                        error_msg = error_json.get('error', {}).get('message', 'Unknown Error')
                        
                        if error_msg in ["EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS"]:
                            st.error("メールアドレスまたはパスワードが間違っています。")
                        elif error_msg == "USER_DISABLED":
                            st.error("このアカウントは無効化されています。")
                        elif error_msg == "TOO_MANY_ATTEMPTS_TRY_LATER":
                            st.error("試行回数が多すぎます。しばらく待ってから再試行してください。")
                        else:
                            st.error(f"Login Error: {error_msg}")
                    except Exception as e:
                        st.error(f"System Error: {e}")

            # --- 新規ユーザー登録 ---
            with tab_signup:
                st.caption("新しいアカウントを作成")
                with st.form("signup_form"):
                    new_email = st.text_input("Email", key="signup_email")
                    new_password = st.text_input("Password (6文字以上)", type="password", key="signup_pass")
                    new_password_confirm = st.text_input("Confirm Password", type="password", key="signup_pass_confirm")
                    submit_signup = st.form_submit_button("Create Account", use_container_width=True)

                if submit_signup:
                    if new_password != new_password_confirm:
                        st.error("パスワードが一致しません。")
                    elif len(new_password) < 6:
                        st.error("パスワードは6文字以上で設定してください。")
                    else:
                        signup_url = FIREBASE_SIGNUP_URL.format(api_key)
                        payload = {
                            "email": new_email,
                            "password": new_password,
                            "returnSecureToken": True
                        }
                        try:
                            with st.spinner("Creating account..."):
                                r = requests.post(signup_url, json=payload)
                                r.raise_for_status()
                                _handle_auth_response(r.json())

                        except requests.exceptions.HTTPError as err:
                            error_json = err.response.json()
                            error_msg = error_json.get('error', {}).get('message', 'Unknown Error')
                            
                            if error_msg == "EMAIL_EXISTS":
                                st.error("このメールアドレスは既に登録されています。")
                            elif error_msg == "WEAK_PASSWORD":
                                st.error("パスワードが弱すぎます。")
                            elif error_msg == "INVALID_EMAIL":
                                st.error("無効なメールアドレス形式です。")
                            else:
                                st.error(f"Signup Error: {error_msg}")
                        except Exception as e:
                            st.error(f"System Error: {e}")
        
        # 未ログイン時はここでストップ
        st.stop()

def logout_button():
    """サイドバーにログアウトボタンを表示"""
    if st.session_state.get('is_logged_in', False):
        st.sidebar.markdown("---")
        st.sidebar.caption(f"Logged in as:\n{st.session_state.get('user_email')}")
        if st.sidebar.button("Logout", type="secondary"):
            st.session_state['is_logged_in'] = False
            # セッション情報のクリア
            keys_to_remove = ['user_email', 'localId', 'idToken']
            for key in keys_to_remove:
                st.session_state.pop(key, None)
            st.rerun()

def check_auth():
    """
    各ページの先頭で呼び出す一括管理関数
    1. Analytics埋め込み
    2. ログインチェック (未ログインならstop)
    3. ログアウトボタン表示
    """
    inject_analytics()
    login_form()
    logout_button()
