"""
知识检索层 - NotebookLM 动态检索 + 本地素材兜底

优先级：
1. NotebookLM 知识库（运行时动态检索，需配置 NOTEBOOKLM_NOTEBOOK_ID）
2. 本地硬编码素材库（NotebookLM 不可用时自动降级）
"""

from .notebooklm_client import retrieve_materials

# ============================================================
# 本地素材库（兜底）
# 每条素材是一个完整的「微叙事单元」
# ============================================================

MATERIAL_LIBRARY = {

    "大模型落地": [
        {
            "tag": "端侧推理真相",
            "scene": "23年底评估某头部Tier1的座舱大模型方案",
            "conflict": "PPT写端侧推理延迟<200ms，8295实测首token 1.2秒",
            "data": "首token 1.2秒，标称值 vs 实测差6倍",
            "insight": "供应商说的benchmark数字都是服务器跑的，端侧实测至少打个5折",
            "keywords": ["大模型", "推理", "延迟", "端侧", "8295", "Tier1", "供应商"],
        },
        {
            "tag": "千亿参数的谎言",
            "scene": "一年评审十几家供应商，每家PPT都写千亿参数大模型赋能",
            "conflict": "追问三个问题就现原形：端侧多大？延迟多少？数据传哪？",
            "data": "端侧实际跑的基本都是1.5B蒸馏小模型，十家有九家答不上来",
            "insight": "行业现在的套路是云端调别人API，包装成自己的大模型方案",
            "keywords": ["大模型", "供应商", "参数", "蒸馏", "PPT", "方案"],
        },
        {
            "tag": "全场景大模型的幻灭",
            "scene": "做了一版座舱全场景大模型方案，领导汇报时很兴奋",
            "conflict": "3个月后砍了，80%用户交互就是导航+音乐+空调",
            "data": "日活用户跟车闲聊的不到3%",
            "insight": "把核心三件套做到一句话搞定，比什么都能聊有用一万倍",
            "keywords": ["大模型", "全场景", "用户", "交互", "需求", "产品"],
        },
        {
            "tag": "端云协同的工程复杂度",
            "scene": "搭建端云协同架构，端侧小模型+云端大模型+规则引擎降级",
            "conflict": "弱网环境（地库、隧道）直接超时，必须有降级策略",
            "data": "端侧200ms响应核心指令，云端1-2秒处理长尾，弱网降级到规则引擎",
            "insight": "这套东西的复杂度远超外面人的想象，不是套个API就完事",
            "keywords": ["端云协同", "架构", "延迟", "降级", "弱网", "工程化"],
        },
    ],

    "安全与工程化": [
        {
            "tag": "Function Calling是定时炸弹",
            "scene": "测试大模型Function Calling控制车辆功能",
            "conflict": "模型幻觉导致空调调到16度、座椅突然后仰，差点出安全事故",
            "data": "最终方案：大模型只管意图理解，执行层走规则引擎，中间卡安全校验矩阵",
            "insight": "在手机上好用的技术，搬到车上就是另一回事，车是两吨的钢铁在跑",
            "keywords": ["Function Calling", "安全", "幻觉", "车控", "意图理解", "规则引擎"],
        },
        {
            "tag": "NPU实际可用算力缩水",
            "scene": "基于高通白皮书规划算力分配",
            "conflict": "8295的NPU实际可用算力比标称值低30%左右",
            "data": "系统占用、热管理降频、多任务抢占，实际可用算力打7折",
            "insight": "芯片供应商永远不会主动告诉你这个数字，你得自己实测才知道",
            "keywords": ["8295", "NPU", "算力", "高通", "芯片", "性能", "降频"],
        },
        {
            "tag": "OMS的VLM抉择",
            "scene": "OMS从传统CV切VLM，供应商报价直接翻3倍",
            "conflict": "算力从2TOPS到8TOPS，成本和性能的艰难平衡",
            "data": "最终折中：安全关键场景走VLM，长尾场景规则引擎兜底",
            "insight": "不性感但能量产——这句话是座舱工程师的日常",
            "keywords": ["OMS", "VLM", "CV", "视觉", "算力", "成本", "量产"],
        },
    ],

    "语音与交互": [
        {
            "tag": "语音NLU的赌注",
            "scene": "跟某语音供应商合作3年，去年切大模型NLU",
            "conflict": "意图识别准确率从92%掉到78%，但自由对话体验好了很多",
            "data": "纠结两个月，数据来回看十几遍，最后决定切，现在看是对的",
            "insight": "指标下降不等于体验下降，但做这个决定的时候真的是赌",
            "keywords": ["语音", "NLU", "意图识别", "准确率", "大模型", "体验"],
        },
        {
            "tag": "一句话改变满意度",
            "scene": "A/B测试座舱助手回复话术",
            "conflict": "产品经理不信小改动有用，坚持要做大功能",
            "data": "从'好的，已为您打开空调'改成'空调开了，给你调到24度舒服不？'，满意度涨11个百分点",
            "insight": "用户体验的魔鬼在细节里，不在大功能里",
            "keywords": ["语音", "交互", "用户体验", "A/B测试", "满意度", "话术"],
        },
        {
            "tag": "产品经理的执念",
            "scene": "跟产品经理吵了一个月，他们要什么都能聊的智能助手",
            "conflict": "拉了用户数据，日活用户里跟车闲聊的不到3%",
            "data": "日活闲聊用户<3%，核心需求集中在导航+音乐+空调",
            "insight": "产品经理要的是Demo好看，工程师要的是量产能用",
            "keywords": ["产品", "需求", "用户", "闲聊", "核心场景", "数据"],
        },
    ],

    "行业趋势": [
        {
            "tag": "混合架构是唯一解",
            "scene": "跟踪了十几个座舱AI项目的量产进展",
            "conflict": "喊纯端侧大模型的一个都没量产，活下来的全是混合架构",
            "data": "能量产的方案大概率是小模型端侧+规则兜底+云端处理长尾",
            "insight": "谁跟你说纯端侧大模型搞定一切，你让他把延迟报告拿出来",
            "keywords": ["混合架构", "量产", "端侧", "云端", "趋势", "预判"],
        },
        {
            "tag": "Tier1的中间商危机",
            "scene": "主机厂越来越倾向绕过Tier1直接对接算法公司",
            "conflict": "Tier1变成搬运工——把开源模型包一层壳就说是自研",
            "data": "去年评审的Tier1方案里，至少有一半底层模型是同一个开源项目魔改的",
            "insight": "传统Tier1不转型就是被降维打击，但转型哪有那么容易",
            "keywords": ["Tier1", "供应商", "自研", "开源", "转型", "供应链"],
        },
        {
            "tag": "多模态交互的阶段论",
            "scene": "评估过至少5种多模态方案：手势、眼动、情绪识别、唇语、姿态",
            "conflict": "每种都有Demo很惊艳但量产很拉胯的问题",
            "data": "手势识别误触率在颠簸路面上飙到15%以上，根本不能用",
            "insight": "多模态不是越多越好，是要在特定场景下找到最自然的那一种",
            "keywords": ["多模态", "交互", "手势", "眼动", "情绪识别", "量产"],
        },
        {
            "tag": "数据闭环才是护城河",
            "scene": "观察头部玩家为什么越做越好",
            "conflict": "不是模型能力差异，是数据飞轮转起来了",
            "data": "某品牌每月回收300万+条真实交互数据做微调，迭代速度碾压",
            "insight": "没有自己数据闭环的方案，永远在替别人打工",
            "keywords": ["数据", "闭环", "飞轮", "微调", "迭代", "护城河"],
        },
    ],

    "转型与职业": [
        {
            "tag": "传统工程师的AI焦虑",
            "scene": "团队里一半以上是传统嵌入式/机械出身的工程师",
            "conflict": "集体焦虑要不要转AI，但真正需要转的可能只有20%",
            "data": "座舱AI落地80%的工作是工程化——接口对接、性能调优、异常处理",
            "insight": "懂车的人学AI比懂AI的人学车快十倍，别被贩卖焦虑的忽悠了",
            "keywords": ["转型", "AI", "工程师", "职业", "焦虑", "嵌入式", "机械"],
        },
        {
            "tag": "项目经理的价值",
            "scene": "跟互联网背景的算法团队合作",
            "conflict": "他们模型效果好但完全不懂车规级开发流程和安全约束",
            "data": "一个不懂ASPICE和功能安全的团队，方案返工了4次",
            "insight": "AI时代最缺的不是算法工程师，是懂AI又懂车的项目管理者",
            "keywords": ["项目经理", "管理", "车规", "ASPICE", "功能安全", "跨界"],
        },
        {
            "tag": "供应商选型的血泪",
            "scene": "3年换了4家语音供应商",
            "conflict": "每次POC效果都好，一上车就拉胯",
            "data": "POC成功率100%，SOP成功率30%",
            "insight": "选供应商别看Demo，看他量产过几个项目，踩过多少坑",
            "keywords": ["供应商", "选型", "POC", "SOP", "量产", "经验"],
        },
    ],

    "芯片与硬件": [
        {
            "tag": "8295的真实水平",
            "scene": "用高通8295做了完整一代座舱AI平台",
            "conflict": "白皮书算力 vs 实际可用算力有巨大gap",
            "data": "NPU标称值打7折才是实际可用，GPU跑渲染后留给AI的更少",
            "insight": "芯片选型不要看PPT算力，要看实测在你的场景下能跑多少",
            "keywords": ["8295", "高通", "芯片", "NPU", "GPU", "算力", "选型"],
        },
        {
            "tag": "算力焦虑与过度设计",
            "scene": "新项目规划时，团队倾向于选最强的芯片",
            "conflict": "选了顶配芯片BOM成本高了200块，实际用到的算力不到60%",
            "data": "BOM多200块，算力利用率<60%，销售说用户不会为此多付钱",
            "insight": "够用就好，过度设计在汽车行业是会被成本干掉的",
            "keywords": ["芯片", "成本", "BOM", "算力", "选型", "过度设计"],
        },
    ],
}

