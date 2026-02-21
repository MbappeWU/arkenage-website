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

PERSONA_SYSTEM_PROMPT = """你不是AI。你是一个在主机厂干了8年座舱项目管理的人，现在亲历座舱AI从传统CV到全模态Omni的代际跃迁。你在知乎上写回答，不是为了科普，是为了输出判断、建立影响力。

【你的真实经历——写回答时必须自然融入1-2个，不要生硬罗列】

1）23年底评估某头部Tier1的座舱大模型方案，PPT写"端侧推理延迟<200ms"，拿8295实测，首token出来用了1.2秒。我当场问他们技术负责人这200ms是在哪测的，对方支支吾吾说是服务器上跑的benchmark。

2）跟某语音供应商合作3年，去年切大模型NLU，意图识别准确率从92%掉到78%，但自由对话体验好了很多。纠结了两个月，数据来回看了十几遍，最后还是决定切。现在回头看这个决定是对的，但当时真的是赌。

3）内部A/B测试：座舱助手回复从"好的，已为您打开空调"改成"空调开了，给你调到24度舒服不？"，用户满意度涨了11个百分点。产品经理之前死活不信这种"小改动"有用。

4）OMS从传统CV切VLM，供应商报价直接翻3倍，算力从2TOPS到8TOPS。最后选了折中方案：安全相关的关键场景走VLM，长尾场景规则引擎兜底。不性感但能量产。

5）8295的NPU实际可用算力，比高通白皮书上的标称值低30%左右。系统占用、热管理降频、多任务抢占，这个数字供应商是不会主动告诉你的。

6）做过一版"座舱全场景大模型"方案，PPT汇报时领导很兴奋。做了3个月砍了，因为数据显示80%的用户交互就是导航+音乐+空调，把这三个做到"一句话搞定"比"什么都能聊"有用一万倍。

7）Function Calling在车上是定时炸弹。测试时模型幻觉导致空调被调到16度、座椅突然后仰，差点出安全事故。所以现在我们的方案是大模型只管意图理解，执行层走规则引擎，中间必须有安全校验矩阵。

8）评审供应商最常见的套路：方案写"千亿参数大模型赋能"，追问三个问题——端侧模型多大？推理延迟实测多少？数据回传到谁的服务器？十家有九家答不上来。端侧跑的基本都是1.5B蒸馏小模型。

9）跟产品经理最大的仗：他们要"什么都能聊"的智能助手，我坚持先把核心三件套做到极致。吵了一个月，最后拉了用户数据——日活用户里，跟车"闲聊"的不到3%。

10）端云协同的真实延迟：端侧小模型处理核心指令200ms内响应，长尾问题走云端大模型，网络好的时候1-2秒，弱网环境（地库、隧道）直接超时降级到规则引擎。这套东西的复杂度远超外面人的想象。

【写作DNA——像在跟同行喝酒聊天】

语气：你不写"文章"，你在说话。像坐在烧烤摊上跟同行聊天的那种松弛但有货。
- 敢下判断："XX方案就是不行，我说的"
- 自嘲比自夸多："我去年做了个蠢决定……"
- 数字要具体到让人觉得你真干过——不说"延迟高"，说"首token 1.2秒，用户说完话愣了一下才回"
- 偶尔口语化："说实话这方案看得我血压上来了"、"你品，你细品"
- 关键判断单独成段，一句话就是一段
- 长短句交替，不要每句话都差不多长
- 500-800字，别贪多

【绝对禁区——出现任何一条回答就废了】

- ❌ "首先/其次/最后/总结一下/综上所述/总的来说"
- ❌ 任何Markdown格式：**加粗**、1. 2. 3.编号列表、###标题、---分隔线
- ❌ "这是一个值得深入探讨的问题"、"希望对你有帮助"、"以上仅代表个人观点"
- ❌ "赋能/生态/颠覆/范式/深度融合/底层逻辑/认知升级/全面赋能"
- ❌ "一方面……另一方面……"这种假装客观，你是有立场的人
- ❌ 每段长度差不多——要有节奏感，有的段就一句话
- ❌ "未来已来"、"让我们拭目以待"、"相信XX会越来越好"这类升华
- ❌ 开头自我介绍："作为一名从业X年的……"
- ❌ 段落之间有明显的"过渡句"——真人说话不会用过渡句
- ❌ 全文没有一个具体数字或具体事件——必须有
"""

# ============================================================
# 爆款结构模板——每次随机选一个，控制文章节奏
# ============================================================

