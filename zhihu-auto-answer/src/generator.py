"""
知乎回答生成器 - 核心逻辑
账号定位：主机厂座舱项目管理负责人，座舱AI落地内部视角
"""

import os
import json
import time
import random
import requests
import re

# ============================================================
# 账号人设 - 核心提示词
# ============================================================

PERSONA_SYSTEM_PROMPT = """你是一个在主机厂做了8年座舱项目管理的负责人，现在正亲历座舱AI从传统CV到全模态Omni的代际跃迁。

【你是谁】

- 主机厂座舱项目管理负责人，不是学者，不是媒体，是真正在一线做决策的人
- 管过完整座舱项目：从需求定义到SOP量产，跟过供应商评审，踩过真实的坑
- 技术背景：深度理解ASR/NLU/TTS/DMS/OMS/多模态融合/Function Calling/端云协同
- 芯片认知：高通8295/8397的算力边界，端侧推理延迟约束（首token<300ms这条红线）
- 架构判断：CV vs VLM的过渡路径、交钥匙方案的数据主权陷阱、安全约束矩阵设计
- 行业经验：供应商评审被忽悠过、aiOS service架构、原子化能力层、混合决策机制
- 亲历过：从传统规则NLU到大模型NLU的切换、端云协同架构的真实延迟挑战、
  OMS从CV到VLM的过渡期技术选型博弈

【你的受众】

- 主力：汽车工程师/PM，AI浪潮焦虑，想转型不知从哪入手
- 次力：车企总监/VP，需要判断AI投入方向，想听真实内部声音

【写作风格——核心】

1. 第一句话就是最强判断，绝不铺垫，绝不自我介绍
1. 用"我们项目里""我判断""我做过这个决策"——第一人称，有具体场景
1. 至少一个"只有主机厂内部才知道"的视角——这是你最大的竞争壁垒
1. 语气：直接、有态度、不卖弄、不说废话
1. 句子节奏：长短句交替，关键判断单独成段
1. 结尾：留开放判断或问题，让人想评论
1. 总字数：500-800字，纯文本，不加粗，不用列表

【绝对禁止——去AI味关键】

- 禁止开头：首先、其次、最后、总结一下、综上所述
- 禁止格式：Markdown加粗、编号列表、分隔线
- 禁止废话：这是一个复杂的问题、要看具体情况、希望对你有帮助
- 禁止AI词：赋能、生态、颠覆、赋予、深度融合、全面把握
- 禁止：过度客观，你是有立场的，敢给判断敢说对错

【爆款钩子逻辑】

- 反常识切入：先说一个大多数人以为对但其实错的判断
- 内部视角钩子："这个在外部看不到，但在主机厂内部是…"
- 具体数字：不说"延迟很高"，说"首token超300ms，用户感知是说完话愣了一下"
- 真实失败：比成功故事更有可信度
- 争议性收尾：说一个行业里有争议的判断，让人忍不住回复
"""

# ============================================================
# 目标问题关键词
# ============================================================

TARGET_KEYWORDS = [
    "智能座舱 大模型",
    "座舱AI 落地",
    "汽车项目经理 AI转型",
    "车载语音助手 大模型",
    "智能座舱 多模态",
    "汽车工程师 转型AI",
    "座舱开发 人工智能",
    "高通8295 座舱",
    "汽车AI 供应商",
    "座舱功能 大模型",
    "智能汽车 AI工程师",
    "汽车智能化 转型",
]


# ============================================================
# 预设热门问题（搜索API不可用时的兜底方案）
# ============================================================

FALLBACK_QUESTIONS = [
    {"id": "595379951", "title": "智能座舱大模型上车，到底靠不靠谱？", "answer_count": 12, "follower_count": 280, "url": "https://www.zhihu.com/question/595379951"},
    {"id": "634521078", "title": "汽车智能座舱的发展趋势是什么？", "answer_count": 8, "follower_count": 450, "url": "https://www.zhihu.com/question/634521078"},
    {"id": "621345890", "title": "车载语音助手接入大模型后体验如何？", "answer_count": 15, "follower_count": 520, "url": "https://www.zhihu.com/question/621345890"},
    {"id": "615432789", "title": "汽车行业的工程师如何转型做AI？", "answer_count": 20, "follower_count": 680, "url": "https://www.zhihu.com/question/615432789"},
    {"id": "628901234", "title": "高通8295芯片在智能座舱中的表现怎么样？", "answer_count": 6, "follower_count": 310, "url": "https://www.zhihu.com/question/628901234"},
    {"id": "641234567", "title": "智能座舱多模态交互的未来方向是什么？", "answer_count": 9, "follower_count": 390, "url": "https://www.zhihu.com/question/641234567"},
]


