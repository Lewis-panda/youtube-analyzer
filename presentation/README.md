# 期末報告簡報（PPT）

`deck.pptx` ─ 15 頁、16:9、可直接匯入 Google Slides 再編輯。
風格：暖白底 `#faf7f3`＋深藍字 `#073763`＋teal `#0faf7f` 點綴，字型 Noto Sans TC（Google Slides 內建），Apple 風。

## 內容流程（13 分鐘 / 約 52 秒一頁）
標題 → 研究動機 → 研究缺口 → 研究問題(RQ1–4) → 資料 → 系統架構 →
RQ1 頻道健康 → RQ2 三社群 → RQ3 情緒主體 → RQ3 內容敏感度(8pp) → RQ4 留言衝突 →
策略 → 限制 → 結論 → 謝謝/Q&A。
RQ 結果頁皆配 dashboard 實際截圖。

## 重建方式（兩個環境）
1. **截 dashboard 圖**（需 dashboard 在 127.0.0.1:8000；playwright 在 SMA env）：
   ```bash
   ~/micromamba/envs/SMA/bin/python presentation/capture.py     # -> assets/*.png
   ```
2. **產 pptx ＋ 預覽 PNG**（pptx + Pillow 在系統 python3）：
   ```bash
   python3 presentation/build_deck.py                           # -> deck.pptx + preview/s01..s15.png
   ```

## 檔案
- `deck.pptx` ─ 交付檔
- `build_deck.py` ─ 版面引擎（同一份規格同時產 pptx 與 PNG 預覽）
- `deck_content.py` ─ 每頁文字／數據內容
- `capture.py` ─ playwright 截 dashboard 面板
- `assets/` ─ dashboard 截圖；`preview/` ─ 每頁 PNG 預覽（QC 用）

> 註：本機無 libreoffice，無法直接把 pptx render 成圖；`preview/s*.png` 是用同一套座標另外畫的「忠實預覽」，最終仍請在 Google Slides 開 `deck.pptx` 確認。
