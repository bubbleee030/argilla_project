import argilla as rg
import os

# 從環境變數讀取，或使用預設值 (建議在執行時設定環境變數)
API_URL = os.getenv("ARGILLA_API_URL", "https://bubble030-test-argilla.hf.space")
API_KEY = os.getenv("ARGILLA_API_KEY") # 請不要將 Key 寫死在這裡

if not API_KEY:
    raise ValueError("請設定環境變數 ARGILLA_API_KEY 或在程式碼中填入您的 Key")

def create_argilla_user(username, password, workspace_name="argilla"):
    client = rg.Argilla(api_url=API_URL, api_key=API_KEY)
    
    # 1. 建立使用者
    try:
        user = client.users(username)
        print(f"使用者 '{username}' 已存在。")
    except:
        print(f"正在建立使用者 '{username}'...")
        user_to_create = rg.User(username=username, password=password)
        user = user_to_create.create()
        print(f"使用者 '{username}' 建立成功。")

    # 2. 將使用者加入 Workspace
    try:
        workspace = client.workspaces(workspace_name)
        user.add_to_workspace(workspace)
        print(f"成功將使用者 '{username}' 加入工作區 '{workspace_name}'。")
    except Exception as e:
        print(f"加入工作區失敗: {e}")

if __name__ == "__main__":
    # 在這裡修改要建立的帳號密碼
    TARGET_USER = "user2"
    TARGET_PASS = "12345678"
    
    create_argilla_user(TARGET_USER, TARGET_PASS)