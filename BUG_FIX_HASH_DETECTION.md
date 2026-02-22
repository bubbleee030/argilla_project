# 備份異動偵測Bug修復報告

## 問題描述

備份系統在執行時，會錯誤判斷備份內容「沒有變化」(`no changes detected`)，即使使用者在 Argilla 中新增了標註或回應。這導致實際上有異動的備份反而沒有被正式保存。

### 症狀

- 使用者在 Argilla 上做了進度（新增回應、標註等）
- 執行 `python scripts/auto_backup.py --once` 進行備份
- 日誌顯示：`⏭️ No changes detected, but keeping backup for debugging`
- 新備份被刪除，Git 沒有更新
- 實際上資料已經改變，但系統沒有偵測到

### 測試證據

進行了備份內容的 SHA-256 哈希對比：

```
備份 110939 (舊): 10aa338675729d66...
備份 103602 (新): 590851161eaac68d...
latest 目錄  : 10aa338675729d66...
```

新備份的哈希值（590851161eaac68d...）明顯不同於舊備份（10aa338675729d66...），證明內容確實改變了。但系統仍然錯誤判斷為「沒有變化」。

---

## 根本原因

在 `backup_dataset()` 方法中的邏輯流程存在時序問題：

### 原始流程（有Bug）

```python
def backup_dataset(self) -> bool:
    backup_path = self.get_backup_path()
    
    # 1️⃣ 建立新的備份目錄並匯出資料
    backup_path.mkdir(parents=True, exist_ok=True)
    self.dataset.to_disk(path=str(backup_path), ...)
    
    # 2️⃣ 處理 JSON 編碼
    self.fix_json_encoding(...)
    
    # 3️⃣ 檢查是否有異動
    content_changed = self.has_backup_changed(backup_path)  # ❌ Bug在這裡
```

### Bug發生的地方

在 `has_backup_changed()` 內部：

```python
def has_backup_changed(self, new_backup_path: Path) -> bool:
    existing_backups = self.get_existing_backups()  # ⚠️ 此時新備份已在目錄中！
    latest_backup = existing_backups[0]              # 所以這裡拿到的是新備份本身
    
    new_hash = self.calculate_backup_hash(new_backup_path)  # 新備份的哈希
    old_hash = self.calculate_backup_hash(latest_backup)     # 也是新備份的哈希！
    
    if new_hash == old_hash:  # 當然相同，因為都是同一個檔案
        return False  # 判斷為「沒有變化」❌
```

### 問題圖示

```
時間軸：
1. 新備份被建立到 backup_path → 目錄中現在有：[old_backup, new_backup]
2. 呼叫 has_backup_changed(new_backup_path)
3. 在函式內呼叫 get_existing_backups() 
   → 列出所有備份並按修改時間排序（最新的在前）
   → 傳回 [new_backup, old_backup]  ⚠️
4. 取 [0] → 得到 new_backup（最新建立的）
5. 比對：new_backup hash vs new_backup hash
6. 當然完全相同 → 判斷為 "no changes"  ❌❌❌
```

---

## 修復方案

### 核心理念

在備份建立**之前**先取得舊備份的哈希值，然後和新備份比對，避免和自己比較。

### 修復步驟

#### 1. 修改 `backup_dataset()` 方法

**之前**：
```python
def backup_dataset(self) -> bool:
    backup_path = self.get_backup_path()
    
    try:
        # 建立備份...
        self.dataset.to_disk(...)
        
        # 檢查異動（此時新備份已在目錄中 ❌）
        content_changed = self.has_backup_changed(backup_path)
```

**之後**：
```python
def backup_dataset(self) -> bool:
    # ✅ 在建立新備份之前，先取得舊備份的哈希值
    existing_backups = self.get_existing_backups()
    old_hash = None
    if existing_backups:
        old_hash = self.calculate_backup_hash(existing_backups[0])
        logger.info(f"Latest existing backup hash: {old_hash[:16] if old_hash else 'None'}...")
    
    backup_path = self.get_backup_path()
    
    try:
        # 建立備份...
        self.dataset.to_disk(...)
        
        # ✅ 計算新備份的哈希，然後直接比對（不再呼叫 has_backup_changed）
        new_hash = self.calculate_backup_hash(backup_path)
        content_changed = (old_hash is None or new_hash != old_hash)
```

#### 2. 改進 `has_backup_changed()` 方法

雖然已改為直接比較哈希，但為了防守性程式設計，也改進了此方法：

