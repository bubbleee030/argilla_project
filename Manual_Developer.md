# Argilla 開發者維運手冊 (Developer Manual)

## 1. 簡介
本手冊旨在協助開發人員與資料工程師管理 Argilla 標註專案。
**工作流程概覽：**
1.  **資料準備**：使用 `prepare_argilla.py` 將原始模型輸出轉換為 Argilla 格式。
2.  **資料上傳**：使用 `upload_argilla.py` 建立資料集並上傳資料。
3.  **使用者管理**：建立標註人員帳號並加入工作區 (Workspace)。
4.  **進度監控**：查看標註進度。
5.  **資料匯出**：匯出已標註資料以供後續訓練使用。

---

## 2. 環境建置

請確保執行環境已安裝 `argilla` 套件。

```bash
pip install argilla
```

### 初始化連線資訊
在所有腳本中，均需使用以下資訊進行連線（請確保 API Key 具有 Owner 權限）：

```python
import argilla as rg

API_URL = "YOUR_API_URL" # 請替換為您的實際 Url
API_KEY = "YOUR_API_KEY" # 請替換為您的實際 Key

client = rg.Argilla(api_url=API_URL, api_key=API_KEY)
```

---

## 3. 資料準備 (Data Preparation)

原始的模型輸出通常是長格式（每列一筆回答），我們需要先將其轉換為寬格式（每列包含 Prompt 與多個 Responses），以便進行成對比較。

請執行 `prepare_argilla.py`：

```python
# prepare_argilla.py
import json
from collections import defaultdict

def transform_to_wide_format(input_file: str, output_file: str):
    """
    將長格式的 JSONL 轉換為寬格式，以便進行偏好標註。
    結構：{ "base_qid": {"prompt": "...", "responses": ["resp1", "resp2", ...]} }
    """
    grouped_data = defaultdict(lambda: {"prompt": "", "responses": []})

    print(f"正在讀取檔案: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                item = json.loads(line)
                qid = item.get('qid', '')
                prompt = item.get('prompt', '')
                model_resp = item.get('model_resp', '')

                if '_v' in qid:
                    base_qid = qid.split('_v')[0]
                    if not grouped_data[base_qid]['prompt']:
                        grouped_data[base_qid]['prompt'] = prompt
                    grouped_data[base_qid]['responses'].append(model_resp)
                
            except json.JSONDecodeError:
                print(f"警告：跳過無法解析的行: {line.strip()}")

    print(f"找到 {len(grouped_data)} 個獨立的 prompt。")

    print(f"正在寫入到檔案: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        for base_qid, data in grouped_data.items():
            # 確保至少有兩個回覆可供比較
            if len(data['responses']) >= 2:
                record = {
                    "id": base_qid,
                    "prompt": data['prompt']
                }
                # 將 responses 列表展開為單獨的字段 (response_0, response_1)
                for i, response in enumerate(data['responses']):
                    record[f"response_{i}"] = response
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print("資料轉換完成！")

if __name__ == '__main__':
    INPUT_JSONL_PATH = 'results/model_predictions_full3_adv2_tem0.87_p0.95.jsonl'
    OUTPUT_JSONL_PATH = 'argilla_ready_adv_tem0.87_p0.95.jsonl'
    transform_to_wide_format(INPUT_JSONL_PATH, OUTPUT_JSONL_PATH)
```

---

## 4. 資料上傳 (Data Upload)

確認轉檔無誤後，執行 `upload_argilla.py` 將資料上傳。此腳本會定義資料集結構（Prompt, Response 0, Response 1）以及標註問題（LabelQuestion）。

```python
# upload_argilla.py
import argilla as rg
import json
import traceback

API_URL = "https://bubble030-test-argilla.hf.space"
API_KEY = "YOUR_API_KEY"

DATASET_NAME = "模型回答偏好選擇-adv"
DATA_FILE_PATH = "argilla_ready_adv_tem0.87_p0.95.jsonl"
MAX_RESPONSES = 2

try:
    client = rg.Argilla(api_url=API_URL, api_key=API_KEY)
    print(f"✅ 成功連線到 Argilla！")

    # 定義 fields (Prompt + Response_0 + Response_1)
    fields_to_define = [rg.TextField(name="prompt", title="模型收到的提示 (Prompt)", use_markdown=True)]
    for i in range(MAX_RESPONSES):
        fields_to_define.append(
            rg.TextField(name=f"response_{i}", title=f"response_{i}", use_markdown=True)
        )

    # 定義 Settings (偏好選擇 LabelQuestion)
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
            rg.TextQuestion(name="reasoning", title="為什麼？(選填)", required=False)
        ],
        guidelines="請閱讀兩個回覆，然後在右側選擇您認為比較好的選項。",
        distribution=rg.TaskDistribution(min_submitted=3)
    )

    # 建立資料集
    try:
        dataset = rg.Dataset.from_name(DATASET_NAME)
        print(f"✅ 資料集 '{DATASET_NAME}' 已存在。")
    except Exception:
        print(f"ℹ️ 資料集 '{DATASET_NAME}' 不存在，建立新資料集。")
        dataset = rg.Dataset(name=DATASET_NAME, settings=settings)
        dataset.create()

    # 讀取並上傳紀錄
    records_to_upload = []
    with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line.strip())
            record_fields = {"prompt": data["prompt"]}
            for i in range(MAX_RESPONSES):
                key = f"response_{i}"
                if key in data:
                    record_fields[key] = data[key]
            
            records_to_upload.append(rg.Record(fields=record_fields))
            
    if records_to_upload:
        dataset.records.log(records_to_upload)
        print(f"🚀 成功上傳 {len(records_to_upload)} 筆紀錄！")

except Exception as e:
    traceback.print_exc()
```

