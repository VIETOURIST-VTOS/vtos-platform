.PHONY: up down logs test build prod backup
up:        ## chạy dev (db + api + web)
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f --tail=100
test:      ## pytest backend
	cd backend && pytest -q
prod:      ## chạy thật với tên miền trong .env
	docker compose -f docker-compose.prod.yml up -d --build
backup:
	docker compose exec db pg_dump -U vtos vtos | gzip > infra/backups/vtos_$$(date +%F_%H%M).sql.gz
