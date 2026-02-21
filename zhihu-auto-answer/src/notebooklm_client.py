"""
NotebookLM 知识检索客户端
运行时从 NotebookLM 笔记本中检索与问题相关的素材
作为回答生成的 RAG（检索增强生成）层
"""

import os
import asyncio
import json


def _get_or_create_event_loop():
    """获取或创建事件循环（兼容不同运行环境）"""
    try:
        loop = asyncio.get_running_loop()
        # 如果已有运行中的循环，需要在新线程中运行
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool
    except RuntimeError:
        return None


async def _async_query(notebook_id: str, question: str, timeout: float = 30.0) -> dict:
    """异步查询 NotebookLM"""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage(timeout=timeout) as client:
        result = await client.chat.ask(notebook_id, question)
        return {
            "answer": result.answer,
            "references": [
                {
                    "source_id": ref.source_id,
                    "cited_text": ref.cited_text or "",
                    "citation_number": ref.citation_number,
                }
                for ref in (result.references or [])
            ],
            "conversation_id": result.conversation_id,
        }


def query_notebook(notebook_id: str, question: str, timeout: float = 30.0) -> dict:
    """同步包装：查询 NotebookLM 笔记本

    Args:
        notebook_id: NotebookLM 笔记本 ID
        question: 要查询的问题
        timeout: 超时时间（秒）

    Returns:
        {"answer": str, "references": list, "conversation_id": str}
        失败时返回 {"answer": "", "references": [], "error": str}
    """
    try:
        result = asyncio.run(_async_query(notebook_id, question, timeout))
        return result
    except Exception as e:
        return {"answer": "", "references": [], "error": str(e)}


async def _async_list_notebooks() -> list:
    """异步列出所有笔记本"""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()
        return [
            {"id": nb.id, "title": nb.title}
            for nb in notebooks
        ]


def list_notebooks() -> list:
    """同步包装：列出所有笔记本"""
    try:
        return asyncio.run(_async_list_notebooks())
    except Exception as e:
        print(f"   列出笔记本失败: {e}")
        return []


def retrieve_materials(question_title: str) -> str:
    """根据问题从 NotebookLM 检索相关素材

    这是生成器调用的主入口。流程：
    1. 从环境变量获取 notebook_id
    2. 构造检索 prompt
    3. 查询 NotebookLM
    4. 格式化返回结果

    Returns:
        格式化的素材文本，可直接嵌入生成 prompt
        失败时返回空字符串
    """
    notebook_id = os.environ.get("NOTEBOOKLM_NOTEBOOK_ID", "").strip()
    if not notebook_id:
        print("   ⚠️  未配置 NOTEBOOKLM_NOTEBOOK_ID，跳过 NotebookLM 检索")
        return ""

    # 检查认证是否可用，将环境变量写成文件供 notebooklm-py 读取
    auth_json = os.environ.get("NOTEBOOKLM_AUTH_JSON", "").strip()
    auth_file = os.path.expanduser("~/.notebooklm/storage_state.json")
    if auth_json and not os.path.exists(auth_file):
        os.makedirs(os.path.dirname(auth_file), exist_ok=True)
        with open(auth_file, "w") as f:
            f.write(auth_json)
        print(f"   ✅ 已从环境变量写入认证文件: {auth_file}")
    if not auth_json and not os.path.exists(auth_file):
        print("   ⚠️  未找到 NotebookLM 认证信息，跳过检索")
        return ""

    # 构造检索 prompt——引导 NotebookLM 返回结构化的行业素材
    retrieval_prompt = (
        f"我要回答一个知乎问题：「{question_title}」\n\n"
        "请从笔记本中找出与这个问题最相关的内容，包括：\n"
        "1. 具体的项目案例或经历（有时间、数字、结果的）\n"
        "2. 行业数据或技术指标\n"
        "3. 有争议性或反常识的观点\n"
        "4. 内部人才知道的信息差\n\n"
        "直接列出要点，不需要写成完整文章。"
    )

    print(f"   📚 正在从 NotebookLM 检索相关素材...")
    result = query_notebook(notebook_id, retrieval_prompt, timeout=45.0)

    if result.get("error"):
        print(f"   ⚠️  NotebookLM 检索失败: {result['error']}")
        return ""

    answer = result.get("answer", "").strip()
    if not answer or len(answer) < 50:
        print(f"   ⚠️  NotebookLM 返回内容过短（{len(answer)}字），跳过")
        return ""

    # 格式化检索结果
    formatted = f"【NotebookLM 知识库检索结果】\n{answer}"

    # 如果有引用来源，附上
    refs = result.get("references", [])
    if refs:
        cited_texts = [r["cited_text"] for r in refs if r.get("cited_text")]
        if cited_texts:
            formatted += "\n\n【原始引用片段】\n"
            for i, text in enumerate(cited_texts[:5], 1):
                formatted += f"{i}. {text[:200]}\n"

    print(f"   ✅ NotebookLM 检索成功（{len(answer)}字）")
    return formatted