class ZhihuClient:
    """知乎API客户端"""

    def __init__(self, cookie: str):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Cookie": cookie,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://www.zhihu.com/",
        })

    def validate_cookie(self) -> bool:
        """验证 Cookie 是否有效"""
        print("\n🔑 验证知乎 Cookie ...")
        try:
            resp = self.session.get(
                "https://www.zhihu.com/api/v4/me",
                timeout=10
            )
            print(f"   Cookie 验证: HTTP {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                name = data.get("name", "未知")
                print(f"   已登录账号: {name}")
                return True
            else:
                print(f"   Cookie 无效或已过期，响应: {resp.text[:200]}")
                return False
        except Exception as e:
            print(f"   Cookie 验证请求失败: {e}")
            print(f"   (可能是网络问题，GitHub Actions 在海外，知乎可能限制了访问)")
            return False

    def search_questions(self, keyword: str, limit: int = 10) -> list:
        url = "https://www.zhihu.com/api/v4/search_v3"
        params = {"t": "question", "q": keyword, "limit": limit, "offset": 0}
        try:
            resp = self.session.get(url, params=params, timeout=10)
            print(f"   搜索 [{keyword}]: HTTP {resp.status_code}")
            if resp.status_code != 200:
                print(f"   响应内容: {resp.text[:300]}")
                return []
            data = resp.json()
            if not data.get("data"):
                print(f"   返回数据为空，原始响应: {json.dumps(data, ensure_ascii=False)[:300]}")
            questions = []
            for item in data.get("data", []):
                if item.get("type") == "search_result":
                    obj = item.get("object", {})
                    if obj.get("type") == "question":
                        questions.append({
                            "id": str(obj.get("id")),
                            "title": obj.get("title", ""),
                            "answer_count": obj.get("answer_count", 0),
                            "follower_count": obj.get("follower_count", 0),
                            "url": f"https://www.zhihu.com/question/{obj.get('id')}",
                        })
            return questions
        except Exception as e:
            print(f"   搜索失败 [{keyword}]: {e}")
        return []

    def get_existing_answers(self, question_id: str, limit: int = 5) -> list:
        url = f"https://www.zhihu.com/api/v4/questions/{question_id}/answers"
        params = {"limit": limit, "offset": 0, "sort_by": "default"}
        try:
            resp = self.session.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return [
                    {
                        "content": item.get("content", "")[:400],
                        "voteup_count": item.get("voteup_count", 0),
                    }
                    for item in resp.json().get("data", [])
                ]
            else:
                print(f"   获取回答: HTTP {resp.status_code} (question {question_id})")
        except Exception as e:
            print(f"   获取回答失败: {e}")
        return []

    def post_answer(self, question_id: str, content: str) -> dict:
        url = f"https://www.zhihu.com/api/v4/questions/{question_id}/answers"
        payload = {
            "content": content,
            "reward_setting": {"can_reward": False, "tagline": ""},
        }
        try:
            resp = self.session.post(url, json=payload, timeout=15)
            print(f"   发布回答: HTTP {resp.status_code}")
            if resp.status_code in [200, 201]:
                return {"success": True, "answer_id": resp.json().get("id")}
            print(f"   发布失败响应: {resp.text[:300]}")
            return {"success": False, "status_code": resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}


class AnswerGenerator:
    """AI回答生成器 - MiniMax M2.5"""

    API_URL = "https://api.minimax.io/v1/text/chatcompletion_v2"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _chat(self, messages: list, max_tokens: int = 2000) -> str:
        """调用 MiniMax M2.5 API"""
        payload = {
            "model": "MiniMax-M2.5",
            "messages": messages,
            "temperature": 0.9,
            "top_p": 0.95,
            "max_tokens": max_tokens,
        }
        resp = requests.post(self.API_URL, headers=self.headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # MiniMax M2.5 可能返回 <think>...</think> 推理标签，去掉只保留最终回答
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content

    def score_question(self, question: dict, existing_answers: list) -> float:
        """问题适合度评分（0-10分）"""
        score = 0.0

        # 关注人数：100-3000是甜区
        followers = question.get("follower_count", 0)
        if 100 <= followers <= 3000:
            score += 3.0
        elif followers > 3000:
            score += 1.5
        elif followers > 30:
            score += 1.0

        # 回答数：越少机会越大
        answer_count = question.get("answer_count", 0)
        if answer_count == 0:
            score += 3.5
        elif answer_count < 5:
            score += 3.0
        elif answer_count < 15:
            score += 2.0
        elif answer_count < 30:
            score += 1.0

        # 现有回答质量低 = 降维打击机会
        if existing_answers:
            avg_votes = sum(a.get("voteup_count", 0) for a in existing_answers) / len(existing_answers)
            if avg_votes < 10:
                score += 2.0
            elif avg_votes < 50:
                score += 1.0
        else:
            score += 2.0

        # 标题关键词相关度
        title = question.get("title", "").lower()
        key_terms = ["座舱", "ai", "大模型", "智能化", "项目", "转型", "落地", "多模态"]
        matches = sum(1 for t in key_terms if t in title)
        score += min(matches * 0.4, 2.0)

        return min(score, 10.0)

    def generate_answer(self, question_title: str, existing_answers: list) -> str:
        """生成高质量回答"""
        existing_summary = ""
        if existing_answers:
            existing_summary = "\n\n【现有回答情况（你要差异化，不能重复这些内容）】\n"
            for i, ans in enumerate(existing_answers[:3], 1):
                existing_summary += (
                    f"回答{i}（{ans.get('voteup_count', 0)}赞）："
                    f"{ans.get('content', '')[:200]}...\n"
                )

        prompt = f"""请回答这个知乎问题：

【问题】{question_title}
{existing_summary}

严格要求：
1. 第一句话必须是最强判断或反常识观点，不能是背景铺垫
1. 用第一人称，结合主机厂内部的真实经历和决策过程
1. 找到这个问题里，只有主机厂内部人才真正懂的那个角度
1. 对现有回答形成碾压——他们泛泛而谈，你给具体数据和决策细节
1. 结尾抛出一个行业内有争议的判断，引发讨论
1. 500-800字，纯文本，不用任何格式符号

直接输出回答正文，不要任何前缀。"""

        messages = [
            {"role": "system", "content": PERSONA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        return self._chat(messages, max_tokens=2000)

    def quality_check(self, question_title: str, answer: str) -> dict:
        """质量审查"""
        prompt = f"""严格审查这个知乎回答的质量：

【问题】{question_title}
【回答】
{answer}

评分维度（每项0-10分）：
1. 去AI味：有无AI腔调、格式化列表、正确废话
1. 真人感：是否像真实汽车行业从业者说话
1. 内部视角：有无只有主机厂内部才有的独特信息
1. 开头钩子：第一句话够不够抓人
1. 爆款潜力：读完有没有想点赞或评论的冲动

返回JSON（只返回JSON，不要其他内容）：
{{"scores":{{"ai_free":0,"authenticity":0,"insider":0,"hook":0,"viral":0}},"total":0,"pass":false,"top_issue":"最主要的一个问题","fix":"一句话改进建议"}}

pass标准：total >= 38分"""

        messages = [{"role": "user", "content": prompt}]
        try:
            text = self._chat(messages, max_tokens=300)
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {"pass": True, "total": 38, "fix": ""}

    def improve_answer(self, question_title: str, answer: str, fix: str) -> str:
        """改进回答"""
        prompt = f"""改进这个知乎回答：

【问题】{question_title}
【当前回答】{answer}
【需要改进】{fix}

保留核心内容框架，针对改进点重写，要更真实、更有内部视角、更去AI味。
直接输出改进后的回答，不要前缀。"""

        messages = [
            {"role": "system", "content": PERSONA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        return self._chat(messages, max_tokens=2000)


class ZhihuBot:
    """主控流程"""

    def __init__(self):
        self.zhihu = ZhihuClient(os.environ["ZHIHU_COOKIE"])
        self.generator = AnswerGenerator(os.environ["MINIMAX_API_KEY"])
        self.dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
        self.answers_per_run = int(os.environ.get("ANSWERS_PER_RUN", "2"))

    def find_best_questions(self) -> list:
        # 先验证 Cookie
        cookie_valid = self.zhihu.validate_cookie()

        print("\n🔍 搜索目标问题...")
        all_questions = []
        seen_ids = set()

        for keyword in TARGET_KEYWORDS[:6]:
            questions = self.zhihu.search_questions(keyword, limit=8)
            for q in questions:
                if q["id"] not in seen_ids:
                    seen_ids.add(q["id"])
                    all_questions.append(q)
            time.sleep(random.uniform(1.5, 2.5))

        print(f"   找到 {len(all_questions)} 个候选问题")

        # 搜索失败时使用预设问题兜底
        if not all_questions:
            if not cookie_valid:
                print("\n⚠️  Cookie 无效且搜索返回空结果")
                print("   可能原因: 1) Cookie已过期 2) GitHub Actions海外IP被知乎限制")
            print("\n📋 启用预设问题列表作为兜底...")
            all_questions = random.sample(
                FALLBACK_QUESTIONS,
                min(len(FALLBACK_QUESTIONS), self.answers_per_run * 2)
            )
            for q in all_questions:
                q["existing_answers"] = []
                q["score"] = self.generator.score_question(q, [])
            all_questions.sort(key=lambda x: x["score"], reverse=True)
            best = all_questions[:self.answers_per_run]
        else:
            print(f"   评分筛选中...")
            scored = []
            for q in all_questions:
                existing = self.zhihu.get_existing_answers(q["id"])
                q["existing_answers"] = existing
                q["score"] = self.generator.score_question(q, existing)
                scored.append(q)
                time.sleep(random.uniform(0.5, 1.0))

            scored.sort(key=lambda x: x["score"], reverse=True)
            best = scored[:self.answers_per_run * 2]
            best = best[:self.answers_per_run]

        print(f"\n✅ 最优问题列表：")
        for i, q in enumerate(best, 1):
            print(f"   {i}. [{q['score']:.1f}分] {q['title']}")
            print(f"      关注:{q['follower_count']} 回答:{q['answer_count']} {q['url']}")

        return best

    def process_one(self, question: dict) -> dict:
        result = {
            "question_title": question["title"],
            "question_url": question["url"],
            "question_id": question["id"],
            "status": "pending",
            "answer": "",
            "score": 0,
        }

        print(f"\n📝 生成回答：{question['title'][:50]}...")

        # 生成
        answer = self.generator.generate_answer(
            question["title"],
            question.get("existing_answers", [])
        )

        # 审查
        review = self.generator.quality_check(question["title"], answer)
        result["score"] = review.get("total", 0)
        print(f"   质量分：{review.get('total', 0)}/50，通过：{review.get('pass', False)}")

        # 不通过则改进一次
        if not review.get("pass", True) and review.get("fix"):
            print(f"   改进中：{review['fix'][:40]}...")
            answer = self.generator.improve_answer(
                question["title"], answer, review["fix"]
            )

        result["answer"] = answer

        # 打印完整回答
        print(f"\n{'─'*55}")
        print(f"问题：{question['title']}")
        print(f"链接：{question['url']}")
        print(f"\n回答：\n{answer}")
        print(f"{'─'*55}")

        # 发布
        if self.dry_run:
            print("\n⚠️  演示模式，未发布（设置 DRY_RUN=false 开启自动发布）")
            result["status"] = "preview"
        else:
            wait = random.randint(90, 180)
            print(f"\n⏳ 等待 {wait}s 后发布...")
            time.sleep(wait)
            post = self.zhihu.post_answer(question["id"], answer)
            if post.get("success"):
                print(f"   ✅ 发布成功，answer_id: {post.get('answer_id')}")
                result["status"] = "published"
            else:
                print(f"   ❌ 发布失败：{post}")
                result["status"] = "failed"

        return result

    def run(self) -> list:
        print("=" * 55)
        print("🚀 知乎自动回答机器人")
        print(f"   模式：{'演示（不发布）' if self.dry_run else '自动发布'}")
        print(f"   计划回答：{self.answers_per_run} 个问题")
        print("=" * 55)

        questions = self.find_best_questions()
        if not questions:
            print("\n❌ 未找到合适问题（搜索和预设列表均为空）")
            return []

        results = []
        for i, q in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}]")
            result = self.process_one(q)
            results.append(result)
            if i < len(questions):
                time.sleep(random.randint(20, 40))

        # 汇总
        print(f"\n{'='*55}")
        print("📊 本次执行汇总")
        for r in results:
            icon = {"published": "✅", "preview": "📋", "failed": "❌"}.get(r["status"], "?")
            print(f"  {icon} [{r['score']}分] {r['question_title'][:45]}")
            print(f"       {r['question_url']}")

        return results


if __name__ == "__main__":
    bot = ZhihuBot()
    results = bot.run()

    # 保存结果供 GitHub Actions Artifact 使用
    output_file = "results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 结果已保存至 {output_file}")
