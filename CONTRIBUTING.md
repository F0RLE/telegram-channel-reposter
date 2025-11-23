# 🤝 Руководство по внесению вклада

## Процесс разработки

1. Создайте ветку от `main`
2. Внесите изменения
3. Напишите тесты для новых функций
4. Убедитесь, что все тесты проходят
5. Создайте Pull Request

## Стандарты кода

### Type Hints
Все функции должны иметь type hints:

```python
def my_function(param1: str, param2: int) -> bool:
    """Function description"""
    return True
```

### Docstrings
Все функции должны иметь docstrings в формате Google style:

```python
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
    """
    return True
```

### Обработка ошибок
Используйте централизованный error handler:

```python
from core.error_handler import ErrorHandler, retry_with_backoff

@retry_with_backoff()
async def my_function():
    try:
        # code
    except Exception as e:
        ErrorHandler.log_and_notify(e, "Context")
```

### Тестирование
- Покрытие должно быть >70%
- Все новые функции должны иметь тесты
- Используйте pytest и pytest-asyncio

## Коммиты

Используйте понятные сообщения коммитов:
- `feat: добавлена функция X`
- `fix: исправлена ошибка Y`
- `refactor: рефакторинг модуля Z`
- `test: добавлены тесты для X`

