#!/bin/bash
# Batch generate Reddit brainrot Shorts
# Usage: ./batch_generate_reddit.sh <subreddit> <batch_name> <count>
# Example: ./batch_generate_reddit.sh tifu batch4 10

SUBREDDIT="${1:-tifu}"
BATCH="${2:-batch4}"
COUNT="${3:-10}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output/$BATCH"

mkdir -p "$OUTPUT_DIR"

echo "=== Generating $COUNT videos from r/$SUBREDDIT → $BATCH ==="
echo ""

MANIFEST="[]"
SUCCESS=0

for i in $(seq 1 $COUNT); do
    NUM=$(printf "%02d" $i)
    echo ">>> [$i/$COUNT] Generating short${BATCH#batch}_${NUM}.mp4 from r/$SUBREDDIT"

    # Run generator
    python3 "$SCRIPT_DIR/main.py" --subreddit "$SUBREDDIT" 2>&1
    EXIT=$?

    if [ $EXIT -eq 0 ]; then
        # Find the most recently created short_ file
        LATEST=$(ls -t "$SCRIPT_DIR/output/short_"*.mp4 2>/dev/null | head -1)
        if [ -n "$LATEST" ]; then
            DEST="$OUTPUT_DIR/short${BATCH#batch}_${NUM}.mp4"
            mv "$LATEST" "$DEST"
            echo ">>> Saved: $DEST"
            SUCCESS=$((SUCCESS + 1))
        fi
    else
        echo ">>> ERROR on video $i, skipping"
    fi

    # Small pause between videos
    sleep 2
done

echo ""
echo "=== Done: $SUCCESS/$COUNT videos generated in output/$BATCH/ ==="
ls -lh "$OUTPUT_DIR/"
