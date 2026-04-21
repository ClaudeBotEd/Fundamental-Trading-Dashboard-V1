.PHONY: backend test install vault-check frontend

backend:
	cd backend && uv run uvicorn main:app --reload --port 8000

test:
	cd backend && uv run pytest -v

install:
	cd backend && uv sync

vault-check:
	cd backend && uv run python -c \
		"from core.config import settings; from core.vault import VaultWriter; \
		vw = VaultWriter(settings.obsidian_vault_path); \
		print('Vault OK:', vw.vault_path, '| Exists:', vw.vault_path.exists())"

frontend:
	cd frontend && npm run dev
