build:
	docker-compose build

up:
	docker-compose up --build backend

down:
	docker-compose down

logs:
	docker-compose logs -f backend

shell:
	docker-compose run --rm backend bash

test:
	docker-compose run --rm backend pytest tests/

format:
	docker-compose run --rm backend black delivery_box/
	docker-compose run --rm backend isort delivery_box/

check:
	docker-compose run --rm backend mypy delivery_box/
	docker-compose run --rm backend pylint delivery_box/