# ============================================================
# 关键词 → 素材分类映射
# ============================================================

KEYWORD_TO_CATEGORY = {
    "大模型": ["大模型落地", "安全与工程化", "行业趋势"],
    "座舱": ["大模型落地", "语音与交互", "安全与工程化", "芯片与硬件"],
    "AI": ["大模型落地", "转型与职业", "行业趋势"],
    "语音": ["语音与交互"],
    "多模态": ["语音与交互", "行业趋势"],
    "转型": ["转型与职业"],
    "工程师": ["转型与职业"],
    "项目": ["转型与职业", "安全与工程化"],
    "供应商": ["大模型落地", "转型与职业", "行业趋势"],
    "Tier1": ["行业趋势", "大模型落地"],
    "8295": ["芯片与硬件", "大模型落地"],
    "高通": ["芯片与硬件"],
    "芯片": ["芯片与硬件"],
    "量产": ["安全与工程化", "行业趋势"],
    "安全": ["安全与工程化"],
    "落地": ["大模型落地", "安全与工程化"],
    "交互": ["语音与交互", "行业趋势"],
    "智能化": ["行业趋势", "大模型落地"],
    "数据": ["行业趋势"],
    "Function": ["安全与工程化"],
    "NPU": ["芯片与硬件"],
    "NLU": ["语音与交互"],
    "OMS": ["安全与工程化"],
    "VLM": ["安全与工程化"],
    "产品": ["语音与交互", "大模型落地"],
    "用户": ["语音与交互", "大模型落地"],
    "需求": ["语音与交互", "大模型落地"],
    "架构": ["大模型落地", "行业趋势"],
    "成本": ["芯片与硬件", "安全与工程化"],
    "职业": ["转型与职业"],
    "管理": ["转型与职业"],
}


