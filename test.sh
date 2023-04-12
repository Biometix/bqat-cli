docker run --rm -it \
    --shm-size=8G \
    --cpus=8 \
    --memory=10G \
    -v "$(pwd)"/reports:/app/reports \
    bqat-cli \
    "python3.8 -m pytest tests --junitxml=reports/junit/junit.xml --html=reports/junit/report.html --self-contained-html && genbadge tests -o reports/junit/tests-badge.svg && touch config.py config-3.py && coverage run -m pytest tests && coverage xml -o reports/coverage/coverage.xml && coverage html -d reports/coverage/ && genbadge coverage -o reports/coverage/coverage-badge.svg"
