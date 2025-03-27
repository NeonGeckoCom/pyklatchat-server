python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements/requirements.txt
pip install -r requirements/dev_requirements.txt

pre-commit install
./bin/fmt.sh