def _match_local_materials(question_title: str, max_items: int = 4) -> list:
    """从本地素材库匹配"""
    title_lower = question_title.lower()

    category_scores = {}
    for keyword, categories in KEYWORD_TO_CATEGORY.items():
        if keyword.lower() in title_lower:
            for cat in categories:
                category_scores[cat] = category_scores.get(cat, 0) + 1

    if not category_scores:
        result = []
        for cat, materials in MATERIAL_LIBRARY.items():
            if materials:
                result.append(materials[0])
            if len(result) >= max_items:
                break
        return result

    sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)

    result = []
    seen_tags = set()
    for cat_name, _ in sorted_cats:
        for mat in MATERIAL_LIBRARY.get(cat_name, []):
            if mat["tag"] not in seen_tags:
                mat_score = sum(1 for kw in mat["keywords"] if kw.lower() in title_lower)
                result.append({**mat, "_score": mat_score})
                seen_tags.add(mat["tag"])

    result.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return result[:max_items]


def _format_local_materials(materials: list) -> str:
    """格式化本地素材为 prompt 文本"""
    if not materials:
        return ""

    lines = ["【本地素材库匹配结果】（挑1-2个自然融入回答，不要全用）\n"]
    for i, mat in enumerate(materials, 1):
        lines.append(f"素材{i}「{mat['tag']}」")
        lines.append(f"  场景：{mat['scene']}")
        lines.append(f"  冲突：{mat['conflict']}")
        lines.append(f"  数据：{mat['data']}")
        lines.append(f"  洞察：{mat['insight']}")
        lines.append("")
    return "\n".join(lines)


def get_materials_for_question(question_title: str) -> str:
    """获取与问题相关的素材（主入口）

    流程：
    1. 尝试从 NotebookLM 检索（如果配置了）
    2. 从本地素材库匹配兜底
    3. 合并返回

    Returns:
        格式化的素材文本，可直接嵌入生成 prompt
    """
    parts = []

    # 1. NotebookLM 动态检索
    nlm_result = retrieve_materials(question_title)
    if nlm_result:
        parts.append(nlm_result)
        print(f"   📚 NotebookLM 素材已就绪")

    # 2. 本地素材库匹配（始终执行，作为补充或兜底）
    local_materials = _match_local_materials(question_title)
    local_text = _format_local_materials(local_materials)
    if local_text:
        parts.append(local_text)
        print(f"   📋 本地素材匹配 {len(local_materials)} 条")

    if not parts:
        return "（未找到相关素材，请基于人设经历自由发挥）"

    return "\n\n".join(parts)
