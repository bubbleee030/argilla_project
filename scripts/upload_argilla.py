# 最終修正版：使用 LabelQuestion 且不尋找舊問題 ID

import argilla as rg
import json

# --- 1. 請填入您的個人資訊 ---
API_URL = "https://bubble030-test-argilla.hf.space"  # 請將此處替換為您的 Argilla 伺服器 URL
API_KEY = "0gAM-17abmG8GIh1gHJlzzzbT-dt04jm3X7TGHvJgEIcFMTkLnoYf3Cm8Z723HH41QSWk7btB6PBx13z6bI6rnCC3TBvT4QlHMktzhrC0oo"  # 請將此處替換為您的 Argilla API Key

# --- 2. 請填入您的資料設定 ---
# 再次建議：使用一個全新的、乾淨的資料集名稱，以確保不會讀到舊的、有問題的設定
DATASET_NAME = "模型回答偏好選擇_整合" # 請設定您的資料集名稱
DATA_FILE_PATH = "/home/ubuntu/argilla_project/data/argilla_ready_jsonl/argilla_ready_mix_tem0.87_p0.95_shuffled.jsonl" # 請確認資料路徑, upload 前請先執行 prepare_argilla.py 進行轉檔
MAX_RESPONSES = 2 # 請設定每個 prompt 的最大回覆數量 (與 prepare_argilla.py 保持一致)

# --- 程式主體開始 ---
try:
    # 3. 連線到 Argilla
    client = rg.Argilla(api_url=API_URL, api_key=API_KEY)
    print(f"✅ 成功連線到 Argilla！你好, {client.me.username}!")

    # 4. 定義 fields
    fields_to_define = [rg.TextField(name="prompt", title="模型收到的提示 (Prompt)", use_markdown=True)]
    for i in range(MAX_RESPONSES):
        fields_to_define.append(
            rg.TextField(name=f"response_{i}", title=f"response_{i}", use_markdown=True)
        )

    # 5. 定義新的 Settings，使用 LabelQuestion
    settings = rg.Settings(
        fields=fields_to_define,
        questions=[
            rg.LabelQuestion(
                name="preference_selection",
                title="請問哪一個回答比較好？",
                required=True,
                labels={
                    "resp_0_better": "Response 0 比較好",
                    "resp_1_better": "Response 1 比較好",
                    "equal": "兩個一樣好 / 一樣差"
                }
            ),
            rg.TextQuestion(
                name="reasoning",
                title="為什麼？(選填)",
                required=False
            )
        ],
        guidelines="請閱讀兩個回覆，然後在右側選擇您認為比較好的選項。",
        distribution=rg.TaskDistribution(min_submitted=2) # 每個紀錄至少需要 2 個標註者完成標註
    )
    print("📑 資料集設定 (Settings) 已定義完成。")

    # 6. 建立或獲取資料集
    try:
        dataset = rg.Dataset.from_name(DATASET_NAME)
        print(f"✅ 資料集 '{DATASET_NAME}' 已存在。將使用此資料集。")
    except Exception:
        print(f"ℹ️ 資料集 '{DATASET_NAME}' 不存在，將建立新的資料集。")
        dataset = rg.Dataset(name=DATASET_NAME, settings=settings)
        dataset.create()
    
    print(f"📖 已成功在伺服器上建立/獲取資料集 '{dataset.name}'。")

    # 7. 讀取檔案並準備紀錄
    records_to_upload = []
    with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line.strip())
            
            record_fields = {"prompt": data["prompt"]}
            for i in range(MAX_RESPONSES):
                key = f"response_{i}"
                if key in data:
                    record_fields[key] = data[key]
            
            # 直接建立 Record，完全不使用 Suggestion，也不需要 question_id
            record = rg.Record(fields=record_fields)
            records_to_upload.append(record)
            
    print(f"🗂️ 資料讀取完成，成功準備 {len(records_to_upload)} 筆紀錄。")
    
    # 8. 上傳紀錄
    if records_to_upload:
        dataset.records.log(records_to_upload)
        print(f"🚀 成功將 {len(records_to_upload)} 筆紀錄上傳到資料集 '{DATASET_NAME}'！")
        print(f"👉 您現在可以前往 Argilla UI 查看資料集。")

except Exception as e:
    print(f"❌ 發生錯誤: {e}")
    import traceback
    traceback.print_exc()
