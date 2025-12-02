import os

# Папки/файлы, которые игнорируем
IGNORE = {"__pycache__", ".git", ".github"}

def build_tree(start_path, prefix="", is_last=True):
    items = [i for i in sorted(os.listdir(start_path)) if i not in IGNORE]
    tree = ""

    for index, item in enumerate(items):
        path = os.path.join(start_path, item)
        last = index == len(items) - 1

        branch = "└── " if last else "├── "
        tree += prefix + branch + item + "\n"

        if os.path.isdir(path):
            extension = "    " if last else "│   "
            tree += build_tree(path, prefix + extension, last)

    return tree


# Папка, где находится скрипт
current_folder = os.path.dirname(os.path.abspath(__file__))

# Файл для записи
output_file = os.path.join(current_folder, "file_tree.txt")

# Генерация дерева
tree_text = build_tree(current_folder)

# Сохранение дерева в файл
with open(output_file, "w", encoding="utf-8") as f:
    f.write(tree_text)

print("Дерево сохранено в:", output_file)
