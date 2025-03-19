import chromadb
import os
from .file_utils import *
import tiktoken

class VectorDatabase:

    def __init__(self, file_root, db_root, chunk_size: int=2000, tokenizer_name="cl100k_base"):
        self.tokenizer = tiktoken.get_encoding(tokenizer_name)
        cwd = os.getcwd()
        self.file_root_abs = safe_link_path(cwd, file_root, None)
        db_root_abs = safe_link_path(cwd, db_root, None)
        os.makedirs(db_root_abs, exist_ok=True)
        os.makedirs(file_root, exist_ok=True)

        db_path_abs = safe_link_path(db_root_abs, "../../../vdb/chroma.vdb", None)
        files_list_path_abs = safe_link_path(db_root_abs, "../../../vdb/files_list.txt", None)
        self.collection = VectorDatabase.load_collection(self.file_root_abs, db_path_abs, files_list_path_abs, chunk_size, self.tokenizer)

    @staticmethod
    def load_collection(file_root_path_abs, db_path, files_list_path, chunk_size,  encoding):
        db = chromadb.PersistentClient(path=db_path)
        collection = db.get_or_create_collection("main")
        def split_and_add_text(text, title):
            print(f"adding {title} to vdb...")
            nonlocal collection, chunk_size, encoding
            lines = text.splitlines()
            next_line_idx = 0
            while True:
                start_line_idx = next_line_idx
                text_chunk = ""
                text_chunk_num_tokens = 0
                while text_chunk_num_tokens < chunk_size and next_line_idx < len(lines):
                    next_line_content = lines[next_line_idx]
                    text_chunk += next_line_content + "\n"
                    text_chunk_num_tokens += len(encoding.encode(next_line_content))
                    next_line_idx += 1
                collection.add(
                    ids=[f"{start_line_idx}@{title}"],
                    documents=[text_chunk],
                    metadatas=[{"title": title}]
                )
                if next_line_idx >= len(lines):
                    break

        files_list_str = read_file(files_list_path)
        files_list = [] if files_list_str is None else files_list_str.split("\n")
        memory_files_set = set(files_list)
        new_files_set = set()
        def add_to_db(rel_path):
            nonlocal memory_files_set
            nonlocal new_files_set
            nonlocal file_root_path_abs
            abs_path = safe_link_path(file_root_path_abs, "." + rel_path, file_root_path_abs)
            assert os.path.exists(abs_path)
            if is_dir(abs_path):
                l = ls(abs_path)
                for name, _ in l:
                    new_rel_path = safe_link_path(rel_path, name, None)
                    add_to_db(new_rel_path)
            else:
                new_files_set.add(rel_path)
                if rel_path in memory_files_set:
                    memory_files_set.remove(rel_path)
                    return
                text = read_file(abs_path)
                split_and_add_text(text, rel_path)

        add_to_db("/")
        for file_path_rel in memory_files_set:
            collection.delete(where={"title": file_path_rel})
            print(f"removing {file_path_rel} from vdb...")
        new_files_list_str = "\n".join(new_files_set)
        overwrite_file(files_list_path, new_files_list_str)
        return collection

    def search(self, query: str, n_results: int=5) -> [(str, str, int)]:
        # return 值的每个元组是: (文件相对路径, text_chunk, text_chunk 的首行id)
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        ids = results["ids"][0]
        docs = results["documents"][0]
        to_return = []
        for i, string in enumerate(ids):
            line_idx_str, file_path_rel = string.split("@", 1)
            to_return.append((file_path_rel, docs[i], int(line_idx_str)))
        return to_return
