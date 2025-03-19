from pathlib import Path
import os

def safe_link_path(base_path: str, add_path: str, root_path: str) -> str:
    def link_path(base_path, add_path):
        if os.path.isabs(add_path):
            return add_path
        else:
            return str((Path(base_path) / add_path).resolve())
    def is_ancestor(ancestor, path):
        if ancestor is None:
            return True
        ancestor_path = Path(ancestor).resolve()
        path = Path(path).resolve()
        return path.is_relative_to(ancestor_path)
    new_path = link_path(base_path, add_path)
    if is_ancestor(root_path, new_path):
        return new_path
    else:
        return root_path

def is_dir(path):
    return os.path.isdir(path)

def ls(path):
    l = []
    with os.scandir(path) as entries:
        for entry in entries:
            l.append((entry.name, entry.is_dir()))
    return l

def read_file(file_path) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return None
    except UnicodeDecodeError:
        return None

def getcwd():
    return os.getcwd()

def overwrite_file(file_path, content):
    """
    覆写文件，无论文件是否存在，都将其内容替换为给定字符串。

    :param file_path: str, 文件路径
    :param content: str, 要写入的内容
    """
    with open(file_path, 'w') as file:
        file.write(content)