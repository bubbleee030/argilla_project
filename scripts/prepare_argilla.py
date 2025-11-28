import json
from collections import defaultdict

def transform_to_wide_format(input_file: str, output_file: str):
    """
    將長格式的 JSONL 轉換為寬格式，以便進行偏好標註。

    Args:
        input_file: 來源檔案路徑 (e.g., 'multi_responses.jsonl')
        output_file: 轉換後的目標檔案路徑 (e.g., 'argilla_ready.jsonl')
    """
    # 使用 defaultdict 簡化邏輯
    # 結構：{ "base_qid": {"prompt": "...", "responses": ["resp1", "resp2", ...]} }
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
                    # 如果是該群組的第一筆資料，就設定 prompt
                    if not grouped_data[base_qid]['prompt']:
                        grouped_data[base_qid]['prompt'] = prompt
                    grouped_data[base_qid]['responses'].append(model_resp)
                
            except json.JSONDecodeError:
                print(f"警告：跳過無法解析的行: {line.strip()}")

    print(f"找到 {len(grouped_data)} 個獨立的 prompt。")

    # 將分組後的資料寫入新的 JSONL 檔案
    print(f"正在寫入到檔案: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        for base_qid, data in grouped_data.items():
            # 確保至少有兩個回覆可供比較
            if len(data['responses']) >= 2:
                record = {
                    "id": base_qid,
                    "prompt": data['prompt']
                }
                # 將 responses 列表展開為單獨的字段
                for i, response in enumerate(data['responses']):
                    record[f"response_{i}"] = response
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print("資料轉換完成！")

if __name__ == '__main__':
    # --- 設定您的檔案路徑 ---
    INPUT_JSONL_PATH = 'INPUT_JSONL_PATH'  # 您 fine-tuning 後的輸出檔案
    OUTPUT_JSONL_PATH = 'OUTPUT_JSONL_PATH'    # 準備上傳到 Argilla 的檔案
    # -------------------------

    transform_to_wide_format(INPUT_JSONL_PATH, OUTPUT_JSONL_PATH)