```python
def has_backup_changed(self, new_backup_path: Path) -> bool:
    """檢查備份內容是否和最新的備份不同"""
    existing_backups = self.get_existing_backups()
    
    # ✅ 跳過與新備份同名的目錄，避免和自己比較
    latest_backup = None
    for backup in existing_backups:
        if backup.name != new_backup_path.name:  # 檢查目錄名稱
            latest_backup = backup
            break
    
    if latest_backup is None:
        logger.info("找不到舊備份來比對")
        return True
    
    # 現在可以安全地比較
    new_hash = self.calculate_backup_hash(new_backup_path)
    old_hash = self.calculate_backup_hash(latest_backup)
    ...
```

---

## 修復結果

### 修復前
```
2026-02-03 10:36:06,944 - __main__ - INFO - Backup content unchanged (hash: 590851161eaac68d...)
2026-02-03 10:36:06,945 - __main__ - INFO - ⏭️ No changes detected, but keeping backup for debugging
2026-02-03 10:36:06,945 - __main__ - INFO - Latest backup already exists, no update needed
```

### 修復後
```
2026-02-03 10:38:16,489 - __main__ - INFO - Backup content changed (old: 10aa338675729d66..., new: 590851161eaac68d...)
2026-02-03 10:38:16,490 - __main__ - INFO - ✅ Updated latest backup copy: latest/ <- 模型回答偏好選擇_整合_20260203_103812
[master 7e045fd] Backup updated: 2026-02-03 10:38
 3 files changed, 424 insertions(+), 42 deletions(-)
2026-02-03 10:38:17,461 - __main__ - INFO - ✅ Auto-committed and pushed to Git: Backup updated: 2026-02-03 10:38
```

### 驗證

✅ 系統現在正確識別備份內容的異動  
✅ 新備份被正式保存（不再被誤刪）  
✅ Git 倉庫被正確更新  
✅ 使用者在 Argilla 上的進度現在會被確實備份  

---

## 技術細節

### 哈希計算方式

為了準確比對備份內容，哈希計算過程會：

1. **過濾出關鍵欄位**：只比對實際資料，忽略時間戳
   - 記錄 ID、欄位內容、狀態
   - 回應：值 + 狀態（不含 `inserted_at`, `updated_at` 等）
   - 建議：值 + 類型

2. **使用 SHA-256 雜湊**：
   ```python
   content_str = json.dumps(records_content, sort_keys=True, ensure_ascii=False)
   file_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
   ```

3. **確保一致性**：使用排序的鍵（`sort_keys=True`），使得相同的內容一定產生相同的哈希

### 為什麼時間戳不包含在哈希中

- 避免時間戳的自動更新被誤判為「資料變化」
- 使用 Argilla API 備份時，每次都會更新 `updated_at` 等欄位
- 如果包含時間戳，每次備份都會被判定為「有變化」，無法偵測真正的資料異動

---

## 相關檔案修改

修改檔案：`/home/ubuntu/argilla_project/scripts/auto_backup.py`

### 修改清單

1. **backup_dataset() 方法**
   - 新增：在建立備份前取得舊備份哈希
   - 改進：直接比較哈希而不是呼叫 has_backup_changed()
   - 移除：調試用的 `# shutil.rmtree(backup_path)` 註解

2. **has_backup_changed() 方法**
   - 新增：防守性檢查（跳過同名目錄）
   - 新增：詳細文件說明此方法已棄用

3. **日誌記錄**
   - 新增：顯示舊備份的哈希值
   - 改進：清晰的「內容已改變」vs「內容未改變」訊息

---

## 測試建議

### 手動測試

1. 清空舊備份
   ```bash
   cd /home/ubuntu/argilla_project
   rm -rf backups/模型回答偏好選擇_整合_*
   ```

2. 執行第一次備份（建立基準）
   ```bash
   source /home/ubuntu/sft_project/sft_env/bin/activate
   python scripts/auto_backup.py --once
   ```

3. 在 Argilla UI 中新增標註或回應

4. 執行第二次備份（應該偵測到變化）
   ```bash
   python scripts/auto_backup.py --once
   ```

5. 驗證日誌中出現 `"Backup content changed"`

### 預期結果

- ✅ 第二次備份應該顯示「有變化」
- ✅ 新備份目錄被保留（不被誤刪）
- ✅ Git 倉庫得到更新
- ✅ `backups/latest/` 目錄指向最新備份

---

## 總結

此 Bug 修復確保了備份系統的核心功能——**異動偵測** 能夠正確運作。現在：

- 使用者的進度會被確實記錄
- 備份系統不會因為時序問題而誤判
- Git 倉庫保持最新狀態
- 整個自動備份流程可以可靠地運行

修復代碼已測試驗證，系統運作正常。

