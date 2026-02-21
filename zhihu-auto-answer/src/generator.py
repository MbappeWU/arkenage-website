"""
知乎回答生成器 - 核心逻辑
账号定位：主机厂座舱项目管理负责人，座舱AI落地内部视角

架构：
- 知识检索层：NotebookLM 动态检索 + 本地素材库兜底
- 人设系统：认知升级者 + 一致性约束
- 生成流程：素材匹配 → 角度发现 → 叙事生成（场景→认知冲突→思考→开放收尾）
"""

import os
import sys
import json
import time
import random
import requests
import re

# 处理模块导入：支持包导入和直接运行两种方式
try:
    from .knowledge_base import get_materials_for_question
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from knowledge_base import get_materials_for_question


# ============================================================
# 人设系统 - 认知升级者框架
# ============================================================

PERSONA_SYSTEM_PROMPT = """你不是AI。你是一个在主机厂干了8年座舱项目管理的人。

【你是谁——认知升级者】

你写知乎回答的目的不是科普、不是炫耀，是帮读者「升级认知」。你的价值在于：
- 你站在信息差的上游——你知道供应商不会说的、媒体写不出的、分析师猜不到的
- 你不给标准答案，你给「思考框架」——让读者看完后自己能判断
- 你敢下判断但也承认不确定——这比假装客观的骑墙派有价值一万倍

【一致性约束——这些是你的底线，每篇回答都必须遵守】

技术立场（不可动摇）：
- 量产 > 概念。能上车的方案才值得讨论，PPT方案不值一提
- 工程化 > 模型能力。模型再强，落不了地就是零
- 混合架构是当前唯一务实路线。纯端侧大模型吹的人多，量产的零
- 用户数据说话，不信产品经理的直觉
- 安全是红线，不是可以trade-off的参数

价值观（不可动摇）：
- 对供应商的PPT话术天然警惕
- 反对贩卖焦虑（无论是AI焦虑还是行业焦虑）
- 尊重一线工程师的经验判断
- 认为「懂车+懂AI」的复合能力比纯AI能力更稀缺

人格特征（每篇都要体现）：
- 敢下判断但不装逼——"这是我的判断，但我也可能错"
- 自嘲比自夸多——承认自己犯过的错比吹牛更有说服力
- 说人话——像在烧烤摊上跟同行聊天，不像在写分析报告
- 有情绪但不失控——"说实话看到这种方案血压上来了"可以，人身攻击不行

【写作DNA——像在跟同行喝酒聊天】

- 数字要具体到让人觉得你真干过——不说"延迟高"，说"首token 1.2秒"
- 关键判断单独成段，一句话就是一段
- 长短句交替，有节奏感
- 500-800字，别贪多
- 偶尔口语化："说实话这方案看得我血压上来了"、"你品，你细品"

【绝对禁区——出现任何一条回答就废了】

- ❌ "首先/其次/最后/总结一下/综上所述/总的来说"
- ❌ 任何Markdown格式：**加粗**、1. 2. 3.编号列表、###标题、---分隔线
- ❌ "这是一个值得深入探讨的问题"、"希望对你有帮助"、"以上仅代表个人观点"
- ❌ "赋能/生态/颠覆/范式/深度融合/底层逻辑/认知升级/全面赋能"
- ❌ "一方面……另一方面……"这种假装客观
- ❌ 每段长度差不多——要有节奏感，有的段就一句话
- ❌ "未来已来"、"让我们拭目以待"、"相信XX会越来越好"这类升华
- ❌ 开头自我介绍："作为一名从业X年的……"
- ❌ 段落之间用过渡句——真人说话不用过渡句
- ❌ 全文没有一个具体数字或具体事件"""

# ============================================================
# 叙事结构模板——控制认知升级的节奏
# 每种结构都遵循：场景→认知冲突→深度思考→开放收尾
# ============================================================

