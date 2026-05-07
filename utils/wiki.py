import re
from typing import Any

import httpx

from astrbot.api import logger
from astrbot.api.star import Context

WIKI_API_URL = "https://zh.minecraft.wiki/api.php"

EXTRACT_PROMPT = (
    "从用户的问题中提取要查询的 Minecraft Wiki 页面标题。"
    "只输出页面标题，不要输出任何其他内容。"
    "示例：\n"
    "问：黑曜石的抗爆性是多少 → 黑曜石\n"
    "问：凋零骷髅有什么行为 → 凋灵骷髅\n"
    "问：末影人有什么特性 → 末影人\n"
    "问：/tp 怎么用 → 命令/tp\n"
    "问：附魔台怎么合成 → 附魔台\n"
)

SYSTEM_PROMPT = (
    "你是一个 Minecraft Wiki 助手。根据提供的 Wiki 页面内容，直接回答用户的问题。"
    "回答要简洁准确，先给结论，再给关键细节。但不要提到“结论”和“关键细节”这些关键词，分行就行。使用中文回答。"
    "如果 Wiki 内容中没有相关信息，明确说明未找到。"
)


def _strip_templates(text: str) -> str:
    old = None
    cur = text
    while old != cur:
        old = cur
        cur = re.sub(r"\{\{[^{}]*\}\}", "", cur)
    return cur


