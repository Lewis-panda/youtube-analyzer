#!/usr/bin/env python3
import pandas as pd
import sqlite3
from pathlib import Path

def main():
    run_dir = Path("runs/dodomen-generic-demo")
    tables_dir = run_dir / "tables"
    
    # Load sentiment and comments
    sentiment_path = tables_dir / "qwen_comment_sentiment.csv"
    if not sentiment_path.exists():
        print("No sentiment found")
        return
    
    sentiment = pd.read_csv(sentiment_path)
    
    # Load ABSA negative if available
    absa_path = tables_dir / "qwen_comment_absa_negative.csv"
    absa = pd.read_csv(absa_path) if absa_path.exists() else pd.DataFrame()
    
    # Combine sentiment with ABSA
    if not absa.empty and "primary_aspect" in absa.columns:
        # The ABSA table uses source_id for the comment_id
        absa_simple = absa[["source_id", "primary_aspect"]].rename(columns={"source_id": "comment_id", "primary_aspect": "aspect"})
        absa_simple = absa_simple.drop_duplicates("comment_id")
        sentiment = sentiment.merge(absa_simple, on="comment_id", how="left")
        sentiment["aspect"] = sentiment["aspect"].fillna("other")
    else:
        sentiment["aspect"] = "other"
        
    # Per video ABSA summary
    neg_comments = sentiment[sentiment["sentiment_label"] == "negative"].copy()
    if not neg_comments.empty:
        aspect_counts = neg_comments.groupby(["video_id", "aspect"]).size().reset_index(name="count")
        video_totals = neg_comments.groupby("video_id").size().reset_index(name="total_negative")
        video_aspect_summary = aspect_counts.merge(video_totals, on="video_id")
        video_aspect_summary["aspect_share"] = video_aspect_summary["count"] / video_aspect_summary["total_negative"]
        video_aspect_summary = video_aspect_summary.sort_values(["video_id", "count"], ascending=[True, False])
        video_aspect_summary.to_csv(tables_dir / "video_aspect_summary.csv", index=False)
        print("Generated video_aspect_summary.csv")
        
    # Top Negative comments per video
    conn = sqlite3.connect("../SharedData/state/yt_graph.sqlite3")
    comments_df = pd.read_sql_query("SELECT comment_id, text_plain FROM comments", conn)
    conn.close()
    
    sentiment_with_text = neg_comments.merge(comments_df, on="comment_id", how="inner")
    
    # Sort by video and like_count desc, then take top 3
    sentiment_with_text = sentiment_with_text.sort_values(["video_id", "like_count"], ascending=[True, False])
    top_comments = sentiment_with_text.groupby("video_id").head(3)
    
    keep_cols = ["video_id", "comment_id", "text_plain", "like_count", "aspect"]
    top_comments[keep_cols].to_csv(tables_dir / "video_top_negative_comments.csv", index=False)
    print("Generated video_top_negative_comments.csv")

    # --- Positive ABSA: per-video aspect summary (aspects only, no raw text) ---
    absa_pos_path = tables_dir / "qwen_comment_absa_positive.csv"
    if absa_pos_path.exists():
        pos_absa = pd.read_csv(absa_pos_path)
        base = pd.read_csv(sentiment_path)
        if "primary_aspect" in pos_absa.columns and "comment_id" in base.columns:
            pos_map = (
                pos_absa[["source_id", "primary_aspect"]]
                .rename(columns={"source_id": "comment_id", "primary_aspect": "aspect"})
                .drop_duplicates("comment_id")
            )
            pos = base[base["sentiment_label"] == "positive"].merge(pos_map, on="comment_id", how="left")
            pos["aspect"] = pos["aspect"].fillna("other")
            pa = pos.groupby(["video_id", "aspect"]).size().reset_index(name="count")
            pt = pos.groupby("video_id").size().reset_index(name="total_positive")
            vps = pa.merge(pt, on="video_id")
            vps["aspect_share"] = vps["count"] / vps["total_positive"]
            vps = vps.sort_values(["video_id", "count"], ascending=[True, False])
            vps.to_csv(tables_dir / "video_positive_aspect_summary.csv", index=False)
            print("Generated video_positive_aspect_summary.csv")

            # channel-level positive aspect distribution (what the channel is praised for)
            cps = pos.groupby("aspect").size().reset_index(name="n_positive_mentions")
            cps["positive_aspect_share"] = cps["n_positive_mentions"] / cps["n_positive_mentions"].sum()
            cps = cps.sort_values("n_positive_mentions", ascending=False)
            cps.to_csv(tables_dir / "channel_positive_aspect_summary.csv", index=False)
            print("Generated channel_positive_aspect_summary.csv")

if __name__ == "__main__":
    main()