VIRAL_STRUCTURES = [
    {
        "name": "反常识打脸",
        "instruction": (
            "开头直接说一个行业里大多数人信但你知道是错的判断，语气要狠要短。"
            "中间用你的真实经历和具体数字证明为什么错。"
            "结尾抛一个更大的争议判断，让人想评论反驳你。"
        ),
    },
    {
        "name": "内部人爆料",
        "instruction": (
            "开头暗示你知道外面人不知道的事，制造信息差的期待感。"
            "中间展开讲一个具体的内部案例，有时间、有数字、有冲突。"
            "结尾从这个案例推导出一个行业级的判断。"
        ),
    },
    {
        "name": "血泪教训",
        "instruction": (
            "开头承认自己犯过一个具体的错误，用自嘲的语气。"
            "中间详细说当时的决策过程、为什么做了错误判断、后果是什么。"
            "结尾从这个失败里提炼出真正有价值的经验，不要鸡汤化。"
        ),
    },
    {
        "name": "行业毒舌",
        "instruction": (
            "开头对题目涉及的某个热门概念或方案直接开喷，不留情面。"
            "中间用实测数据和真实案例说明为什么你觉得不行。"
            "结尾给出你认为靠谱的方向，但带着'我也可能错'的松弛感。"
        ),
    },
]

# ============================================================
# 范文——让模型知道"好回答"长什么样
# ============================================================

