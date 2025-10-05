## 📂 Suggested Folder & File Structure

```
cirs_agent/
│
├── backend/
│   ├── ingestion/
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── monitor.py
│   │   ├── scraper.py
│   │
│   │
│   ├── transcription/
│   │   └── (future WhisperX + pyannote)
│   │
│   ├── processing/
│   │   └── (future cleaning, spellcheck)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                    # FastAPI endpoints (UI hooks)
│   │   └── schemas.py                   # Pydantic schemas for API
│   │
│   ├── config.py                        # Centralized config (accounts, freq, max downloads, cutoff date)
│   ├── logger.py                        # Logging utility (saves logs to /logs)
│   └── main.py                          # FastAPI entrypoint
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── InstagramSettings.jsx    # UI for frequency, max downloads, cutoff date
│   │   │   ├── ControlButtons.jsx       # Start/Stop/Check Now
│   │   │   └── LogViewer.jsx            # Show recent logs
│   │   ├── App.jsx
│   │   └── index.js
│   └── package.json
│
├── data/
│   ├── input/                           # Raw downloaded audio files
│   ├── content/                         # Processed/organized files
│   └── logs/                            # Logs written by logger.py
│
├── db/
│   └── metadata.sqlite                  # SQLite database for metadata (PoC)
│
├── tests/
│   ├── test_instagram_ingestion.py
│   ├── test_scheduler.py
│   └── test_metadata_db.py
│
├── PROJECT_OVERVIEW.md                  # High-level plan (living doc)
├── planning.md                          # Milestone plan (this document)
├── requirements.txt                     # Python dependencies
└── README.md                            # Setup instructions
```

**Metadata DB Schema (SQLite PoC)**

**Table: `media_metadata`**

| Field          | Type        | Notes                                |
| -------------- | ----------- | ------------------------------------ |
| source_id      | UUID (TEXT) | Unique ID per record                 |
| source_type    | TEXT        | instagram / youtube / journal / epub |
| original_url   | TEXT        | Original media URL                   |
| file_path      | TEXT        | Local path to stored file            |
| publish_date   | DATETIME    | Publish date from source             |
| author         | TEXT        | Username (Instagram) or channel name |
| length_seconds | INTEGER     | Media length in seconds              |
| language       | TEXT        | Language code if available           |
| license        | TEXT        | Copyright/license info               |
| ingest_date    | DATETIME    | When ingested                        |
| notes          | TEXT        | Free-form notes                      |