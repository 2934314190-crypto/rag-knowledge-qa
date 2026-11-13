import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.services.vector_store import vector_store  # noqa: E402


def main() -> None:
    if vector_store.is_connected():
        print(f"Milvus 已连接: {settings.milvus_uri}")
    else:
        print(f"无法连接 Milvus: {settings.milvus_uri}，请确认已启动")
        sys.exit(1)

    vector_store.ensure_collection()
    print(f"Collection 已就绪: {vector_store.collection} (dim={vector_store.dim})")
    print(f"当前文档切片数: {vector_store.count()}")


if __name__ == "__main__":
    main()