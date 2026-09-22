"""Build and validate the pre-registered 40-case Week 3 RAG dataset."""

# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .rag_schemas import validate_rag_dataset

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "insight_agent/evaluation/dataset/rag_test.json"


def src(document: str, section: str) -> dict[str, str]:
    return {"document": document, "section": section}


def fact(name: str, *accepted_values: str) -> dict[str, Any]:
    return {"name": name, "accepted_values": list(accepted_values)}


def case(
    case_id: str,
    split: str,
    case_type: str,
    question: str,
    sources: list[dict[str, str]],
    facts: list[dict[str, Any]],
    *,
    unacceptable: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": case_id,
        "split": split,
        "case_type": case_type,
        "question": question,
        "gold_sources": sources,
        "expected_facts": facts,
        "unacceptable_conclusions": unacceptable or [],
        "should_answer": case_type != "no_answer",
        "tags": tags or [],
    }


def build_dataset() -> dict[str, Any]:
    dealer = "经销商分级与考核管理制度.md"
    customer = "重点客户流失预警办法.md"
    price = "汽车配件价格与折扣管理办法.md"
    inventory = "库存与补货管理规范.md"
    quality = "产品质量与售后处理规范.md"
    goals = "2026年度经营目标.md"
    cases = [
        case(
            "w3-dev-single-01",
            "dev",
            "single_document",
            "A级经销商连续下降后，公司要求采取哪些整改措施？",
            [src(dealer, "4.2")],
            [
                fact("专项预警", "1个工作日内发出专项预警"),
                fact("书面整改计划", "5个工作日内提交书面整改计划"),
                fact("联合拜访", "10个工作日内完成一次联合客户拜访"),
                fact("观察期", "30日整改观察期"),
            ],
            unacceptable=["3个工作日内提交说明"],
            tags=["dealer", "version_conflict"],
        ),
        case(
            "w3-dev-single-02",
            "dev",
            "single_document",
            "什么情况会触发经销商经营预警？系统预警能否直接证明客户即将流失？",
            [src(dealer, "3.2")],
            [
                fact("连续下降", "连续两个月环比下降"),
                fact("季度阈值", "季度销售额环比下降超过20%", "环比下降超过20%"),
                fact("预警边界", "不直接证明客户即将流失"),
            ],
            unacceptable=["预警即证明客户即将流失"],
            tags=["dealer", "boundary"],
        ),
        case(
            "w3-dev-single-03",
            "dev",
            "single_document",
            "A级经销商降级由谁提出、谁批准？",
            [src(dealer, "5.1")],
            [fact("提出人", "区域销售经理提出"), fact("批准人", "销售总监批准")],
            unacceptable=["区域负责人直接调整等级"],
            tags=["dealer", "approval"],
        ),
        case(
            "w3-dev-single-04",
            "dev",
            "single_document",
            "重点客户的数据预警包含哪些可量化条件？",
            [src(customer, "2.1")],
            [
                fact("月度条件", "月度销售额连续两个月环比下降"),
                fact("同比条件", "季度销售额同比下降超过20%"),
                fact("采购间隔", "最近60天没有有效采购"),
            ],
            tags=["customer", "threshold"],
        ),
        case(
            "w3-dev-single-05",
            "dev",
            "single_document",
            "重点客户风险颜色如何按条件数量分级？",
            [src(customer, "2.2")],
            [
                fact("黄色", "满足一项为黄色关注"),
                fact("橙色", "满足两项为橙色预警"),
                fact("红色", "满足三项及以上", "明确表达停止合作意向为红色预警"),
            ],
            unacceptable=["预警分数直接当作流失事实"],
            tags=["customer", "classification"],
        ),
        case(
            "w3-dev-single-06",
            "dev",
            "single_document",
            "重点客户流失预警中，客户经理、区域销售经理和客户运营部分别负责什么？",
            [src(customer, "3.3")],
            [
                fact(
                    "客户经理",
                    "客户经理是第一责任人",
                    "联系客户、核验原因、提出方案并更新进展",
                ),
                fact("区域销售经理", "协调价格、库存、技术和售后资源"),
                fact("客户运营部", "预警监控、时限提醒、证据完整性检查和闭环督办"),
            ],
            tags=["customer", "roles"],
        ),
        case(
            "w3-dev-single-07",
            "dev",
            "single_document",
            "黄色、橙色和红色客户预警各有什么处理时限？",
            [src(customer, "4.1")],
            [
                fact("黄色时限", "10个工作日内完成核验"),
                fact("橙色时限", "5个工作日内提交方案"),
                fact("红色时限", "1个工作日内升级", "3个工作日内完成首次管理层复盘"),
            ],
            tags=["customer", "deadline"],
        ),
        case(
            "w3-dev-single-08",
            "dev",
            "single_document",
            "一般订单的标准折扣上限是多少，谁可以按已批准方案执行？",
            [src(price, "3.1")],
            [
                fact(
                    "标准上限",
                    "一般订单折扣不超过8%",
                    "不超过8%",
                    "标准折扣上限是8%",
                ),
                fact("执行人", "客户经理可以按已批准的客户方案执行"),
            ],
            tags=["price", "threshold"],
        ),
        case(
            "w3-dev-single-09",
            "dev",
            "single_document",
            "什么情况会触发折扣与毛利专项复核，由哪些部门负责？",
            [src(price, "5.2")],
            [
                fact("触发条件", "平均折扣上升超过3个百分点且毛利率同步下降"),
                fact("负责部门", "财务部与销售运营部"),
            ],
            tags=["price", "margin"],
        ),
        case(
            "w3-test-single-10",
            "test",
            "single_document",
            "重点安全类产品预计多久内缺货可以申请紧急补货，谁审批？",
            [src(inventory, "3.2")],
            [
                fact("缺货窗口", "预计7天内缺货"),
                fact("审批人", "供应链经理审批"),
                fact("申请依据", "客户影响、需求依据、运输成本和临时替代方案"),
            ],
            tags=["inventory", "approval"],
        ),
        case(
            "w3-test-single-11",
            "test",
            "single_document",
            "库存进入滞销复核的条件是什么？",
            [src(inventory, "5")],
            [fact("滞销条件", "连续90天无销售且无已确认订单")],
            tags=["inventory", "threshold"],
        ),
        case(
            "w3-test-single-12",
            "test",
            "single_document",
            "涉及人身安全风险或批量失效时属于什么级别，应立即采取什么措施？",
            [src(quality, "2.1")],
            [
                fact("问题级别", "一级问题"),
                fact("停止出库", "立即停止相关批次继续出库"),
                fact("上报时限", "2小时内上报质量负责人"),
            ],
            tags=["quality", "safety"],
        ),
        case(
            "w3-test-single-13",
            "test",
            "single_document",
            "一二三级质量问题的首次响应时限分别是多少？",
            [src(quality, "3.1")],
            [
                fact("一级响应", "一级问题2小时内响应"),
                fact("二级响应", "二级问题1个工作日内响应"),
                fact("三级响应", "三级问题2个工作日内响应"),
            ],
            tags=["quality", "deadline"],
        ),
        case(
            "w3-test-single-14",
            "test",
            "single_document",
            "什么销售下降幅度要求区域负责人组织专项诊断？",
            [src(goals, "2.1")],
            [
                fact("环比阈值", "季度销售额环比下降超过10%"),
                fact("同比阈值", "同比下降超过15%"),
            ],
            tags=["goals", "threshold"],
        ),
        case(
            "w3-challenge-single-15",
            "challenge",
            "single_document",
            "月度经营报告应在什么时候完成，并注明哪些分析信息？",
            [src(goals, "4.1")],
            [
                fact("完成时间", "每月第5个工作日前"),
                fact("报告信息", "数据截止日期、统计口径和异常阈值"),
                fact("内容分层", "分别列示事实、可能因素和建议"),
            ],
            tags=["goals", "reporting"],
        ),
        case(
            "w3-dev-multi-01",
            "dev",
            "multi_document",
            "华东某A级经销商季度销售环比下降25%，公司应先认定什么风险，并按现行制度采取哪些关键动作？",
            [src(dealer, "3.2"), src(dealer, "4.2"), src(goals, "2.1")],
            [
                fact(
                    "经营异常", "季度销售额环比下降超过20%触发经营预警", "触发经营预警"
                ),
                fact("专项诊断", "区域负责人应组织专项诊断"),
                fact(
                    "整改动作",
                    "专项预警",
                    "书面整改计划",
                    "联合客户拜访",
                    "30日整改观察期",
                ),
            ],
            unacceptable=["直接取消A级资格", "3个工作日内提交说明"],
            tags=["dealer", "goals", "version_conflict"],
        ),
        case(
            "w3-dev-multi-02",
            "dev",
            "multi_document",
            "重点客户达到橙色预警并提出13%折扣诉求时，谁负责处置，折扣由谁审批？",
            [src(customer, "3.2"), src(customer, "3.3"), src(price, "4.2")],
            [
                fact(
                    "客户责任",
                    "客户经理是第一责任人",
                    "第一责任人是客户经理",
                    "第一责任人",
                ),
                fact(
                    "协调责任",
                    "区域销售经理负责协调",
                    "区域销售经理负责复核挽回方案并协调",
                ),
                fact("折扣审批", "销售总监和财务总监共同审批"),
            ],
            unacceptable=["可以流失风险为由绕过审批"],
            tags=["customer", "price", "approval"],
        ),
        case(
            "w3-dev-multi-03",
            "dev",
            "multi_document",
            "刹车系统预计7天内缺货且可能影响安全类客户时，紧急补货和质量响应分别依据什么规则？",
            [src(inventory, "3.2"), src(quality, "2.1")],
            [
                fact("紧急补货", "可发起紧急补货", "供应链经理审批"),
                fact(
                    "安全风险",
                    "一级问题",
                    "立即停止相关批次继续出库",
                    "2小时内上报质量负责人",
                ),
            ],
            tags=["inventory", "quality", "safety"],
        ),
        case(
            "w3-dev-multi-04",
            "dev",
            "multi_document",
            "A级经销商调整等级时，经营分析系统和审批流程各有什么边界？",
            [src(dealer, "5.1"), src(goals, "5")],
            [
                fact("审批流程", "区域销售经理提出，销售总监批准", "区域销售经理提出"),
                fact(
                    "系统边界",
                    "经营分析系统只能提供辅助判断",
                    "只能提供辅助判断",
                ),
                fact("证据边界", "没有数据或制度依据时应明确说明证据不足"),
            ],
            tags=["dealer", "governance"],
        ),
        case(
            "w3-dev-multi-05",
            "dev",
            "multi_document",
            "销售下降同时出现缺货和质量投诉时，报告应如何区分可能原因，哪些结论不能直接下？",
            [src(inventory, "4.1"), src(quality, "5")],
            [
                fact("库存边界", "不能只依据销售额将下降归因于客户需求"),
                fact("质量边界", "不能仅凭时间相关性认定质量问题导致销售下降"),
                fact("证据要求", "引用投诉和质量调查证据", "引用实际库存或缺货记录"),
            ],
            unacceptable=["质量问题是销售下降的唯一原因"],
            tags=["causality", "evidence"],
        ),
        case(
            "w3-dev-multi-06",
            "dev",
            "multi_document",
            "经营报告发现品类折扣上升4个百分点且毛利率连续下降时，应使用什么毛利率口径并启动什么复核？",
            [src(goals, "2.2"), src(price, "5.2")],
            [
                fact("毛利率口径", "总毛利除以总销售额", "禁止直接平均单笔毛利率"),
                fact(
                    "专项复核",
                    "财务部与销售运营部应开展专项复核",
                    "启动财务部与销售运营部的专项复核",
                ),
            ],
            tags=["margin", "price"],
        ),
        case(
            "w3-test-multi-07",
            "test",
            "multi_document",
            "红色客户预警涉及超标准折扣时，升级时限和审批纪律是什么？",
            [src(customer, "4.1"), src(customer, "3.2"), src(price, "4.2")],
            [
                fact("升级时限", "1个工作日内升级", "3个工作日内完成首次管理层复盘"),
                fact("审批纪律", "不得以流失风险为由绕过审批"),
                fact(
                    "折扣权限",
                    "按以下权限审批",
                    "区域销售经理和财务经理",
                    "销售总监和财务总监",
                ),
            ],
            tags=["customer", "price", "deadline"],
        ),
        case(
            "w3-test-multi-08",
            "test",
            "multi_document",
            "刹车系统区域经营报告和库存分析分别必须观察哪些指标，为什么不能只看销售额？",
            [src(goals, "3.1"), src(inventory, "2.2")],
            [
                fact("经营指标", "销售额、销量、平均折扣和加权毛利率"),
                fact("库存指标", "库存周转天数、缺货次数、滞销数量和在途数量"),
                fact("判断边界", "单看期末库存不能判断供应是否健康"),
            ],
            tags=["goals", "inventory", "metrics"],
        ),
        case(
            "w3-test-multi-09",
            "test",
            "multi_document",
            "重点客户一次恢复下单后能否立即关闭流失风险，经销商等级恢复又需要什么条件？",
            [src(customer, "4.2"), src(dealer, "5.2")],
            [
                fact("客户关闭边界", "一次新订单但未恢复稳定采购时只能降级观察"),
                fact("等级恢复", "连续两个考核周期恢复目标后，可以申请重新评定"),
            ],
            unacceptable=["一次新订单即可直接关闭"],
            tags=["customer", "dealer", "closure"],
        ),
        case(
            "w3-challenge-multi-10",
            "challenge",
            "multi_document",
            "超过15%的折扣申请如果涉及经营系统建议，应如何审批并保留什么边界？",
            [src(price, "4.2"), src(goals, "5")],
            [
                fact("审批链", "销售总监和财务总监审核", "总经理批准"),
                fact("系统边界", "经营分析系统只能提供辅助判断"),
                fact("证据不足", "没有数据或制度依据时应明确说明证据不足"),
            ],
            tags=["price", "governance", "approval"],
        ),
        case(
            "w3-dev-exact-01",
            "dev",
            "exact_clause",
            "请准确列出《汽车配件价格与折扣管理办法》4.2节的三个现行折扣审批区间和审批人。",
            [src(price, "4.2")],
            [
                fact(
                    "8至12",
                    "超过8%且不超过12%，须由区域销售经理和财务经理共同审批",
                    "超过8%且不超过12%，由区域销售经理和财务经理共同审批",
                ),
                fact(
                    "12至15",
                    "超过12%且不超过15%，须由销售总监和财务总监共同审批",
                    "超过12%且不超过15%，由销售总监和财务总监共同审批",
                ),
                fact("超过15", "超过15%", "还须总经理批准"),
            ],
            unacceptable=["10%", "14%", "18%"],
            tags=["exact", "version_conflict"],
        ),
        case(
            "w3-dev-exact-02",
            "dev",
            "exact_clause",
            "请按《经销商分级与考核管理制度》4.2节列出A级经销商连续下降后的五项措施。",
            [src(dealer, "4.2")],
            [
                fact("预警", "1个工作日内发出专项预警"),
                fact("整改计划", "5个工作日内提交书面整改计划"),
                fact("联合拜访", "10个工作日内完成一次联合客户拜访"),
                fact("观察", "30日整改观察期", "每周跟踪订单、库存、价格和客户反馈"),
                fact("复核", "发起等级与资源支持复核", "报销售总监审批"),
            ],
            tags=["exact", "dealer"],
        ),
        case(
            "w3-dev-exact-03",
            "dev",
            "exact_clause",
            "《重点客户流失预警办法》3.3节规定的三类核心岗位职责是什么？",
            [src(customer, "3.3")],
            [
                fact("客户经理", "第一责任人"),
                fact("区域销售经理", "协调价格、库存、技术和售后资源"),
                fact("客户运营部", "预警监控、时限提醒、证据完整性检查和闭环督办"),
            ],
            tags=["exact", "roles"],
        ),
        case(
            "w3-dev-exact-04",
            "dev",
            "exact_clause",
            "《库存与补货管理规范》4.1节为什么禁止仅凭销售额认定需求下降？",
            [src(inventory, "4.1")],
            [
                fact("原因拆分", "区分需求下降、缺货、价格变化和客户流失"),
                fact(
                    "禁止结论",
                    "存在缺货记录时，不能只依据销售额将下降归因于客户需求",
                    "不能只依据销售额将下降归因于客户需求",
                ),
            ],
            tags=["exact", "causality"],
        ),
        case(
            "w3-dev-exact-05",
            "dev",
            "exact_clause",
            "《产品质量与售后处理规范》第5节对销售下降和质量投诉的因果表述有什么限制？",
            [src(quality, "5")],
            [
                fact("待验证因素", "可以将质量问题列为待验证因素"),
                fact("因果限制", "不能仅凭时间相关性认定质量问题导致销售下降"),
                fact("证据要求", "引用投诉和质量调查证据"),
            ],
            tags=["exact", "causality"],
        ),
        case(
            "w3-dev-exact-06",
            "dev",
            "exact_clause",
            "《2026年度经营目标》2.2节规定毛利率应如何计算，禁止什么做法？",
            [src(goals, "2.2")],
            [
                fact("公式", "总毛利除以总销售额"),
                fact("禁止", "禁止直接平均单笔毛利率"),
            ],
            tags=["exact", "metric"],
        ),
        case(
            "w3-test-exact-07",
            "test",
            "exact_clause",
            "《2026年度经营目标》第5节对没有数据或制度依据的情况要求如何表述？",
            [src(goals, "5")],
            [fact("证据不足", "应明确说明证据不足")],
            tags=["exact", "no_evidence"],
        ),
        case(
            "w3-test-exact-08",
            "test",
            "exact_clause",
            "《重点客户流失预警办法》4.2节规定风险关闭必须具备什么，一次新订单应如何处理？",
            [src(customer, "4.2")],
            [
                fact("关闭条件", "客户沟通记录和后续经营数据"),
                fact("一次订单", "只能降级观察，不能直接关闭"),
            ],
            tags=["exact", "closure"],
        ),
        case(
            "w3-test-exact-09",
            "test",
            "exact_clause",
            "《汽车配件价格与折扣管理办法》2.2节如何解释0.0800，并规定哪种平均折扣口径？",
            [src(price, "2.2")],
            [
                fact("比例解释", "0.0800表示按未折扣成交金额优惠8%"),
                fact("监控口径", "制度监控默认采用订单行平均折扣率"),
            ],
            tags=["exact", "metric"],
        ),
        case(
            "w3-challenge-exact-10",
            "challenge",
            "exact_clause",
            "《库存与补货管理规范》3.2节的紧急补货触发条件、申请材料和审批人分别是什么？",
            [src(inventory, "3.2")],
            [
                fact("触发", "重点安全类产品预计7天内缺货"),
                fact("材料", "客户影响、需求依据、运输成本和临时替代方案"),
                fact("审批", "供应链经理审批"),
            ],
            tags=["exact", "approval"],
        ),
        case(
            "w3-dev-noanswer-01",
            "dev",
            "no_answer",
            "现行制度规定单笔两千万元设备投资由谁审批？",
            [],
            [],
            unacceptable=["两千万元设备投资由总经理审批"],
            tags=["no_answer", "finance"],
        ),
        case(
            "w3-dev-noanswer-02",
            "dev",
            "no_answer",
            "公司国内出差住宿费每天的报销上限是多少元？",
            [],
            [],
            unacceptable=["住宿费上限为500元", "住宿费上限为800元"],
            tags=["no_answer", "travel"],
        ),
        case(
            "w3-dev-noanswer-03",
            "dev",
            "no_answer",
            "员工每年有多少天带薪病假，由谁审批？",
            [],
            [],
            unacceptable=["每年10天带薪病假", "由人力资源部审批"],
            tags=["no_answer", "hr"],
        ),
        case(
            "w3-test-noanswer-04",
            "test",
            "no_answer",
            "信息安全制度要求员工密码多少天强制更换一次？",
            [],
            [],
            unacceptable=["每90天更换密码", "每60天更换密码"],
            tags=["no_answer", "security"],
        ),
        case(
            "w3-challenge-noanswer-05",
            "challenge",
            "no_answer",
            "销售人员的季度佣金比例是多少，最高封顶多少？",
            [],
            [],
            unacceptable=["季度佣金比例为3%", "最高封顶20万元"],
            tags=["no_answer", "compensation"],
        ),
    ]
    return {
        "name": "InsightAgent Week 3 RAG Retrieval and Citation Benchmark",
        "version": "1.0.2",
        "dataset_status": "frozen-before-final-run",
        "frozen_at": "2026-09-17",
        "annotation_audit": (
            "Dev scorer audit added meaning-preserving answer aliases and removed one "
            "fact not asked by its question; test/challenge questions were not inspected."
        ),
        "split_policy": "Only dev may guide tuning; test and challenge remain frozen.",
        "case_type_counts": {
            "single_document": 15,
            "multi_document": 10,
            "exact_clause": 10,
            "no_answer": 5,
        },
        "acceptance_thresholds": {
            "document_hit_at_5": 0.90,
            "mrr": 0.80,
            "answer_fact_accuracy": 0.90,
            "citation_precision": 0.90,
            "no_answer_accuracy": 1.0,
            "fabricated_citation_count": 0,
        },
        "cases": cases,
    }


def main() -> int:
    dataset = build_dataset()
    errors = validate_rag_dataset(dataset)
    if errors:
        raise ValueError("Week 3 数据集无效:\n- " + "\n- ".join(errors))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(dataset['cases'])} cases to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
