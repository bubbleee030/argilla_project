import argilla as rg
import json
import os

API_URL = os.getenv("ARGILLA_API_URL", "https://bubble030-test-argilla.hf.space")
API_KEY = os.getenv("ARGILLA_API_KEY")

if not API_KEY:
    raise ValueError("請設定 ARGILLA_API_KEY")

def export_data(dataset_name, output_file, workspace_name="argilla"):
    client = rg.Argilla(api_url=API_URL, api_key=API_KEY)
    
    try:
        workspace = client.workspaces(workspace_name)
        dataset = client.datasets(name=dataset_name, workspace=workspace)
        
        print(f"正在匯出資料集 '{dataset_name}'...")
        exported_records = dataset.records.to_list(flatten=True)
        
        # 統計狀態
        pending = sum(1 for r in exported_records if r.get('status') == 'pending')
        submitted = sum(1 for r in exported_records if r.get('status') == 'submitted')
        
        print(f"總筆數: {len(exported_records)}, 待處理: {pending}, 已提交: {submitted}")
        
        # 建立輸出目錄 (如果不存在)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(exported_records, f, ensure_ascii=False, indent=4)
            
        print(f"匯出完成: {output_file}")
        
    except Exception as e:
        print(f"匯出失敗: {e}")

if __name__ == "__main__":
    # 設定匯出任務
    export_data(
        dataset_name="模型回答偏好選擇-adv", 
        output_file="./output/records_list_adv.json"
    )
    
    export_data(
        dataset_name="模型回答偏好選擇-matched", 
        output_file="./output/records_list_matched.json"
    )