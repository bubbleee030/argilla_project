import argilla as rg
import os

API_URL = os.getenv("ARGILLA_API_URL", "https://bubble030-test-argilla.hf.space")
API_KEY = os.getenv("ARGILLA_API_KEY")

if not API_KEY:
    raise ValueError("請設定 ARGILLA_API_KEY")

def check_dataset_progress(dataset_names):
    client = rg.Argilla(api_url=API_URL, api_key=API_KEY)
    
    for name in dataset_names:
        try:
            dataset = client.datasets(name)
            progress = dataset.progress(with_users_distribution=True)
            print(f"\n=== 資料集: {name} ===")
            print(progress)
        except Exception as e:
            print(f"無法讀取資料集 '{name}': {e}")

if __name__ == "__main__":
    # 列出您想監控的資料集名稱
    DATASETS_TO_CHECK = ["模型回答偏好選擇-matched", "模型回答偏好選擇-adv"]
    check_dataset_progress(DATASETS_TO_CHECK)