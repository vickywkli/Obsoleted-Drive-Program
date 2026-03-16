python -m venv .venv
# Windows:
. .venv/Scripts/activate
# macOS/Linux:
# source .venv/bin/activate

pip install pandas numpy python-docx openpyxl pyyaml num2words
cp config/config.sample.yaml config/config.yaml
python scripts/run.py --config config/config.yaml --year 2024
