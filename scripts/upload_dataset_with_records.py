# 上傳完整 Dataset + Records + Responses

import argilla as rg
import json
from pathlib import Path

# --- 1. 請填入您的個人資訊 ---
API_URL = "https://bubble030-test-argilla.hf.space"  # 請將此處替換為您的 Argilla 伺服器 URL
API_KEY = "0gAM-17abmG8GIh1gHJlzzzbT-dt04jm3X7TGHvJgEIcFMTkLnoYf3Cm8Z723HH41QSWk7btB6PBx13z6bI6rnCC3TBvT4QlHMktzhrC0oo"  # 請將此處替換為您的 Argilla API Key

# --- 2. 請填入您的資料設定 ---
BACKUP_DIR = "/home/ubuntu/argilla_project/backups/模型回答偏好選擇_整合_20260211_221013"  # 備份目錄
DATASET_NAME = "模型回答偏好選擇_整合"  # 資料集名稱

# --- 程式主體開始 ---
try:
    # 3. 連線到 Argilla
    client = rg.Argilla(api_url=API_URL, api_key=API_KEY)
    print(f"✅ 成功連線到 Argilla！你好, {client.me.username}!")

    # 3.5 建立舊 user_id 到新 user_id 的映射表
    old_to_new_user_mapping = {
        "bd8c15d3-3cff-41f6-b3b0-0afb39b177e9": "eacb82fb-9cba-41b0-b7e3-4a0fe7db7c70",  # user1 舊→新
        "4deef335-99ee-494d-97aa-70ca1ee42822": "953caa26-1525-4f06-8e0b-09129902dcd5"   # user2 舊→新
    }
    print("📋 已建立用戶 ID 映射表。")

    # 4. 從備份中讀取 Settings
    settings_path = Path(BACKUP_DIR) / ".argilla" / "settings.json"
    with open(settings_path, 'r', encoding='utf-8') as f:
        settings_data = json.load(f)
    
    print("📑 已讀取備份的 Settings。")

    # 5. 重建 Settings 物件
    # 根據 settings_data 重建 Settings
    fields = []
    for field_data in settings_data.get("fields", []):
        if field_data["type"] == "text":
            field_settings = field_data.get("settings", {})
            fields.append(
                rg.TextField(
                    name=field_data["name"],
                    title=field_data.get("title", field_data["name"]),
                    use_markdown=field_settings.get("use_markdown", False)
                )
            )
    
    questions = []
    for question_data in settings_data.get("questions", []):
        question_type = question_data.get("type")
        question_name = question_data["name"]
        question_title = question_data.get("title", question_name)
        question_required = question_data.get("required", True)
        
        if question_type == "label_selection":
            # 從備份的格式中提取 labels
            question_settings = question_data.get("settings", {})
            options = question_settings.get("options", [])
            labels = {opt["value"]: opt["text"] for opt in options}
            
            questions.append(
                rg.LabelQuestion(
                    name=question_name,
                    title=question_title,
                    required=question_required,
                    labels=labels
                )
            )
        elif question_type == "text":
            questions.append(
                rg.TextQuestion(
                    name=question_name,
                    title=question_title,
                    required=question_required
                )
            )

    distribution_data = settings_data.get("distribution", {})
    distribution = rg.TaskDistribution(
        min_submitted=distribution_data.get("min_submitted", 1)
    ) if distribution_data else None

    settings = rg.Settings(
        fields=fields,
        questions=questions,
        guidelines=settings_data.get("guidelines", ""),
        distribution=distribution
    )
    print("📑 Settings 已重建完成。")

    # 6. 建立或獲取資料集
    try:
        # 首先嘗試刪除現有資料集（可選，如果要完全覆蓋舊資料）
        existing_dataset = rg.Dataset.from_name(DATASET_NAME)
        print(f"⚠️ 資料集 '{DATASET_NAME}' 已存在。")
        # 如果要覆蓋，可以在這裡刪除舊的
        # existing_dataset.delete()
        # print(f"🗑️ 已刪除舊資料集。")
        # dataset = rg.Dataset(name=DATASET_NAME, settings=settings)
        # dataset.create()
        dataset = existing_dataset
        print(f"✅ 使用現有資料集 '{DATASET_NAME}'。")
    except Exception:
        print(f"ℹ️ 資料集 '{DATASET_NAME}' 不存在，將建立新的資料集。")
        dataset = rg.Dataset(name=DATASET_NAME, settings=settings)
        dataset.create()
        print(f"📖 已成功在伺服器上建立資料集 '{dataset.name}'。")

    # 7. 讀取備份中的 Records
    records_path = Path(BACKUP_DIR) / "records.json"
    with open(records_path, 'r', encoding='utf-8') as f:
        backup_records = json.load(f)
    
    print(f"🗂️ 已成功讀取 {len(backup_records)} 筆紀錄。")

    # 8. 準備要上傳的 Records，使用新的 user_id (包含 responses)
    records_to_upload = []
    
    for record_data in backup_records:
        # 從備份中提取 fields 和 responses
        fields = record_data.get("fields", {})
        responses = record_data.get("responses", {})
        
        # 建立 Record 物件
        record = rg.Record(fields=fields)
        
        # 添加 responses，並將舊 user_id 轉換為新 user_id
        if responses:
            for question_name, response_list in responses.items():
                for response_value in response_list:
                    if response_value.get("value"): # 確保 response 有值
                        old_user_id = str(response_value.get("user_id"))
                        new_user_id = old_to_new_user_mapping.get(old_user_id)
                        
                        if new_user_id:
                            record.responses.add(
                                rg.Response(
                                    question_name=question_name,
                                    value=response_value.get("value"),
                                    user_id=new_user_id  # 使用新的 user_id
                                )
                            )
                            print(f"✓ 已將 {question_name} 的 responses 從舊用戶 ID 轉換為新用戶 ID")
                        else:
                            print(f"⚠️ 警告：找不到舊用戶 ID {old_user_id} 的映射")
        
        records_to_upload.append(record)
    
    print(f"📝 已準備 {len(records_to_upload)} 筆紀錄（responses 已轉換為新的 user_id）。")

    # 9. 上傳 Records
    if records_to_upload:
        dataset.records.log(records_to_upload)
        print(f"🚀 成功將 {len(records_to_upload)} 筆紀錄（含舊的 responses）上傳到資料集 '{DATASET_NAME}'！")
        print(f"👉 所有舊的標註已保留並關聯到新的用戶帳戶。")
    else:
        print("⚠️ 沒有紀錄可以上傳。")

except Exception as e:
    print(f"❌ 發生錯誤: {e}")
    import traceback
    traceback.print_exc()
