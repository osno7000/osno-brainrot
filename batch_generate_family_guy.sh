#!/bin/bash
# Batch generate all Peter+Stewie teaching videos

cd /home/osno/projects/osno-brainrot

TOPICS=(
  "salary_negotiation"
  "cashback_hack"
  "4_percent_rule"
  "keyboard_shortcuts"
  "inflation_cash"
  "sleep_debt"
)

echo "=== Batch generating $(echo ${#TOPICS[@]}) topics (compound_interest already done) ==="
echo ""

for topic in "${TOPICS[@]}"; do
  echo ">>> Generating: $topic"
  python3 generate_dialogue_video.py "$topic"
  echo ">>> Done: $topic"
  echo ""
done

echo "=== All done! ==="
ls -lh output/peter_stewie_*.mp4
