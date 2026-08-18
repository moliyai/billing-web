.PHONY: clean clean-pycache clean-migrations

clean: clean-pycache clean-migrations

clean-pycache:
	@echo "Cleaning __pycache__ and compiled Python files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete

clean-migrations:
	@echo "Cleaning migration files..."
	find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
	find . -path "*/migrations/*.pyc" -delete
