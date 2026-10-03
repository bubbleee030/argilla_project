# argilla_project: pairwise preference annotation for LLM responses

**English** · [Annotator manual (繁體中文)](docs/ANNOTATOR_MANUAL.zh-TW.md)

A small toolkit for running a human preference-labelling study on [Argilla](https://argilla.io),
hosted on Hugging Face Spaces. Annotators see a prompt and two model responses and choose the
better one (or "equally good / equally bad"), with an optional free-text reason.

The exports feed the preference data used elsewhere in this work. `sft_project` has converters
from Argilla exports to DPO pairs and to a judge test set.

## What it does

| Stage | Script | Notes |
|---|---|---|
| Prepare | `scripts/prepare_argilla.py` | Long-format model outputs to wide format: one row per prompt, several responses. |
| Upload | `scripts/upload_argilla.py`, `scripts/upload_dataset_with_records.py` | Creates the dataset and its questions, then uploads the records. |
| Users | `scripts/create_user.py` | Creates annotator accounts and adds them to a workspace. |
| Monitor | `scripts/check_progress.py` | Annotation progress. |
| Export | `scripts/export_dataset.py` | JSON / CSV export for downstream training. |
| Backup | `scripts/auto_backup.py`, `scripts/backup.sh` | See below. |

## Why the backup system exists

A free Hugging Face Space sleeps and can be deleted after 36 hours of inactivity, and that would
take the annotations with it. `auto_backup.py` protects against that:

- writes a new backup only when the content changed, not when a timestamp did
- commits each backup to Git, keeps the last N backups, and cleans up after a failed run
- sends a Discord notification on success or failure
- keeps Chinese text intact (UTF-8 throughout)

One limitation, recorded in the backup metadata: Argilla does not export discarded responses.
`BUG_FIX_HASH_DETECTION.md` documents a change-detection bug found and fixed along the way.

## Data

The repository contains a snapshot of 800 records (standard and adversarial model outputs,
mixed and shuffled) under `data/` and `backups/latest/`.

## Setup

```bash
pip install -r requirements.txt
cp .env.template .env        # Argilla URL and API key
python scripts/prepare_argilla.py
python scripts/upload_argilla.py
bash scripts/backup.sh backup
```

Read `Manual_Developer.md` for the full workflow and `QUICK_START_BACKUP.md` for the backup setup.