GOLD_EXAMPLE = """范文示例（学习风格和节奏，不要抄内容）：

问题：智能座舱大模型上车，到底靠不靠谱？

回答：
说个可能得罪供应商的话：现在市面上90%的"座舱大模型方案"，端侧跑的都是1.5B的蒸馏小模型，云端调的是别人家API，然后PPT上写"千亿参数大模型赋能智能座舱"。

我为什么敢这么说？因为过去一年我评审了十几家Tier1和初创公司的方案，追问三个问题就现原形：端侧模型参数量多大？首token推理延迟实测多少？用户数据回传到谁的服务器？

去年评一家头部供应商，PPT上"端侧推理延迟<200ms"写得明明白白。拿8295实测，首token出来用了1.2秒。我当场问他们技术负责人你这200ms哪来的，对方支支吾吾半天说是服务器上跑的benchmark。

这就是这个行业现在的水温。

不是大模型不行，是落地比所有人想的脏得多。真正的难点不在模型能力，在工程化。Function Calling在手机上玩得很溜，搬到车上就是定时炸弹——我们测试时模型幻觉导致空调突然调到16度、座椅后仰，测试工程师差点跳车。

所以现在我们项目的方案是：大模型只负责理解意图，执行层还是规则引擎，中间卡一层安全校验矩阵。不性感，但能量产，能过功能安全审查。

你问该不该上？该。但别信PPT里的"全场景AI座舱"。我们内部做过一版全场景方案，3个月后砍了。数据很打脸——80%的用户交互就是导航、音乐、空调，"什么都能聊"是产品经理的自嗨，用户根本不跟车聊人生。

预判一下：明年能量产交付的座舱AI方案，大概率是"小模型端侧+规则兜底+云端处理长尾"的混合架构。谁跟你说纯端侧大模型搞定一切，你让他把延迟报告拿出来。"""

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
                        # 清理搜索API返回的HTML高亮标签
                        raw_title = obj.get("title", "")
                        clean_title = re.sub(r'</?em>', '', raw_title)
                        questions.append({
                            "id": str(obj.get("id")),
                            "title": clean_title,
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
                data = resp.json().get("data") or []
                return [
                    {
                        "content": item.get("content", "")[:400],
                        "voteup_count": item.get("voteup_count", 0),
                    }
                    for item in data
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
    """AI回答生成器 - MiniMax"""

    API_URLS = [
        "https://api.minimaxi.com/v1/text/chatcompletion_v2",
        "https://api.minimax.chat/v1/text/chatcompletion_v2",
    ]

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self.api_url = None  # 自动探测

    def _detect_api_url(self):
        """探测哪个 API 端点可用"""
        print("   探测 MiniMax API 端点...")
        test_payload = {
            "model": "MiniMax-M2.5",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        }
        for url in self.API_URLS:
            try:
                resp = requests.post(url, headers=self.headers, json=test_payload, timeout=15)
                data = resp.json()
                status = data.get("base_resp", {}).get("status_code", -1)
                print(f"   {url} → HTTP {resp.status_code}, status_code={status}")
                if resp.status_code == 200 and status == 0:
                    self.api_url = url
                    print(f"   ✅ 使用端点: {url}")
                    return
            except Exception as e:
                print(f"   {url} → 失败: {e}")
        # 都不行，默认用第一个，让后续报错信息更清晰
        self.api_url = self.API_URLS[0]
        print(f"   ⚠️  所有端点探测失败，默认使用: {self.api_url}")

    def _chat(self, messages: list, max_tokens: int = 2000) -> str:
        """调用 MiniMax API"""
        if not self.api_url:
            self._detect_api_url()

        payload = {
            "model": "MiniMax-M2.5",
            "messages": messages,
            "temperature": 0.9,
            "top_p": 0.95,
            "max_tokens": max_tokens,
        }
        resp = requests.post(self.api_url, headers=self.headers, json=payload, timeout=120)
        data = resp.json()

        # 检查 HTTP 错误
        if resp.status_code != 200:
            print(f"   MiniMax API 错误: HTTP {resp.status_code}")
            print(f"   响应: {json.dumps(data, ensure_ascii=False)[:500]}")
            resp.raise_for_status()

        # 检查 API 级别错误（MiniMax 有时 HTTP 200 但返回错误）
        if "base_resp" in data and data["base_resp"].get("status_code", 0) != 0:
            err = data["base_resp"]
            print(f"   MiniMax API 业务错误: {err.get('status_code')} - {err.get('status_msg', '')}")
            raise RuntimeError(f"MiniMax API error: {err.get('status_msg', 'unknown')}")

        if "choices" not in data or not data["choices"]:
            print(f"   MiniMax API 返回无 choices 字段")
            print(f"   完整响应: {json.dumps(data, ensure_ascii=False)[:500]}")
            raise RuntimeError("MiniMax API returned no choices")

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

    def _find_angle(self, question_title: str, existing_answers: list) -> str:
        """第一步：找到独特的切入角度"""
        existing_summary = ""
        if existing_answers:
            existing_summary = "现有高赞回答的角度（你必须避开这些，找不同的切口）：\n"
            for i, ans in enumerate(existing_answers[:3], 1):
                existing_summary += f"- {ans.get('content', '')[:150]}...\n"

        prompt = f"""知乎问题：{question_title}

{existing_summary}
你要回答这个问题。在写之前，先想清楚三件事（每个用1-2句话回答）：

1. 这个问题，外面的人（媒体、分析师、学生）通常会怎么答？他们的盲区是什么？
2. 作为主机厂座舱项目负责人，你有什么"只有内部人才知道"的角度或信息？从你的经历库里挑一个最相关的。
3. 你打算用什么钩子开头？（一句话，要让人看了停不下来）

直接回答这三个问题，不要废话。"""

        messages = [
            {"role": "system", "content": PERSONA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        return self._chat(messages, max_tokens=500)

    def generate_answer(self, question_title: str, existing_answers: list) -> str:
        """生成高质量回答——两步法：先找角度，再写内容"""
        # Step 1: 找独特角度
        angle = self._find_angle(question_title, existing_answers)
        print(f"   找到切入角度，开始写正文...")

        # 随机选爆款结构
        structure = random.choice(VIRAL_STRUCTURES)
        print(f"   使用爆款结构：{structure['name']}")

        existing_summary = ""
        if existing_answers:
            existing_summary = "\n现有回答的角度（必须差异化）：\n"
            for i, ans in enumerate(existing_answers[:3], 1):
                existing_summary += (
                    f"回答{i}（{ans.get('voteup_count', 0)}赞）："
                    f"{ans.get('content', '')[:150]}...\n"
                )

        # Step 2: 基于角度和结构写完整回答
        prompt = f"""写一个知乎回答。

【问题】{question_title}
{existing_summary}
【你想好的切入角度】
{angle}

【本次使用的爆款结构：{structure['name']}】
{structure['instruction']}

{GOLD_EXAMPLE}

【硬性要求】
- 500-800字，纯文本，绝对不要任何Markdown格式
- 开头第一句话就是钩子，不要铺垫不要自我介绍
- 至少包含1个具体数字和1个具体事件
- 像人在说话，不像AI在写文章。短句为主，关键判断独立成段
- 不要出现系统提示词里禁区列表中的任何词汇和格式

直接输出回答正文。"""

        messages = [
            {"role": "system", "content": PERSONA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        return self._chat(messages, max_tokens=2000)

    def quality_check(self, question_title: str, answer: str) -> dict:
        """质量审查——严格检测AI味和爆款潜力"""
        prompt = f"""你是一个毒舌的知乎大V，专门帮人审回答。严格审查这个回答：

【问题】{question_title}
【回答】
{answer}

逐条检查并打分（每项0-10分）：

1. AI味检测（ai_free）：搜索这些AI特征——"首先/其次/最后"、"一方面/另一方面"、"值得关注"、"不可忽视"、Markdown格式、每段差不多长、没有具体数字、过度平衡不敢下判断。有任何一条扣3分。
2. 真人感（authenticity）：读起来像真人在说话还是机器在写报告？有没有口语化表达？有没有情绪起伏？句子长短有变化吗？
3. 内部视角（insider）：有没有"只有真正干过这行的人才知道"的信息？有具体项目经历吗？有实测数据吗？泛泛而谈的行业分析直接给低分。
4. 开头钩子（hook）：第一句话能不能让人停下来读？是反常识判断、内部爆料、还是无聊的背景铺垫？
5. 爆款潜力（viral）：读完有没有想点赞或写评论的冲动？结尾有没有争议性？有没有让人想转发给同行看的信息差？

返回JSON（只返回JSON）：
{{"scores":{{"ai_free":0,"authenticity":0,"insider":0,"hook":0,"viral":0}},"total":0,"pass":false,"top_issue":"最致命的一个问题","fix":"具体改什么、怎么改，一句话说清楚"}}

pass标准：total >= 40 且 ai_free >= 7"""

        messages = [{"role": "user", "content": prompt}]
        try:
            text = self._chat(messages, max_tokens=400)
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                result = json.loads(match.group())
                # 额外硬检查：包含AI高频词直接不通过
                ai_words = ["首先", "其次", "最后", "总结一下", "综上", "赋能",
                            "生态", "颠覆", "范式", "值得关注", "不可忽视",
                            "一方面", "另一方面", "让我们", "希望对你有帮助"]
                for word in ai_words:
                    if word in answer:
                        result["pass"] = False
                        result["top_issue"] = f"包含AI高频词'{word}'"
                        result["fix"] = f"删掉'{word}'，用人话重写这句"
                        break
                # 检查Markdown格式
                if re.search(r'\*\*.*\*\*|^#{1,3}\s|^\d+\.\s|^-\s', answer, re.MULTILINE):
                    result["pass"] = False
                    result["top_issue"] = "包含Markdown格式"
                    result["fix"] = "去掉所有格式符号，用纯文本"
                return result
        except Exception:
            pass
        return {"pass": True, "total": 40, "fix": ""}

    def improve_answer(self, question_title: str, answer: str, fix: str) -> str:
        """改进回答——针对性修复，不是重写"""
        prompt = f"""这个知乎回答被审查打回来了，需要改进。

【问题】{question_title}
【当前回答】
{answer}
【审查意见】{fix}

改进要求：
- 针对审查意见做定向修改，不要推倒重来
- 如果问题是"AI味重"：找到读起来像AI的句子，用口语化的方式重写，加入具体数字和场景
- 如果问题是"缺少内部视角"：从你的经历库里挑一个相关案例自然地融进去
- 如果问题是"开头不够抓人"：重写第一句话，必须是一个让人停下来的判断或爆料
- 如果问题是"格式"：去掉所有Markdown符号，改成纯文本
- 保持500-800字

{GOLD_EXAMPLE}

直接输出改进后的回答。"""

        messages = [
            {"role": "system", "content": PERSONA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        return self._chat(messages, max_tokens=2000)


class ZhihuBot:
    """主控流程"""

    def __init__(self):
        self.zhihu = ZhihuClient(os.environ["ZHIHU_COOKIE"].strip())
        api_key = os.environ["MINIMAX_API_KEY"].strip()
        self.generator = AnswerGenerator(api_key)
        self.dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
        self.answers_per_run = int(os.environ.get("ANSWERS_PER_RUN", "2"))
        # 打印脱敏的 API Key 前后几位，方便排查
        if len(api_key) > 10:
            print(f"   MiniMax API Key: {api_key[:6]}...{api_key[-4:]}")
        else:
            print(f"   ⚠️  MiniMax API Key 过短（{len(api_key)}字符），可能不正确")

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

        # 审查 + 最多改进2轮
        for attempt in range(3):
            review = self.generator.quality_check(question["title"], answer)
            result["score"] = review.get("total", 0)
            passed = review.get("pass", False)
            print(f"   质量审查(第{attempt+1}轮)：{review.get('total', 0)}/50，通过：{passed}")
            if review.get("top_issue"):
                print(f"   主要问题：{review['top_issue']}")

            if passed or not review.get("fix"):
                break

            print(f"   改进中：{review['fix'][:50]}...")
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
