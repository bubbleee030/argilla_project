# 更新 Records 和 Responses

import argilla as rg
import json
from pathlib import Path

# --- 1. 請填入您的個人資訊 ---
API_URL = "https://bubble030-test-argilla.hf.space"
API_KEY = "0KQy1XjHdNK35xRz4Tk6AQZ8lrw1TB8EEo8VCubfSa4JQnWhn50jBSwE44gTCvWSv7QBdYzRDaNcEzpPuoSjQ4Erf47sMk31b5GnT1DkqvM"

# --- 2. 請填入您的資料設定 ---
DATASET_NAME = "模型回答偏好選擇_整合"
BACKUP_DIR = "/home/ubuntu/argilla_project/backups/模型回答偏好選擇_整合_20260211_221013"

# --- 程式主體開始 ---
try:
    # 3. 連線到 Argilla
    client = rg.Argilla(api_url=API_URL, api_key=API_KEY)
    print(f"✅ 成功連線到 Argilla！你好, {client.me.username}!")

    # 4. 獲取資料集
    dataset = rg.Dataset.from_name(DATASET_NAME)
    print(f"📖 已獲取資料集 '{dataset.name}'。")

    # --- 方法 1: 更新 Records 的元數據或 Fields ---
    # 示例：更新 records 的某些欄位
    print("\n--- 方法 1: 更新 Records 的元數據 ---")
    data = dataset.records.to_list(flatten=True)
    print(f"📊 成功讀取 {len(data)} 筆紀錄。")
    
    # 可以在這裡對 records 進行修改
    # 例如：修改某個欄位
    # for record in data:
    #     if 'prompt' in record:
    #         record['prompt'] = record['prompt'].upper()  # 範例：轉為大寫

    # 上傳更新後的 records
    # dataset.records.log(records=data)
    # print(f"✅ 成功更新 {len(data)} 筆紀錄的元數據。")

    # --- 方法 2: 更新 Records 的 Responses ---
    # 這是更新回覆的推薦方法
    print("\n--- 方法 2: 更新 Records 的 Responses ---")
    
    # 讀取備份中的 records 和 responses
    records_path = Path(BACKUP_DIR) / "records.json"
    with open(records_path, 'r', encoding='utf-8') as f:
        backup_records = json.load(f)
    
    print(f"📂 已從備份讀取 {len(backup_records)} 筆紀錄。")

    # 將備份 records 映射到 server records ID
    # 因為 server 上的 ID 可能與備份中的不同
    backup_map = {record["id"]: record for record in backup_records}
    
    updated_records = []
    
    for server_record in dataset.records(with_responses=True):
        # 嘗試從備份中找到對應的 record（通過 prompt 匹配）
        backup_record = None
        for bk_record in backup_records:
            if bk_record.get("fields", {}).get("prompt") == server_record.fields.get("prompt"):
                backup_record = bk_record
                break
        
        if backup_record and backup_record.get("responses"):
            # 更新該 record 的 responses
            backup_responses = backup_record.get("responses", {})
            
            for question_name, response_list in backup_responses.items():
                for response_value in response_list:
                    if response_value.get("value"):
                        # 创建新的 response 或更新现有的
                        # 首先検查是否已有該 question 的 response
                        existing_responses = server_record.responses.get(question_name, [])
                        
                        # 如果沒有既有 response，就添加新的
                        if not existing_responses:
                            server_record.responses.add(
                                rg.Response(
                                    question_name=question_name,
                                    value=response_value.get("value"),
                                    user_id=response_value.get("user_id")
                                )
                            )
                        else:
                            # 如果有既有 response，也可以選擇更新
                            for resp in existing_responses:
                                resp.value = response_value.get("value")
                                resp.user_id = response_value.get("user_id")
        
        updated_records.append(server_record)
    
    print(f"📝 已準備 {len(updated_records)} 筆紀錄的 responses。")
    
    # 上傳更新後的 records（包含 responses）
    if updated_records:
        dataset.records.log(records=updated_records)
        print(f"🚀 成功更新 {len(updated_records)} 筆紀錄的 responses！")
    
    # --- 方法 3: 獲取特定的 Records 並進行定點更新 ---
    print("\n--- 方法 3: 定點更新特定 Records ---")
    
    # 例：查看第一筆紀錄的 responses
    first_records = dataset.records(with_responses=True)
    first_record = next(iter(first_records), None)
    
    if first_record:
        print(f"📌 第一筆紀錄 ID: {first_record.id}")
        print(f"📝 Responses: {first_record.responses}")
        
        # 可以在這裡修改 responses
        # 例如：更新 preference_selection 的值
        # if first_record.responses.get("preference_selection"):
        #     for resp in first_record.responses["preference_selection"]:
        #         resp.value = "resp_0_better"
        # 
        # # 上傳更新
        # dataset.records.log(records=[first_record])

except Exception as e:
    print(f"❌ 發生錯誤: {e}")
    import traceback
    traceback.print_exc()
