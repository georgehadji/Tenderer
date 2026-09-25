#!/usr/bin/env bash
# Mutation testing of core/pricing and core/rules (docs/architecture.md §13, H2), in a throwaway Linux container:
# mutmut needs fork(), and only git-tracked files go in (never discovery/). Config: [tool.mutmut] in pyproject.toml.
# Usage: scripts/mutation.sh            prints the tally and the diff of every surviving mutant
#        MIN_SCORE=900 scripts/mutation.sh   also fails when (killed + timeouts) per 1000 mutants is lower
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git ls-files -co --exclude-standard | grep -v '^discovery/' | tar -cf - -T - |
docker run -i --rm -e MIN_SCORE="${MIN_SCORE:-0}" python:3.14-slim@sha256:caaf356f40667c496d405780745b9ac25771c189a51dfcc42430d531ea09f8a2 sh -c '
set -e
mkdir /work && tar -xf - -C /work && cd /work
pip install -q uv==0.10.4 2>/dev/null
uv sync --locked -q
uv run -q --with "mutmut>=3,<4" mutmut run --max-children 4 >/tmp/run.log 2>&1 || { tail -20 /tmp/run.log; exit 1; }
uv run -q --with "mutmut>=3,<4" mutmut results --all true >/tmp/results.txt 2>/dev/null
echo "== tally"
awk -F": " "{print \$2}" /tmp/results.txt | sort | uniq -c
total=$(wc -l </tmp/results.txt); killed=$(grep -c ": killed" /tmp/results.txt || true)
timeouts=$(grep -c ": timeout" /tmp/results.txt || true)
score=$(( (killed + timeouts) * 1000 / total ))
echo "score: $score/1000 of $total mutants"
echo "== survivors"
for m in $(grep ": survived" /tmp/results.txt | cut -d: -f1); do
  uv run -q --with "mutmut>=3,<4" mutmut show "$m" 2>/dev/null | grep -E "^[-+][^-+]|^# " || true
  echo "--- $m"
done
[ "$score" -ge "$MIN_SCORE" ] || { echo "mutation score $score is below $MIN_SCORE"; exit 1; }
'