---

## 5. 使用者管理 (User Management)

管理員需手動建立使用者，並**務必將使用者加入到工作區 (Workspace)**，否則使用者登入後將無法看到資料集。

### 5.1 建立並分配使用者
使用以下code 或使用 `create_user.py`
```python
import argilla as rg

client = rg.Argilla(api_url="https://bubble030-test-argilla.hf.space", api_key="YOUR_API_KEY")

# 1. 建立使用者
user_to_create = rg.User(
    username="user1",
    password="12345678", # 設定初始密碼
)
created_user = user_to_create.create()
print(f"User {created_user.username} created.")

# 2. 將使用者加入 Workspace (關鍵步驟)
user = client.users(created_user.username) # 取得使用者物件
workspace = client.workspaces("argilla")   # 取得工作區物件 (預設通常為 'argilla')

added_user = user.add_to_workspace(workspace)
print(f"User {user.username} added to workspace {workspace.name}")
```

### 5.2 查看使用者列表
```python
users = client.users
for user in users:
    print(f"User: {user.username}, Role: {user.role}")
```

---

## 6. 進度監控 (Progress Monitoring)

您可以即時查看資料集的標註進度與人員分佈。
使用以下 code 或使用 `check_progress.py`

```python
import argilla as rg

client = rg.Argilla(api_url="https://bubble030-test-argilla.hf.space", api_key="YOUR_API_KEY")

# 獲取資料集物件
dataset1 = client.datasets("模型回答偏好選擇-matched")
dataset2 = client.datasets("模型回答偏好選擇-adv")

# 查看進度 (包含使用者分佈)
progress1 = dataset1.progress(with_users_distribution=True)
progress2 = dataset2.progress(with_users_distribution=True)

print("Dataset 1 Progress:", progress1)
print("Dataset 2 Progress:", progress2)
```

---

## 7. 資料匯出 (Data Export)

標註完成後，將資料匯出為 JSON 格式，並可依狀態（pending/submitted）進行篩選。
使用以下 code 或使用 `export_dataset.py`

```python
import argilla as rg
import json

client = rg.Argilla(api_url="https://bubble030-test-argilla.hf.space", api_key="YOUR_API_KEY")

# 指定 Workspace 與 Dataset
workspace = client.workspaces("argilla")
dataset = client.datasets(name="模型回答偏好選擇-adv", workspace=workspace)

# 匯出所有紀錄 (flatten=True 會將 fields 和 responses 攤平方便讀取)
exported_records = dataset.records.to_list(flatten=True)

# 篩選資料狀態
pending_records = [r for r in exported_records if r.get('status') == 'pending']
submitted_records = [r for r in exported_records if r.get('status') == 'submitted']

print(f"總筆數: {len(exported_records)}")
print(f"待標註 (Pending): {len(pending_records)}")
print(f"已提交 (Submitted): {len(submitted_records)}")

# 儲存至檔案
output_path = '/home/ubuntu/sft_project/output/records_list_adv.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(exported_records, f, ensure_ascii=False, indent=4)

print(f"資料已儲存至: {output_path}")
```

---

## 8. 自動備份系統 (Auto Backup System)

為了保護資料免於 HF Spaces 36 小時休眠/刪除機制，我們建立了自動備份系統。

### 8.1 備份特點

- **智慧內容偵測**：只在資料真的改變時才建立備份（忽略時間戳記）
- **Discord 通知**：備份失敗或完成時即時通知
- **自動 Git 同步**：每次有變化時自動上傳到 Git
- **備份輪轉**：保留最近 5 個備份，自動刪除舊的
- **錯誤恢復**：失敗時自動清理無用檔案

### 8.2 快速開始

```bash
# 一次性備份
python scripts/auto_backup.py --once

# 測試 Discord webhook（可選）
python scripts/auto_backup.py --test-webhook

# 排程備份（每 2 小時一次）
python scripts/auto_backup.py --schedule 120

# 列出所有備份
python scripts/auto_backup.py --list
```

### 8.3 Discord 通知設定

```bash
# 設定環境變數
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"

# 或永久設定到 ~/.bashrc
echo 'export DISCORD_WEBHOOK_URL="..."' >> ~/.bashrc
```

### 8.4 備份恢復

如果誤刪本機備份：

```bash
# 從 Git 拉回最新備份
git pull

# 查看備份歷史
git log --oneline backups/latest | head -10

# 檢查備份狀態
cat backups/latest/backup_metadata.json
```

### 8.5 備份存儲結構

```
backups/
├── latest/                    # Git 追蹤的最新備份副本
├── 模型回答偏好選擇_整合_20260130_140000/  # 本機備份（不在 Git）
├── 模型回答偏好選擇_整合_20260130_120000/
└── ...
```

只有 `latest/` 資料夾會進入 Git，舊備份留在本機供手動復原使用。

---

## 9. 監控與維護 (Monitoring & Maintenance)

### 9.1 檢查備份日誌

```bash
# 檢視最後 50 行日誌
tail -50 auto_backup.log

# 即時監控
tail -f auto_backup.log

# 查詢錯誤
grep "❌\|ERROR" auto_backup.log
```

### 9.2 檢查磁碟空間

```bash
# 本機備份大小
du -sh backups/

# Git 儲存庫大小
du -sh .git/
```

### 9.3 定期清理

```bash
# 腳本自動執行輪轉，但可手動刪除舊備份
rm -rf backups/模型回答偏好選擇_整合_20260101_*
```