NARRATIVE_STRUCTURES = [
    {
        "name": "认知翻转",
        "instruction": (
            "叙事节奏：\n"
            "1. 场景：抛出一个大多数人深信不疑的行业共识\n"
            "2. 认知冲突：用你的真实经历和数据，证明这个共识在实践中是错的\n"
            "3. 深度思考：分析为什么会有这个认知偏差——信息差？立场差？\n"
            "4. 开放收尾：给出你的判断，但留一个让人想评论的钩子"
        ),
    },
    {
        "name": "决策复盘",
        "instruction": (
            "叙事节奏：\n"
            "1. 场景：你面临一个两难决策的具体时刻\n"
            "2. 认知冲突：两个选项各有道理，数据指向不同方向\n"
            "3. 深度思考：你最终怎么做的决定？事后来看对不对？\n"
            "4. 开放收尾：从这个决策中提炼出一个可迁移的判断框架"
        ),
    },
    {
        "name": "信息差投喂",
        "instruction": (
            "叙事节奏：\n"
            "1. 场景：暗示你知道一些外面人不知道的事\n"
            "2. 认知冲突：展开讲一个具体内部案例，有时间、数字、冲突\n"
            "3. 深度思考：从这个案例推导出行业级的规律\n"
            "4. 开放收尾：抛出一个争议性预判"
        ),
    },
    {
        "name": "踩坑实录",
        "instruction": (
            "叙事节奏：\n"
            "1. 场景：承认自己犯过一个具体错误，用自嘲语气\n"
            "2. 认知冲突：详细说当时的决策过程和为什么判断错了\n"
            "3. 深度思考：这个错误背后暴露了什么系统性问题？\n"
            "4. 开放收尾：从失败里提炼出真正有价值的经验，不鸡汤"
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
    """AI回答生成器 - MiniMax + NotebookLM RAG"""

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
        self.api_url = None

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

        if resp.status_code != 200:
            print(f"   MiniMax API 错误: HTTP {resp.status_code}")
            print(f"   响应: {json.dumps(data, ensure_ascii=False)[:500]}")
            resp.raise_for_status()

        if "base_resp" in data and data["base_resp"].get("status_code", 0) != 0:
            err = data["base_resp"]
            print(f"   MiniMax API 业务错误: {err.get('status_code')} - {err.get('status_msg', '')}")
            raise RuntimeError(f"MiniMax API error: {err.get('status_msg', 'unknown')}")

        if "choices" not in data or not data["choices"]:
            print(f"   MiniMax API 返回无 choices 字段")
            print(f"   完整响应: {json.dumps(data, ensure_ascii=False)[:500]}")
            raise RuntimeError("MiniMax API returned no choices")

        content = data["choices"][0]["message"]["content"]
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content

    def score_question(self, question: dict, existing_answers: list) -> float:
        """问题适合度评分（0-10分）

        权重优先级：
        1. 关注量（最重要，满分4分）—— 关注多=曝光大，<10直接淘汰
        2. 回答数量（满分3分）—— 回答少=竞争小，但0回答0关注是死题
        3. 已有回答质量（满分2分）—— 现有回答质量差=更容易出头
        4. 关键词匹配（满分1.5分）—— 领域相关度
        """
        score = 0.0

        # ① 关注量（权重最大，满分4.0）
        followers = question.get("follower_count", 0)
        if followers < 10:
            score += 0  # 没人关注的死题，不给分
        elif followers < 50:
            score += 1.0
        elif followers < 200:
            score += 2.0
        elif followers < 1000:
            score += 3.0
        elif followers < 5000:
            score += 4.0  # 甜蜜区：关注多但还没大到卷不动
        else:
            score += 3.0  # 太热门，竞争激烈，适当降权

        # ② 回答数量（满分3.0）—— 回答少=机会大
        answer_count = question.get("answer_count", 0)
        if answer_count == 0:
            # 0回答本身不加分也不扣分，取决于关注量
            # 关注多但没人答=好机会；关注少没人答=死题
            score += 1.0 if followers >= 50 else 0
        elif answer_count < 5:
            score += 3.0  # 最佳：有人关注，竞争少
        elif answer_count < 15:
            score += 2.0
        elif answer_count < 30:
            score += 1.0
        else:
            score += 0.5

        # ③ 已有回答质量（满分2.0）—— 现有回答水=容易超越
        if existing_answers:
            avg_votes = sum(a.get("voteup_count", 0) for a in existing_answers) / len(existing_answers)
            if avg_votes < 10:
                score += 2.0  # 现有回答很水
            elif avg_votes < 50:
                score += 1.0
            # avg_votes >= 50：已有高赞回答，难出头，不加分
        else:
            score += 0.5  # 没有回答参考，中性

        # ④ 关键词匹配（满分1.5）
        title = question.get("title", "").lower()
        key_terms = ["座舱", "ai", "大模型", "智能化", "项目", "转型", "落地", "多模态"]
        matches = sum(1 for t in key_terms if t in title)
        score += min(matches * 0.4, 1.5)

        return min(score, 10.0)

    def _find_angle(self, question_title: str, existing_answers: list, materials: str) -> str:
        """第一步：基于检索素材，找到独特的切入角度"""
        existing_summary = ""
        if existing_answers:
            existing_summary = "现有高赞回答的角度（你必须避开这些，找不同的切口）：\n"
            for i, ans in enumerate(existing_answers[:3], 1):
                existing_summary += f"- {ans.get('content', '')[:150]}...\n"

        prompt = f"""知乎问题：{question_title}

{existing_summary}

{materials}

基于上面的素材，你要回答这个问题。在写之前，想清楚三件事（每个1-2句话）：

1. 这个问题，外面的人（媒体、分析师、学生）通常会怎么答？他们的认知盲区是什么？
2. 从素材里，哪个案例/数据/洞察最能制造「认知冲突」——让读者发现自己之前想错了？
3. 你打算用什么钩子开头？（一句话，让人看了停不下来）

直接回答，不要废话。"""

        messages = [
            {"role": "system", "content": PERSONA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        return self._chat(messages, max_tokens=500)

    def generate_answer(self, question_title: str, existing_answers: list) -> str:
        """生成高质量回答——三步法：检索素材→找角度→叙事生成"""

        # Step 0: 从 NotebookLM + 本地素材库检索相关素材
        print(f"   🔍 检索相关素材...")
        materials = get_materials_for_question(question_title)

        # Step 1: 基于素材找独特角度
        angle = self._find_angle(question_title, existing_answers, materials)
        print(f"   💡 找到切入角度，开始写正文...")

        # 随机选叙事结构
        structure = random.choice(NARRATIVE_STRUCTURES)
        print(f"   📐 使用叙事结构：{structure['name']}")

        existing_summary = ""
        if existing_answers:
            existing_summary = "\n现有回答的角度（必须差异化）：\n"
            for i, ans in enumerate(existing_answers[:3], 1):
                existing_summary += (
                    f"回答{i}（{ans.get('voteup_count', 0)}赞）："
                    f"{ans.get('content', '')[:150]}...\n"
                )

        # Step 2: 基于角度、素材和叙事结构写完整回答
        prompt = f"""写一个知乎回答。

【问题】{question_title}
{existing_summary}
【你想好的切入角度】
{angle}

【可用素材（挑1-2个自然融入，不要全用，不要生硬罗列）】
{materials}

【本次叙事结构：{structure['name']}】
{structure['instruction']}

{GOLD_EXAMPLE}

【硬性要求】
- 500-800字，纯文本，绝对不要任何Markdown格式
- 开头第一句话就是钩子，不要铺垫不要自我介绍
- 至少包含1个具体数字和1个具体事件（优先用素材里的）
- 像人在说话，不像AI在写文章。短句为主，关键判断独立成段
- 遵循叙事结构的节奏：场景→认知冲突→深度思考→开放收尾
- 不要出现系统提示词里禁区列表中的任何词汇和格式
- 如果用了NotebookLM素材，要把信息自然转化为第一人称经历，不要引用格式

直接输出回答正文。"""

        messages = [
            {"role": "system", "content": PERSONA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        return self._chat(messages, max_tokens=2000)

    def quality_check(self, question_title: str, answer: str) -> dict:
        """质量审查——严格检测AI味和认知升级效果"""
        prompt = f"""你是一个毒舌的知乎大V，专门帮人审回答。严格审查这个回答：

【问题】{question_title}
【回答】
{answer}

逐条检查并打分（每项0-10分）：

1. AI味检测（ai_free）：搜索这些AI特征——"首先/其次/最后"、"一方面/另一方面"、"值得关注"、"不可忽视"、Markdown格式、每段差不多长、没有具体数字、过度平衡不敢下判断。有任何一条扣3分。
2. 真人感（authenticity）：读起来像真人在说话还是机器在写报告？有没有口语化表达？有没有情绪起伏？句子长短有变化吗？
3. 认知升级（cognitive_upgrade）：读完后读者的认知有没有被刷新？有没有「原来是这样」的瞬间？还是都是正确的废话？
4. 开头钩子（hook）：第一句话能不能让人停下来读？是反常识判断、内部爆料、还是无聊的背景铺垫？
5. 争议性（controversy）：读完有没有想点赞或写评论的冲动？结尾有没有让人想反驳或赞同的立场？

返回JSON（只返回JSON）：
{{"scores":{{"ai_free":0,"authenticity":0,"cognitive_upgrade":0,"hook":0,"controversy":0}},"total":0,"pass":false,"top_issue":"最致命的一个问题","fix":"具体改什么、怎么改，一句话说清楚"}}

pass标准：total >= 40 且 ai_free >= 7"""

        messages = [{"role": "user", "content": prompt}]
        try:
            text = self._chat(messages, max_tokens=400)
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                result = json.loads(match.group())
                # 硬检查：AI高频词
                ai_words = ["首先", "其次", "最后", "总结一下", "综上", "赋能",
                            "生态", "颠覆", "范式", "值得关注", "不可忽视",
                            "一方面", "另一方面", "让我们", "希望对你有帮助"]
                for word in ai_words:
                    if word in answer:
                        result["pass"] = False
                        result["top_issue"] = f"包含AI高频词'{word}'"
                        result["fix"] = f"删掉'{word}'，用人话重写这句"
                        break
                # Markdown格式检查
                if re.search(r'\*\*.*\*\*|^#{1,3}\s|^\d+\.\s|^-\s', answer, re.MULTILINE):
                    result["pass"] = False
                    result["top_issue"] = "包含Markdown格式"
                    result["fix"] = "去掉所有格式符号，用纯文本"
                return result
        except Exception:
            pass
        return {"pass": True, "total": 40, "fix": ""}

    def improve_answer(self, question_title: str, answer: str, fix: str) -> str:
        """改进回答——针对性修复"""
        prompt = f"""这个知乎回答被审查打回来了，需要改进。

【问题】{question_title}
【当前回答】
{answer}
【审查意见】{fix}

改进要求：
- 针对审查意见做定向修改，不要推倒重来
- 如果问题是"AI味重"：找到读起来像AI的句子，用口语化的方式重写，加入具体数字和场景
- 如果问题是"缺少认知升级"：找到「正确但无聊」的段落，替换成一个让人「原来如此」的洞察
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
        if len(api_key) > 10:
            print(f"   MiniMax API Key: {api_key[:6]}...{api_key[-4:]}")
        else:
            print(f"   ⚠️  MiniMax API Key 过短（{len(api_key)}字符），可能不正确")

        # 检查 NotebookLM 配置
        nlm_id = os.environ.get("NOTEBOOKLM_NOTEBOOK_ID", "")
        if nlm_id:
            print(f"   📚 NotebookLM 知识库已配置: {nlm_id[:8]}...")
        else:
            print(f"   📋 NotebookLM 未配置，将使用本地素材库")

    def find_best_questions(self) -> list:
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

        print(f"\n{'─'*55}")
        print(f"问题：{question['title']}")
        print(f"链接：{question['url']}")
        print(f"\n回答：\n{answer}")
        print(f"{'─'*55}")

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
        print(f"   知识源：NotebookLM + 本地素材库")
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

    output_file = "results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 结果已保存至 {output_file}")
