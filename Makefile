
lint:
	docker run -v ${CURDIR}:/apps registry.ubicast.net/docker/flake8:latest make lint_local

lint_local:
	flake8 .

deadcode:
	docker run -v ${CURDIR}:/apps registry.ubicast.net/docker/vulture:latest make deadcode_local

deadcode_local:
	vulture --exclude ms_client/ --min-confidence 90 .