def clean_wikitext(text: str, max_chars: int = 6000) -> str:
    if not text:
        return ""
    text = re.sub(
        r"\{\{cmd\|(?:long=\d\|)?(?:link=none\|)?([^{}|]+)\}\}", r"\1", text, flags=re.I
    )
    text = re.sub(r"\{\{cd\|([^{}|]+)\}\}", r"\1", text, flags=re.I)
    text = re.sub(
        r"\{\{[Cc]ollapse\|title=.*?\|content=(.*?)\}\}", r"\1", text, flags=re.S
    )
    text = re.sub(r"\{\{[^{}|]+\|([^{}]+?)\}\}", r"\1", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S | re.I)
    text = re.sub(r"<ref[^/]*/>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = _strip_templates(text)
    text = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[https?://[^\s\]]+\s+([^\]]+)\]", r"\1", text)
    text = re.sub(r"\[https?://[^\s\]]+\]", "", text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"-\{([^{}]+)\}-", r"\1", text)
    text = re.sub(r"\*:\s*", "", text)
    text = re.sub(r"^\s*=+\s*(.*?)\s*=+\s*$", r"\1", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "..."
    return text


REDIRECT_RE = re.compile(r"#(?:redirect|重定向)\s*\[\[(.*?)\]\]", re.I)


class WikiUtils:
    def __init__(self, context: Context):
        self.context = context
        self._client = httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": "astrbot-plugin-mc-admin-wiki/1.0"},
        )

    async def close(self):
        await self._client.aclose()

    async def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        payload = {"format": "json", **params}
        resp = await self._client.get(WIKI_API_URL, params=payload)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("error"):
            return {"error": data["error"]}
        return data

    async def search_page(self, query: str, limit: int = 3) -> list[dict[str, str]]:
        """搜索关键词"""
        data = await self._request(
            {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": limit,
            }
        )
        results = []
        for item in data.get("query", {}).get("search", []):
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
            results.append(
                {
                    "title": item.get("title", ""),
                    "snippet": snippet,
                }
            )
        return results

    def _strip_html(self, html: str) -> str:
        """去除 HTML 标签，清理渲染后的页面内容。"""
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S | re.I)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S | re.I)
        text = re.sub(r"<sup[^>]*>.*?</sup>", "", text, flags=re.S | re.I)
        text = re.sub(r'<span class="mw-headline"[^>]*>(.*?)</span>', r"\n\1\n", text)
        text = re.sub(r"<h[1-6][^>]*>", "\n", text)
        text = re.sub(r"</h[1-6]>", "\n", text)
        text = re.sub(r"<li[^>]*>", "- ", text)
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"<tr[^>]*>", "\n", text)
        text = re.sub(r"<td[^>]*>", " | ", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&quot;", '"', text)
        text = re.sub(r"&#\d+;", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    async def get_page_text(self, title: str) -> str:
        """通过 action=parse&prop=text 获取完整的渲染页面文本。"""
        data = await self._request(
            {
                "action": "parse",
                "page": title,
                "prop": "text",
            }
        )
        html = data.get("parse", {}).get("text", "")
        if isinstance(html, dict):
            html = html.get("*", "")
        if not html:
            return ""
        return self._strip_html(html)

    async def get_page_wikitext(self, title: str) -> str:
        data = await self._request(
            {
                "action": "parse",
                "page": title,
                "prop": "wikitext",
            }
        )
        wikitext = data.get("parse", {}).get("wikitext", "")
        if isinstance(wikitext, dict):
            wikitext = wikitext.get("*", "")
        return wikitext or ""

    async def _resolve_redirect(self, title: str, wikitext: str) -> str:
        match = REDIRECT_RE.search(wikitext)
        if match:
            return match.group(1).strip()
        return title

    async def _extract_title(self, provider, question: str) -> str:
        """使用 LLM 从用户问题中提取 Wiki 页面标题。"""
        try:
            resp = await provider.text_chat(
                prompt=question,
                system_prompt=EXTRACT_PROMPT,
            )
            if resp.role == "err":
                return ""
            title = resp.completion_text.strip()
            # 清理 LLM 输出中的常见杂质字符
            title = title.strip('"\'「」《》')
            title = re.sub(r"\s+", " ", title)
            return title
        except Exception as e:
            logger.warning(f"Title extraction failed: {e}")
            return ""

    async def _fetch_page_content(self, title: str) -> tuple[str, str]:
        """获取页面内容。返回 (解析后的标题, 页面文本)。"""
        # 获取 wikitext 以解析重定向
        wikitext = await self.get_page_wikitext(title)
        if wikitext:
            resolved = await self._resolve_redirect(title, wikitext)
            if resolved != title:
                title = resolved
                wikitext = await self.get_page_wikitext(title)

        # 获取完整的渲染页面文本
        page_text = await self.get_page_text(title)
        if not page_text:
            page_text = clean_wikitext(wikitext, max_chars=8000) if wikitext else ""
        return title, page_text

    async def query_wiki(self, question: str) -> str:
        """搜索 Wiki，获取完整页面内容，使用 LLM 回答。"""
        try:
            provider = self.context.get_using_provider()
            if not provider:
                return "未配置 LLM，无法使用 Wiki 查询功能。"

            # 使用 LLM 从问题中提取关键词
            extracted_title = await self._extract_title(provider, question)
            logger.info(f"Wiki 查询：从 '{question}' 提取标题 '{extracted_title}'")

            # 用提取的关键词搜索，失败则用原始问题搜索
            title = ""
            page_text = ""

            if extracted_title:
                search_results = await self.search_page(extracted_title, limit=1)
                if search_results:
                    title = search_results[0]["title"]
                    title, page_text = await self._fetch_page_content(title)

            # 降级：用原始问题搜索
            if not page_text:
                search_results = await self.search_page(question, limit=1)
                if search_results:
                    title = search_results[0]["title"]
                    title, page_text = await self._fetch_page_content(title)

            if not page_text:
                return f"未找到「{extracted_title or question}」的 Wiki 页面内容。"

            if len(page_text) > 8000:
                page_text = page_text[:8000] + "..."

            # 使用 LLM 基于完整页面内容回答
            prompt = (
                f"Wiki 页面：{title}\n\n"
                f"页面内容：\n{page_text}\n\n"
                f"用户问题：{question}\n\n"
                f"请根据上述 Wiki 内容直接回答用户的问题。"
            )

            resp = await provider.text_chat(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
            )

            if resp.role == "err":
                logger.error(f"Wiki LLM 调用失败: {resp.completion_text}")
                return f"Wiki 查询成功但 LLM 处理失败，原始摘要：\n{page_text[:2000]}"

            answer = resp.completion_text.strip()
            if not answer:
                return f"Wiki 查询成功但 LLM 未返回有效答案，原始摘要：\n{page_text[:2000]}"

            return answer

        except httpx.HTTPStatusError as e:
            logger.error(f"Wiki API HTTP 错误: {e}")
            return f"Wiki 请求失败（HTTP {e.response.status_code}），请稍后重试。"
        except httpx.RequestError as e:
            logger.error(f"Wiki API 请求错误: {e}")
            return "Wiki 请求失败，请检查网络连接。"
        except Exception as e:
            logger.exception(f"Wiki 查询异常: {e}")
            return f"Wiki 查询出错：{e}"
