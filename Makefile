APP_NAME := xvg-cli
ENTRY_POINT := ./src/main.py

.PHONY: install build clean

# Установка зависимостей из uv.lock
install:
	uv sync

# Сборка одного исполняемого файла в папку dist/
build: install
	uv run pyinstaller \
		--onefile \
		--clean \
		--name $(APP_NAME) \
		--add-data "pyproject.toml:." \
		--add-data "src/migrations:src/migrations" \
		--hidden-import=yoyo.backends.core.sqlite3 \
  		--copy-metadata=yoyo-migrations \
		$(ENTRY_POINT)

# Очистка артефактов сборки
clean:
	rm -rf build dist *.spec
