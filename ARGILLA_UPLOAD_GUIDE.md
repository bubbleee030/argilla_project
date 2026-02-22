# Argilla Dataset 上傳與更新指南

## 概述

根據 Argilla 官方文檔，上傳和更新 records 需要了解以下核心概念：

- **上傳完整 Dataset**: 包括 Settings（fields 和 questions）+ Records（包含 data 和 responses）
- **更新現有 Records**: 可以透過 `dataset.records.log()` 方法更新 records（元數據、fields、responses）
- **管理 Responses**: 通過 `dataset.records(with_responses=True)` 獲取帶有 responses 的 records，然後進行更新

---

## 方法 1: 上傳完整 Dataset + Records（推薦）

### 使用場景
- 第一次上傳全新的 dataset
- 從備份恢復整個 dataset（包含所有 records 和 responses）

### 如何使用

```bash
python /home/ubuntu/argilla_project/scripts/upload_dataset_with_records.py
```

### 流程說明

1. **連線到 Argilla 伺服器**
   ```python
   client = rg.Argilla(api_url=API_URL, api_key=API_KEY)
   ```

2. **讀取備份的 Settings**
   ```python
   # 從 .argilla/settings.json 讀取
   settings_path = Path(BACKUP_DIR) / ".argilla" / "settings.json"
   with open(settings_path, 'r', encoding='utf-8') as f:
       settings_data = json.load(f)
   ```

3. **重建 Settings 物件**
   - 解析 fields（TextField 等）
   - 解析 questions（LabelQuestion、TextQuestion 等）
   - 設定 guidelines 和 distribution

4. **建立或獲取 Dataset**
   ```python
   dataset = rg.Dataset(name=DATASET_NAME, settings=settings)
   dataset.create()
   ```

5. **準備 Records（包含 responses）**
   ```python
   record = rg.Record(fields=fields)
   record.responses.add(
       rg.Response(
           question_name=question_name,
           value=response_value,
           user_id=user_id
       )
   )
   ```

6. **上傳至伺服器**
   ```python
   dataset.records.log(records=records_to_upload)
   ```

---

## 方法 2: 更新現有 Records 的元數據

### 使用場景
- 批量修改已存在 records 的 fields 內容
- 更新 metadata

### 步驟

```python
# 1. 獲取現有 records
data = dataset.records.to_list(flatten=True)

# 2. 修改 records
for record in data:
    record['field_name'] = 'new_value'

# 3. 上傳更新
dataset.records.log(records=data)
```

### 範例

```python
# 修改所有 prompt 為大寫
data = dataset.records.to_list(flatten=True)
updated_data = [
    {
        **sample,
        "prompt": sample["prompt"].upper() if "prompt" in sample else sample.get("prompt")
    }
    for sample in data
]
dataset.records.log(records=updated_data)
```

---

## 方法 3: 更新 Records 的 Responses（推薦用法）

### 使用場景
- 更新現有 records 的標註結果
- 添加或修改 responses（例如：preference_selection、reasoning）

### 使用腳本

```bash
python /home/ubuntu/argilla_project/scripts/update_records_and_responses.py
```

### 核心代碼模式

```python
# 1. 獲取帶有 responses 的 records
for record in dataset.records(with_responses=True):
    
    # 2. 訪問現有 responses
    for response in record.responses["question_name"]:
        if response:
            # 3. 更新 response 的值和 user_id
            response.value = "new_value"
            response.user_id = "user_id"
        else:
            # 或添加新的 response
            record.responses.add(
                rg.Response("question_name", "value", user_id=user_id)
            )
    
    updated_records.append(record)

# 4. 上傳更新
dataset.records.log(records=updated_records)
```

### 實際應用例子

```python
# 更新 preference_selection 的值
for record in dataset.records(with_responses=True):
    for response in record.responses.get("preference_selection", []):
        if response:
            response.value = "resp_0_better"  # 更新值
            response.user_id = "your_user_id"  # 更新使用者

    updated_records.append(record)

dataset.records.log(records=updated_records)
```

---

## 重要概念

### Record 與 Response 的區別

| 項目 | Record | Response |
|------|--------|----------|
| 定義 | 一份待標註的資料 | 對 questions 的回答 |
| 包含 | fields（資料欄位）| value（回答值）、user_id（標註者）|
| 修改方式 | 透過 `Record.fields` | 透過 `Record.responses.add()` 或更新現有 response |

### 常見問題

#### Q1: 我想上傳備份中的所有 records 和 responses，應該用哪個腳本？
**A**: 使用 `upload_dataset_with_records.py`

#### Q2: 我想批量修改已上傳的 records 的某個欄位，怎麼做？
**A**: 
```python
data = dataset.records.to_list(flatten=True)
# 修改 records
dataset.records.log(records=data)
```

#### Q3: 我想從備份中恢復 responses，應該怎麼做？
**A**: 使用 `update_records_and_responses.py`，它支援從備份匹配 records 並恢復 responses

#### Q4: 我可以更新既有 response 的 user_id 嗎？
**A**: 可以，見方法 3 中的代碼

---

## 腳本配置說明

### upload_dataset_with_records.py

```python
API_URL = "https://bubble030-test-argilla.hf.space"
API_KEY = "your_api_key"
BACKUP_DIR = "/home/ubuntu/argilla_project/backups/模型回答偏好選擇_整合_20260211_221013"
DATASET_NAME = "模型回答偏好選擇_整合"
```

### update_records_and_responses.py

```python
API_URL = "https://bubble030-test-argilla.hf.space"
API_KEY = "your_api_key"
DATASET_NAME = "模型回答偏好選擇_整合"
BACKUP_DIR = "/home/ubuntu/argilla_project/backups/模型回答偏好選擇_整合_20260211_221013"
```

---

## 快速命令參考

| 操作 | 代碼 |
|------|------|
| 連線到 Argilla | `client = rg.Argilla(api_url=API_URL, api_key=API_KEY)` |
| 獲取 Dataset | `dataset = rg.Dataset.from_name(DATASET_NAME)` |
| 創建 Dataset | `dataset = rg.Dataset(name=name, settings=settings); dataset.create()` |
| 讀取所有 records | `data = dataset.records.to_list(flatten=True)` |
| 讀取帶 responses 的 records | `for record in dataset.records(with_responses=True):` |
| 上傳 records | `dataset.records.log(records=records_list)` |
| 添加 response | `record.responses.add(rg.Response(question_name, value, user_id))` |
| 更新 response 值 | `response.value = "new_value"` |

---

## 備份文件結構

您的備份包含以下文件：

```
備份目錄/
├── backup_metadata.json          # 備份元數據（時間戳、record 數量等）
├── records.json                  # 所有 records（包含 fields 和 responses）
└── .argilla/
    ├── dataset.json              # Dataset 配置
    └── settings.json             # Settings 配置（fields、questions、guidelines）
```

---

## 建議工作流程

### 場景 1: 從備份完全恢復 Dataset

1. 執行 `upload_dataset_with_records.py`
2. 檢查 Argilla UI 確認數據已上傳
3. 完成！

### 場景 2: 批量修改既有 records

1. 獲取現有 records: `data = dataset.records.to_list(flatten=True)`
2. 修改 records 內容
3. 上傳: `dataset.records.log(records=data)`

### 場景 3: 更新 responses（標註結果）

1. 執行 `update_records_and_responses.py`
2. 或根據需要自訂 `dataset.records(with_responses=True)` 邏輯

---

最後更新: 2026-02-20
