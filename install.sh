#!/bin/bash

set -e

python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt

cat > mhy << EOF
#!/bin/bash

cd "$(pwd)" || exit 1

source ./venv/bin/activate

python MHY.py "\$@"
EOF

chmod +x mhy
