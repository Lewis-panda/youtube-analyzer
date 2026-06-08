# SMA 期末報告 — LaTeX 專案

從頻道表現到留言社群洞察：台灣 YouTube 頻道的 Audience Intelligence 分析（以 The DoDo Men 為例）。

## 結構

```
report/
  main.tex              # 主檔：preamble（XeLaTeX + Noto CJK TC）+ \input 各章
  build.sh              # 一鍵編譯（呼叫 latexmk -xelatex）
  chapters/
    00_titlepage.tex    # 標題、組員、摘要
    01_motivation.tex   # 1 研究動機（RQ1–RQ5）
    02_literature.tex   # 2 文獻回顧
    03_data.tex         # 3 資料取得（含分析範圍表）
    04_methodology.tex  # 4 研究方法與分析框架（含衝突型態定義表）
    05_case_study.tex   # 5 個案分析：實際 DoDoMen 數據與表格，逐題回答 RQ
    06_conclusion.tex   # 6 結論與研究限制
    07_references.tex   # 參考文獻（natbib thebibliography）
    08_contribution.tex # 組內分工
  figures/
    fig_pipeline.tex    # TikZ 系統架構／資料流圖（Figure 1）
  data_facts.txt        # 撰寫 Ch5 時使用的權威數據摘錄（來源：dashboard / runs）
```

## 編譯環境

本報告為繁體中文，需以 **XeLaTeX** 編譯（系統字型 Noto Serif/Sans CJK TC）。

> 註：conda-forge 的 `texlive-core` 只含引擎、不含套件樹（fontspec/xeCJK/tikz 等都缺），
> 因此改用使用者本機的 **TinyTeX**（同為輕量 TeX Live，且附 `tlmgr` 可隨需安裝套件）。
> TinyTeX 安裝於 `~/.TinyTeX`，可跨專案重用。

### 一鍵編譯

```bash
bash build.sh           # 產生 main.pdf
```

`build.sh` 會把 `~/.TinyTeX/bin/x86_64-linux` 加入 PATH 後執行 `latexmk -xelatex main.tex`。

### 從零重建 TinyTeX（換機時）

```bash
curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh
export PATH="$HOME/.TinyTeX/bin/x86_64-linux:$PATH"
tlmgr install latexmk collection-latexrecommended collection-xetex \
  collection-pictures collection-fontsrecommended collection-langcjk \
  xecjk ctex setspace enumitem titlesec booktabs fancyhdr csquotes pgf \
  multirow makecell threeparttable wrapfig amsmath fontawesome5
```

字型需求：系統需安裝 `fonts-noto-cjk`（提供 Noto Serif/Sans CJK TC）與
Liberation 字型（Latin 正文，Times/Arial 相容）。

## 備註

- 第 5 章已填入實際分析數據（留言者分層、回訪率、3 個觀眾社群、ABSA 面向、衝突熱點、
  外部事件等），來源為本專案 dashboard 之 `dashboard_data/` 與 `runs/`，摘錄於 `data_facts.txt`。
- 目前頁數 18 頁（規定 18–22）。若需增頁，可在 5.2/5.3 補充更多 persona 細節或加入截圖。
