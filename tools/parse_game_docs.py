"""
解析游戏官方文档，提取 trigger/effect/scope 的结构信息

从 script_documentation/*.log 文件中提取：
1. 特殊块（需要内部处理的块，如 hidden_effect, switch, random_list）
2. 作用域块（会改变作用域的块，如 owner, fleet, planet）
3. 简单调用（直接转换为函数调用的）
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional




class UsageAnalyzer:
    """用法字符串分析器"""
    
    def __init__(self):
        # 已知的子上下文关键字
        self.context_keywords = {
            'effect', 'fail_effect', 'limit', 'trigger', 'pre_triggers', 
            'while', 'else_if', 'if', 'else', 'function'
        }
        # 常见参数（非上下文）
        self.param_keywords = {
            'days', 'type', 'target', 'who', 'value', 'name', 'id',
            'add', 'remove', 'factor', 'min', 'max', 'category', 'scope',
            'owner', 'species', 'pop_group', 'graphical_culture'
        }
        # 允许的参数 token（不限于尖括号内容，可用于判定枚举与参数）
        # 不仅用于角括号内判断，也用于普通枚举、括号内枚举等
        self.allowed_param_tokens = set([
            'string', 'text', 'int', 'float', 'key', 
            'filename', 'bool', 'number', 'percentage',
            'yes', 'no', 'variable', 'scope.variable','num', 'all', 'any',
            'job',
            'resource_name', 'category_name',
            'target', 'owner','country', 'planet', 'system', 'fleet', 'ship', 'building',
            
            'district_type_key', 'zone_type_key', 'building_type_key',
            'district_slot_index', 'zone_slot_index',

            
            'random','init effect','star class','string@scope','key@scope','origin',
            'amount',
            
            'flag', 'tech key','preset key',
            
            'female', 'male', 'indeterminable','relic_key',
            'planet scope', 'col_rural','parameter','event_chain',
            'resource_key','rarity','specimen_key', 'exhibit',
            'focus_card_key','cb_type','perk_key',
            'starbase module','starbase building',
            'name of type','specialist_type_key','sector type',
            'living_standard', 'citizenship', 'military_service', 'slavery', 'purge', 'colonization_control', 'population_control', 'migration_control', 'none',
            'federation perk', 'resolution','resolution type',
            'resolution_category','support', 'oppose', 'abstain',
            'origin key', 'resolution_type_key',
            'setting', 'asset type',
            'crisis_perk_name', 'crisis_level_name',
            'espionage category key','espionage type key',
            'buildable','term', 'term_value', 'action_key',
            'age_key', 'rift_id',
            'specimen', 'specimen_type','holding',
            'key or species event target',
            'pc_tundra', 'storm_type', 'modifier', 'stage',
            'approach', 'attackers', 'defenders', 'deposit',
            'hyperlane', 'euclidean',
            'prethoryn', 'unbidden', 'contingency', 'synth_queen',
            'upkeep', 'produces', 'balance',
            'component template key', 'solar system',
            'empire','jobtype', 'pop_category',
            'pop faction scope', 'isolationist',
            'attack', 'weaken', 'vassalize', 'alliance', 'coexist', 'trade',
            'improve_relations', 'harm_relations', 'federation', 'galactic_community', 'spy_network', 'first_contact', 'strengthen_imperial_authority', 'undermine_imperial_authority',
            'event_chain_key','federation law','federation type','federation law category',
            'archaeological site type key',
            'category key', 'starbase_ship_size',
            'colossus status',
            'random_no_capital',
            'in_system', 'out_system',
            'event_id', 'some_id', 'last_created_design',
            'target country', 'target mega structure',
            'patron_name', 'deed', 'category_key', 'patron_key', 
            'starbase_type', 'mission_key',
            'star','random_blocker', 'random_nonblocker','attacker',
            'cloud_type','exhibit_target','defensive', 'offensive',
            'event target','colony type','site type', 'trait',
            'starbase_module', 'starbase_building',
            
        ])
        # 上下文级（表示块/体的内容类型，如 `<effects>` / `<triggers>`）
        self.allowed_context_angle_tokens = set([
            'effects', 'triggers', 'display_triggers',
        ])

    def _extract_tokens(self, s: str) -> List[str]:
        """提取值字符串中的 tokens（尖括号类型、枚举、数值等）。

        保证不调用 analyze；独立纯函数，避免递归。
        """
        tokens: List[str] = []

        # 1) 尖括号内的类型/占位符，保留短语并按 '/' 拆分
        for inner in re.findall(r'<\s*([^>]+?)\s*>', s):
            parts = [p.strip() for p in inner.split('/') if p.strip()]
            for part in parts:
                # 提取 default = X 形式的默认值
                m = re.search(r'default\s*[:=]?\s*([A-Za-z0-9_]+)', part)
                if m:
                    tokens.append(m.group(1))
                # 删除注释括号
                part_clean = re.sub(r'\(.*?\)', '', part).strip()
                if part_clean:
                    tokens.append(part_clean)

        # 2) yes/no 等布尔
        for yn in re.findall(r'\b(yes|no|true|false)\b', s, flags=re.I):
            tokens.append(yn.lower())

        # 3) 数值或范围
        for num in re.findall(r'\b\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\b', s):
            tokens.append(num)

        # 4) 行内 '/' 分隔的简单枚举（忽略包含 '=' 或尖括号片段）
        if '/' in s:
            for segment in re.split(r'\s*/\s*', s):
                seg = segment.strip()
                if not seg or '=' in seg or '<' in seg or '>' in seg:
                    continue
                words = seg.split()
                if 1 <= len(words) <= 3:
                    tokens.append(seg)

        # 去重并过滤无意义词
        seen = set()
        out = []
        for t in tokens:
            if t.lower() in ('or', 'and', 'optional', 'default', 'note', 'note:'):
                continue
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out
    
    def analyze(self, name: str, usage_str: str) -> Dict:
        """入口：分析用法字符串，返回结构信息。

        高层职责：分类 -> 解析 -> 汇总/最终化
        """
        usage_str = usage_str.strip()
        result = {
            "type": "unknown",
            "context_params": {},
            "context": None,
            "params": {},
            "has_implicit_body": False,
            "parsing_valid": True,
            "raw_usage": usage_str
        }

        # 小工具：提取尖括号 / 枚举 / 数值等 tokens
        def _extract_tokens(s: str) -> List[str]:
            return self._extract_tokens(s)

        # 小工具：对解析出来的 token 做归一化（例如数值字面量或 'number'/'int'/'float' -> 'num'）
        def _normalize_tokens(tokens: List[str]) -> List[str]:
            out: List[str] = []
            for t in tokens:
                # 清理外层标点（括号、逗号、句点等）并小写
                t_clean = re.sub(r'^[\(\[\s]+|[\)\],.:;\s]+$', '', t).strip()
                if not t_clean:
                    continue
                # 删除括号及其后的注释，例如 "computing (optional" -> "computing"
                t_clean = re.sub(r'\s*\(.*', '', t_clean).strip()
                if not t_clean:
                    continue
                tl = t_clean.lower()
                # 数值或范围（例如 15, 1.0, 0-100, 0.0-1.0）映射为 num
                if re.match(r'^\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?$', t_clean):
                    nt = 'num'
                elif tl in ('number', 'int', 'float', 'num'):
                    nt = 'num'
                elif tl in ('yes', 'no', 'true', 'false'):
                    nt = 'bool'
                else:
                    nt = tl
                if nt not in out:
                    out.append(nt)
            return out

        # 分类用法（assignment/comparison/block/weighted/simple）
        def _classify(u: str) -> str:
            # 在判断比较运算符时，先移除尖括号内容以避免把 '<value>' 误判为比较
            if '{' not in u:
                u_no_angles = re.sub(r'<[^>]*>', '', u)
                if any(op in u_no_angles for op in ['>=', '<=', '>', '<']):
                    return 'comparison'
                elif '=' in u_no_angles:
                    return 'assignment'
                else:
                    return 'simple'
            # 包含大括号
            if re.search(r"\d+\s*=\s*\{", u):
                return 'weighted_list'
            return 'block'

        # 解析简单赋值/比较，将值放到 [none]
        def _parse_simple(u: str) -> Dict:
            rhs = u.split('=', 1)[-1].split('#', 1)[0].strip() if '=' in u else u
            # 如果形式为 "identifier <cmp> value"，则作为 value_compare 处理
            if re.match(r'^\s*\w+\s*([<>]=?|>=|<=)\s*', u):
                return {'[none]': ['value_compare']}

            vals = _extract_tokens(rhs)
            # 对非尖括号枚举/字面 token 做未知检测（例如括号内的 controlled/excessive/none）
            for tok in list(vals):
                clean = re.sub(r'^[\(\[\s]+|[\)\],.:;\s]+$', '', tok).strip()
                if not clean:
                    continue
                clean_lower = clean.lower()
                # 删除括号及其后的注释，例如 "computing (optional" -> "computing"
                base = re.sub(r'\s*\(.*', '', clean_lower).strip()
                if not base:
                    continue
                # 数字或范围不应被标记为 unknown
                if re.match(r'^\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?$', base):
                    continue
                if ' ' in base:
                    if base in self.allowed_context_angle_tokens or base in self.context_keywords or base in self.param_keywords or base in self.allowed_param_tokens:
                        continue
                    unknowns.append(base)
                    continue
                if base in self.context_keywords or base in self.param_keywords or base in self.allowed_param_tokens or base in self.allowed_context_angle_tokens:
                    # 若原始 token 含额外标点/括号（如 'none)'), 记录原始形式用于人工审查
                    if tok != base:
                        unknowns.append(tok)
                    continue
                unknowns.append(base)

            # 归一化 tokens（例如数字 -> num）
            vals = _normalize_tokens(vals)
            if not vals:
                vals = ['unknown']
            return {'[none]': vals}

        # 找到匹配的 '}' 的索引, start 指向 '{'
        def _find_matching_brace(s: str, start: int) -> int:
            depth = 0
            for i in range(start, len(s)):
                if s[i] == '{':
                    depth += 1
                elif s[i] == '}':
                    depth -= 1
                    if depth == 0:
                        return i
            return -1

        # 用于收集尖括号中未知 token 的列表（闭包共享）
        unknowns: List[str] = []

        # 解析花括号内部内容为嵌套结构（递归支持）
        def _parse_inner_block(inner: str) -> Dict:
            # inner 不包含最外层大括号
            pos = 0
            n = len(inner)
            out: Dict = {}
            while pos < n:
                # 跳过空白
                m = re.search(r"\S", inner[pos:])
                if not m:
                    break
                pos += m.start()
                # 读取 key 或 key 比较形式（例如 "value > 10"）
                km = re.match(r"(\w+)\s*=\s*", inner[pos:])
                if not km:
                    # 尝试匹配比较表达式（key <cmp> value），如 'value > 10' 或 'value >= 1/variable'
                    cmpm = re.match(r"(\w+)\s*([<>]=?|>=|<=)\s*([^\n\r]+)", inner[pos:])
                    if cmpm:
                        key = cmpm.group(1)
                        # 记录为 value_compare 类型（不需要记录实际比较值）
                        out[key] = ['value_compare']
                        pos += cmpm.end()
                        # 继续解析下一个条目/键
                        continue
                    # 无法识别，跳出
                    break
                key = km.group(1)
                pos += km.end()
                # 判断值是嵌套块还是单值
                if pos < n and inner[pos] == '{':
                    end = _find_matching_brace(inner, pos)
                    if end == -1:
                        # 未闭合，保留原始并标记为需人工审查
                        out[key] = ['unclosed_block']
                        break
                    content = inner[pos+1:end]
                    # 递归解析内部
                    parsed_content = _parse_inner_block(content)
                    # 如果内部没有键值对（例如只是 { <planet triggers> }），则尝试提取尖括号 token 并作为值列表返回
                    if not parsed_content:
                        local_toks: List[str] = []
                        for inner_tok in re.findall(r'<\s*([^>]+?)\s*>', content):
                            for part in [p.strip() for p in inner_tok.split('/') if p.strip()]:
                                part_lower = part.lower()
                                # 如果包含 '='，通常是注释或说明，跳过
                                if '=' in part:
                                    continue

                                # 如果是显式上下文关键字（effects/triggers），收集为本地标记并继续
                                if part_lower in self.allowed_context_angle_tokens:
                                    local_toks.append(part_lower)
                                    continue

                                # 处理包含空格的复合 token，例如 'planet triggers'，优先添加完整短语为未知
                                if ' ' in part:
                                    phrase = part_lower.strip()
                                    if phrase in self.allowed_context_angle_tokens or phrase in self.context_keywords or phrase in self.param_keywords or phrase in self.allowed_param_tokens:
                                        continue
                                    unknowns.append(phrase)
                                    local_toks.append(f"<{phrase}>")
                                    continue

                                # 单词形式 token 的常规处理
                                if part_lower in self.context_keywords or part_lower in self.param_keywords or part_lower in self.allowed_param_tokens:
                                    local_toks.append(part_lower)
                                    continue

                                # 收集未知 token
                                unknowns.append(part_lower)
                                local_toks.append(part_lower)

                        toks = _extract_tokens(content)
                        if not toks and local_toks:
                            toks = local_toks
                        if not toks:
                            toks = ['implicit_block']
                        # 归一化 tokens
                        toks = _normalize_tokens(toks)
                        out[key] = toks
                    else:
                        out[key] = parsed_content
                    pos = end + 1
                else:
                    # 非嵌套值，读取直到下一个 key=value 或 key <cmp> value，或者结尾
                    m_eq = re.search(r"\s+\w+\s*=", inner[pos:])
                    m_cmp = re.search(r"\s+\w+\s*(?:[<>]=?|>=|<=)", inner[pos:])
                    # 选择最先出现的匹配
                    next_pos = None
                    if m_eq and m_cmp:
                        next_pos = m_eq.start() if m_eq.start() < m_cmp.start() else m_cmp.start()
                    elif m_eq:
                        next_pos = m_eq.start()
                    elif m_cmp:
                        next_pos = m_cmp.start()

                    if next_pos is not None:
                        val = inner[pos:pos+next_pos].strip()
                        pos = pos + next_pos
                    else:
                        val = inner[pos:].strip()
                        pos = n
                    val = val.split('#', 1)[0].strip()

                    # 检测尖括号内未知 token（用于收集需人工审查项）
                    for inner_tok in re.findall(r'<\s*([^>]+?)\s*>', val):
                        for part in [p.strip() for p in inner_tok.split('/') if p.strip()]:
                            part_lower = part.lower()
                            # 如果包含 '='，通常是注释或说明，跳过
                            if '=' in part:
                                continue

                            # 如果是显式上下文关键字（effects/triggers），跳过
                            if part_lower in self.allowed_context_angle_tokens:
                                continue

                            # 处理包含空格的复合 token（例如 'system target' 或 'planet triggers'）
                            if ' ' in part:
                                # 优先把整个短语作为单一 token 检查（例如 'system target'）
                                phrase = part_lower.strip()
                                if phrase in self.allowed_context_angle_tokens or phrase in self.context_keywords or phrase in self.param_keywords or phrase in self.allowed_param_tokens:
                                    continue
                                # 记录完整短语为未知 token（避免只记录其中单词）
                                unknowns.append(phrase)
                                continue

                            # 单词形式 token 的常规处理
                            if part_lower in self.context_keywords or part_lower in self.param_keywords or part_lower in self.allowed_param_tokens:
                                continue

                            # 收集未知 token
                            unknowns.append(part_lower)

                    toks = _extract_tokens(val)

                    # 额外检测非尖括号的枚举与字面 token（例如括号内的 controlled/excessive/none 或 行内 '/' 枚举）
                    # 把不在允许集合中的 token 收入 unknowns 以触发人工审查
                    toks_check = list(toks)  # 未归一化的原始 token 列表
                    for tok in toks_check:
                        clean = re.sub(r'^[\(\[\s]+|[\)\],.:;\s]+$', '', tok).strip().lower()
                        if not clean:
                            continue
                        # 删除括号及其后的注释，例如 "computing (optional" -> "computing"
                        base = re.sub(r'\s*\(.*', '', clean).strip()
                        if not base:
                            continue
                        # 数字或范围不应被标记为 unknown
                        if re.match(r'^\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?$', base):
                            continue
                        if ' ' in base:
                            if base in self.allowed_context_angle_tokens or base in self.context_keywords or base in self.param_keywords or base in self.allowed_param_tokens:
                                continue
                            unknowns.append(base)
                            continue
                        if base in self.context_keywords or base in self.param_keywords or base in self.allowed_param_tokens or base in self.allowed_context_angle_tokens:
                            # 如果原始 token 带有未清理的括号或标点，也把原始形式当成可疑项记录（便于人工审查）
                            if tok != base:
                                unknowns.append(tok)
                            continue
                        unknowns.append(base)

                    toks = _extract_tokens(val)
                    if not toks:
                        # 如果值包含 {} 可能表示隐式块
                        if '{' in val and '}' in val:
                            toks = ['implicit_block']
                        elif val:
                            toks = [val]
                        else:
                            toks = ['unknown']
                    # 归一化 tokens
                    toks = _normalize_tokens(toks)
                    out[key] = toks
            return out

        # 解析块结构（可能是单行 compact 或 多行）
        def _parse_block(u: str) -> Tuple[Dict, Dict[str, List[str]], bool, Optional[str], List[str]]:
            """返回 (params_dict, context_params_dict, has_implicit_body, context, unknowns)

            context_params_dict: mapping of context-key -> list of body types (e.g. {'limit': ['effect']})
            context: overall implicit body type when detected (e.g. 'effect' or 'trigger')
            unknowns: list of unknown angle-bracket tokens found inside the block
            """
            params: Dict = {}
            context_params: Dict[str, List[str]] = {}
            has_implicit_body = False
            context: Optional[str] = None
            # 使用闭包中的 unknowns 集合以收集整个用法字符串中的未知 tokens（避免局部遮蔽）
            # unknowns 列表在外层定义： unknowns: List[str] = []
            # 注意：不要在此处创建新的局部 unknowns，否则会阻止收集到外部 closure。

            # 找到第一对外层大括号
            br = re.search(r'\{', u)
            if not br:
                return params, context_params, has_implicit_body, context, unknowns
            start = br.start()
            end = _find_matching_brace(u, start)
            if end == -1:
                # 未闭合，尽量解析剩余
                inner = u[start+1:]
                parsing_valid = False
            else:
                inner = u[start+1:end]

            # 如果内联缓和：直接使用内解析器
            inner = inner.strip()
            # 快速检测是否为纯 weights 列表（权重项通常对应一个隐式 body，例如 <effects>）
            if re.search(r"\d+\s*=\s*\{", inner):
                has_implicit_body = True
                # 在顶层查找 effects/triggers 标记，优先确定 body 类型
                body_match = None
                for m in re.finditer(r'<\s*(effects|triggers)\s*>', inner):
                    pos = m.start()
                    depth = 0
                    for ch in inner[:pos]:
                        if ch == '{':
                            depth += 1
                        elif ch == '}':
                            depth -= 1
                    if depth == 0:
                        body_match = m
                        break

                body_singular = 'effect'
                if body_match:
                    body = body_match.group(1)
                    body_singular = 'effect' if body == 'effects' else 'trigger'

                # 将权重作为 context 参数映射到 body 类型
                context_params['[weights]'] = [body_singular]
                if not context:
                    context = body_singular

                return params, context_params, has_implicit_body, context, unknowns

            # 使用内解析器，它能处理 compact 与多行形式
            parsed_inner = _parse_inner_block(inner)

            # 将 parsed_inner 的键和值分类
            context_keys: List[str] = []

            for k, v in parsed_inner.items():
                # 如果是上下文关键字，则不要将其计入 params，而是放入 context_params
                if k in self.context_keywords:
                    context_keys.append(k)

                    # 尝试从原始 inner 文本中识别上下文体（<effects> / <triggers>）
                    ctx_types: List[str] = []
                    m = re.search(rf"{re.escape(k)}\s*=\s*\{{([^}}]*)\}}", inner)
                    if m:
                        seg = m.group(1)
                        if re.search(r'<\s*effects\s*>', seg):
                            ctx_types.append('effect')
                        if re.search(r'<\s*triggers\s*>', seg):
                            ctx_types.append('trigger')

                    # 如果 parsed value 包含显式标记，也可判定
                    if isinstance(v, list):
                        joined = ' '.join(v)
                        if re.search(r'\beffects\b', joined) or '<effects>' in joined:
                            ctx_types.append('effect')
                        if re.search(r'\btriggers\b', joined) or '<triggers>' in joined:
                            ctx_types.append('trigger')

                    # 去重并保持顺序；如果没有检测到类型，保留空列表以表明存在该上下文键
                    ctx_types = list(dict.fromkeys(ctx_types))
                    context_params[k] = ctx_types

                    # 从值或检测到的类型推断隐式 body（注意：不要在这里设置整体的 result['context']，
                    # 只有在顶层直接出现 <effects>/<triggers> 时，才设置整体 context 字段）
                    if isinstance(v, dict) or (isinstance(v, list) and ('<effects>' in ' '.join(v) or '<triggers>' in ' '.join(v))) or bool(ctx_types):
                        has_implicit_body = True
                else:
                    # 非 context 的正常参数
                    params[k] = v
                    if isinstance(v, dict) or (isinstance(v, list) and ('<effects>' in ' '.join(v) or '<triggers>' in ' '.join(v))):
                        has_implicit_body = True

            # 检测顶层隐式 body（只在最外层匹配，忽略嵌套块内的标记）
            body_match = None
            for m in re.finditer(r'<\s*(effects|triggers)\s*>', inner):
                pos = m.start()
                depth = 0
                for ch in inner[:pos]:
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                if depth == 0:
                    body_match = m
                    break

            if body_match:
                body = body_match.group(1)
                body_singular = 'effect' if body == 'effects' else 'trigger'
                has_implicit_body = True
                if context_keys:
                    # 如果存在顶层隐式体，将其作为优先映射到第一个 context key（覆盖先前推断）
                    first_k = context_keys[0]
                    context_params[first_k] = [body_singular]
                    # 将顶层隐式体作为整体 context（覆盖先前推断）
                    context = body_singular
                else:
                    if not context:
                        context = body_singular

            return params, context_params, has_implicit_body, context, unknowns

        # ---- 主体流程 ----
        typ = _classify(usage_str)
        result['type'] = typ

        if typ in ('simple', 'comparison', 'assignment'):
            result['params'] = _parse_simple(usage_str)
            # 将收集到的未知 tokens 返回给上层用于写入 review
            result['review_tokens'] = list(dict.fromkeys(unknowns))
            return result

        if typ == 'weighted_list':
            # 只是标记，解析 weights/implicit body
            params, context_map, hib, ctx, unknowns = _parse_block(usage_str)
            result['params'].update(params)
            result['context_params'].update(context_map)
            result['has_implicit_body'] = hib
            if ctx:
                result['context'] = ctx
            if context_map:
                result['type'] = 'context_container'
            # 如果检测到未知尖括号 tokens，标注并返回供上层写入 review
            result['review_tokens'] = list(dict.fromkeys(unknowns))
            return result

        if typ == 'block':
            params, context_map, hib, ctx, unknowns = _parse_block(usage_str)
            result['params'].update(params)
            result['context_params'].update(context_map)
            result['has_implicit_body'] = hib
            if ctx:
                result['context'] = ctx

            # 如果包含 context_params 或顶层隐式 body 的 context，则视为 context_container
            if result['context_params'] or result['context']:
                result['type'] = 'context_container'



            # 将未知 token 收入结果，供上游决定是否写入 review
            result['review_tokens'] = list(dict.fromkeys(unknowns))

            return result

        # 兜底
        result['parsing_valid'] = False
        return result


class GameDocParser:
    """游戏文档解析器"""
    
    def __init__(self, doc_dir: Path):
        self.doc_dir = Path(doc_dir)
        self.analyzer = UsageAnalyzer()
        
        # 解析结果
        self.triggers: Dict[str, Dict] = {}
        self.effects: Dict[str, Dict] = {}
        self.scopes: Dict[str, Dict] = {}
        self.modifiers: Dict[str, List[str]] = {}
        self.localizations: Dict[str, Dict] = {}
        
        # 需要人工校验的列表
        self.manual_review: Dict[str, Dict] = {}
    
    def parse_all(self):
        """解析所有文档

        先清空或创建 review_needed 目录，保证本次运行的 review 文件覆盖而非追加。
        """
        review_dir = self.doc_dir / 'review_needed'
        if review_dir.exists():
            # 删除旧的 review 文件（覆盖行为）
            for p in review_dir.iterdir():
                try:
                    if p.is_file():
                        p.unlink()
                except Exception:
                    pass
        else:
            review_dir.mkdir()

        self.parse_triggers()
        self.parse_effects()
        self.parse_scopes()
        self.parse_modifiers()
        self.parse_localizations()
    
    def parse_triggers(self):
        """解析 triggers.log"""
        file_path = self.doc_dir / 'triggers.log'
        if not file_path.exists():
            return
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 分割为独立条目
        entries = self._split_entries(content)
        
        for entry in entries:
            name, desc, usage, scopes = self._parse_entry(entry)
            if name:
                # 分析 usage 结构
                structure = self.analyzer.analyze(name, usage)
                
                # 如果解析置信度低，加入人工审查列表
                if not structure['parsing_valid'] or structure['type'] == 'complex_unknown':
                    self.manual_review[name] = {
                        'type': 'trigger',
                        'raw_usage': usage,
                        'reason': 'Complex or unclear usage structure'
                    }

                # 如果 analyzer 检测到需人工审查的尖括号 tokens，追加写入 review 文件
                review_tokens = structure.get('review_tokens') or []
                if review_tokens:
                    self._append_review_file('triggers.log', name, entry, review_tokens)
                    self.manual_review[name] = {
                        'type': 'trigger',
                        'raw_usage': usage,
                        'reason': 'Unknown angle-bracket tokens',
                        'tokens': review_tokens
                    }

                self.triggers[name] = {
                    'description': desc,
                    'usage': usage,
                    'scopes': scopes,
                    'structure': structure
                }
    
    def parse_effects(self):
        """解析 effects.log"""
        file_path = self.doc_dir / 'effects.log'
        if not file_path.exists():
            return
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        entries = self._split_entries(content)
        
        for entry in entries:
            name, desc, usage, scopes = self._parse_entry(entry)
            if name:
                # 分析 usage 结构
                structure = self.analyzer.analyze(name, usage)
                
                if not structure['parsing_valid'] or structure['type'] == 'complex_unknown':
                    self.manual_review[name] = {
                        'type': 'effect',
                        'raw_usage': usage,
                        'reason': 'Complex or unclear usage structure'
                    }

                # 如果 analyzer 检测到需人工审查的尖括号 tokens，追加写入 review 文件
                review_tokens = structure.get('review_tokens') or []
                if review_tokens:
                    self._append_review_file('effects.log', name, entry, review_tokens)
                    self.manual_review[name] = {
                        'type': 'effect',
                        'raw_usage': usage,
                        'reason': 'Unknown angle-bracket tokens',
                        'tokens': review_tokens
                    }

                self.effects[name] = {
                    'description': desc,
                    'usage': usage,
                    'scopes': scopes,
                    'structure': structure
                }
    
    def _append_review_file(self, source_filename: str, name: str, entry: str, tokens: List[str]):
        """把需要人工 review 的条目追加到 script_documentation/review_needed/<source_filename> 中"""
        review_dir = self.doc_dir / 'review_needed'
        review_dir.mkdir(exist_ok=True)
        out_path = review_dir / source_filename
        with open(out_path, 'a', encoding='utf-8') as f:
            f.write(f"=== {name} ===\n")
            f.write(f"Unknown tokens: {tokens}\n")
            f.write(entry.strip() + '\n\n')

    def parse_scopes(self):
        """解析 scopes.log"""
        file_path = self.doc_dir / 'scopes.log'
        if not file_path.exists():
            return
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        entries = self._split_entries(content)
        
        for entry in entries:
            name, desc, _, scopes = self._parse_entry(entry)
            if name:
                # 提取输出作用域
                output_scope = self._extract_output_scope(entry)
                self.scopes[name] = {
                    'description': desc,
                    'input_scopes': scopes,
                    'output_scope': output_scope,
                }
    
    def parse_modifiers(self):
        """解析 modifiers.log"""
        file_path = self.doc_dir / 'modifiers.log'
        if not file_path.exists():
            return
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 格式: "- modifier_name, Category: category1, category2"
        pattern = r'^- ([\w_]+), Category: (.+)$'
        for line in content.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                modifier_name = match.group(1)
                categories_str = match.group(2)
                categories = [c.strip() for c in categories_str.split(',')]
                self.modifiers[modifier_name] = categories
    
    def parse_localizations(self):
        """解析 localizations.log"""
        file_path = self.doc_dir / 'localizations.log'
        if not file_path.exists():
            return
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        current_scope = None
        current_section = None  # 'promotions' or 'properties'
        
        for line in content.split('\n'):
            line = line.strip()
            
            # 跳过空行和注释
            if not line or line.startswith('[') or line.startswith('=='):
                continue
            
            # 检测作用域标题: --Country--
            if line.startswith('--') and line.endswith('--'):
                current_scope = line.strip('-')
                if current_scope:
                    self.localizations[current_scope] = {
                        'promotions': [],
                        'properties': []
                    }
                    current_section = None
            # 检测节标题
            elif line == 'Promotions:' and current_scope:
                current_section = 'promotions'
            elif line == 'Properties' and current_scope:
                current_section = 'properties'
            # 添加项目
            elif current_scope and current_section and line:
                self.localizations[current_scope][current_section].append(line)
    
    def _split_entries(self, content: str) -> List[str]:
        """分割文档为独立条目
        
        处理多种格式：
        1. 标准格式：name - description
        2. 共享 Supported Scopes：多个条目共用一个 Supported Scopes 行
        3. 名称中包含 usage：如 trait_of_species = { ... } - description
        """
        entries = []
        current_group = []  # 当前组（可能包含多个共享 Supported Scopes 的条目）
        
        for line in content.split('\n'):
            # 跳过标题行和空行
            if '==' in line or not line.strip():
                continue
            
            # 遇到 Supported Scopes，说明当前组结束
            if line.startswith('Supported Scopes:') or line.startswith('Output Scope:'):
                if current_group:
                    current_group.append(line)
                    # 拆分组内的多个条目
                    self._split_shared_entries(current_group, entries)
                    current_group = []
                continue
            
            current_group.append(line)
        
        # 处理最后一组
        if current_group:
            self._split_shared_entries(current_group, entries)
        
        return entries
    
    def _is_entry_start(self, line: str) -> bool:
        """判断一行是否为条目的起始行（含 ' - '），且 '-' 必须位于尖括号外。"""
        # 缩进的行不是起始行
        if line.startswith(' '):
            return False
        if ' - ' not in line:
            return False
        # 检查所有 ' - ' 出现的位置，确认是否位于尖括号外
        for m in re.finditer(r' - ', line):
            idx = m.start()
            # 检查 '-' 是否被尖括号包围：查找左侧最近的 '<' 和右侧最近的 '>'
            left_angle = line.rfind('<', 0, idx)
            right_angle = line.find('>', idx)
            if left_angle != -1 and right_angle != -1 and left_angle < idx < right_angle:
                # '-' 位于 '<...>' 内，跳过这个匹配
                continue
            # 只要存在一个不在尖括号内的 ' - '，就认为是条目起始行
            return True
        return False

    def _split_shared_entries(self, group: List[str], entries: List[str]):
        """拆分共享 Supported Scopes 的多个条目"""
        if not group:
            return
        
        # 查找最后的 Supported Scopes 行
        supported_scopes_line = None
        content_lines = group
        
        for i in range(len(group) - 1, -1, -1):
            if group[i].startswith('Supported Scopes:') or group[i].startswith('Output Scope:'):
                supported_scopes_line = group[i]
                content_lines = group[:i]
                break
        
        # 查找所有条目的起始位置（包含 " - " 的行，且 '-' 不在尖括号内）
        entry_starts = []
        for i, line in enumerate(content_lines):
            if self._is_entry_start(line):
                entry_starts.append(i)
        
        if not entry_starts:
            return
        
        # 分割条目
        for idx, start in enumerate(entry_starts):
            end = entry_starts[idx + 1] if idx + 1 < len(entry_starts) else len(content_lines)
            entry_lines = content_lines[start:end]
            
            # 添加 Supported Scopes 行
            if supported_scopes_line:
                entry_lines.append(supported_scopes_line)
            
            entries.append('\n'.join(entry_lines))
    
    def _parse_entry(self, entry: str) -> Tuple[str, str, str, List[str]]:
        """解析单个条目
        
        处理两种格式：
        1. 标准格式：name - description \n usage \n Supported Scopes
        2. 名称包含用法：name = { ... } - description \n usage \n Supported Scopes
        """
        lines = entry.split('\n')
        if not lines:
            return None, None, None, []
        
        # 第一行: name - description
        first_line = lines[0]
        if ' - ' not in first_line:
            return None, None, None, []
        
        name_part, description = first_line.split(' - ', 1)
        name_part = name_part.strip()
        description = description.strip()
        
        # 提取真正的名称（去掉可能的 usage 部分）
        # 例如：trait_of_species = { trait_has_all_tags = { positive } } 
        #      应该提取为：trait_of_species
        if '=' in name_part:
            # 名称中包含了 usage，提取等号前的部分
            name = name_part.split('=')[0].strip()
        else:
            name = name_part
        
        # 提取用法示例和支持的作用域
        # usage 是从第二行开始到 "Supported Scopes:" 之间的所有内容
        usage_lines = []
        scopes = []
        in_usage = False
        
        for line in lines[1:]:
            if line.startswith('Supported Scopes:'):
                scopes_str = line.replace('Supported Scopes:', '').strip()
                scopes = [s.strip() for s in scopes_str.split()]
                break
            elif line.startswith('Output Scope:'):
                # scopes.log 中可能直接是 Output Scope
                break
            else:
                # 收集 usage 行
                if line.strip():
                    usage_lines.append(line)
                    in_usage = True
                elif in_usage:
                    # 保留空行（在代码块中可能有意义）
                    usage_lines.append(line)
        
        # 如果第一行包含 usage（有 = 和 {}），并且没有其他 usage 行
        # 将第一行的 usage 部分也加入
        if '=' in name_part and '{' in name_part and not usage_lines:
            # 例如：trait_of_species = { trait_has_all_tags = { positive } }
            usage_lines.append(name_part)
        
        # 合并 usage 行，保持格式
        usage = '\n'.join(usage_lines).strip()
        
        return name, description, usage, scopes
    
    def _extract_output_scope(self, entry: str) -> str:
        """提取输出作用域"""
        match = re.search(r'Output Scope:\s+(\w+)', entry)
        if match:
            return match.group(1)
        return 'unknown'
    

    def export_to_json(self, output_dir: Path):
        """导出为 JSON 文件"""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # 导出完整信息
        with open(output_dir / 'triggers.json', 'w', encoding='utf-8') as f:
            json.dump(self.triggers, f, indent=2, ensure_ascii=False)
        
        with open(output_dir / 'effects.json', 'w', encoding='utf-8') as f:
            json.dump(self.effects, f, indent=2, ensure_ascii=False)
        
        with open(output_dir / 'scopes.json', 'w', encoding='utf-8') as f:
            json.dump(self.scopes, f, indent=2, ensure_ascii=False)
        
        with open(output_dir / 'modifiers.json', 'w', encoding='utf-8') as f:
            json.dump(self.modifiers, f, indent=2, ensure_ascii=False)
        
        with open(output_dir / 'localizations.json', 'w', encoding='utf-8') as f:
            json.dump(self.localizations, f, indent=2, ensure_ascii=False)

        # 导出人工审查列表
        if self.manual_review:
            with open(output_dir / 'manual_review_needed.json', 'w', encoding='utf-8') as f:
                json.dump(self.manual_review, f, indent=2, ensure_ascii=False)
            print(f"⚠️ 生成了人工审查列表: {len(self.manual_review)} 个条目")

        print(f"✓ 导出完成到 {output_dir}")
        print(f"  - triggers: {len(self.triggers)} 个")
        print(f"  - effects: {len(self.effects)} 个")
        print(f"  - scopes: {len(self.scopes)} 个")
        print(f"  - modifiers: {len(self.modifiers)} 个")
        print(f"  - localizations: {len(self.localizations)} 个作用域")
    
    def print_summary(self):
        """打印摘要信息"""
        print("\n=== 解析摘要 ===")
        print(f"\nTriggers: {len(self.triggers)} 个")
        
        print(f"\nEffects: {len(self.effects)} 个")
        
        print(f"\nScopes: {len(self.scopes)} 个")
        
        print(f"\nModifiers: {len(self.modifiers)} 个")
        # 统计 category
        all_categories = set()
        for categories in self.modifiers.values():
            all_categories.update(categories)
        print(f"  - 不同类别: {len(all_categories)} 个")
        
        print(f"\nLocalizations: {len(self.localizations)} 个作用域")
        total_promotions = sum(len(info['promotions']) for info in self.localizations.values())
        total_properties = sum(len(info['properties']) for info in self.localizations.values())
        print(f"  - 总推广: {total_promotions} 个")
        print(f"  - 总属性: {total_properties} 个")


def main():
    """主函数"""
    script_dir = Path(__file__).parent.parent / 'script_documentation'
    output_dir = Path(__file__).parent.parent / 'codegen_rules'
    
    if not script_dir.exists():
        print(f"❌ 文档目录不存在: {script_dir}")
        return
    
    print(f"解析游戏文档: {script_dir}")
    
    parser = GameDocParser(script_dir)
    parser.parse_all()
    parser.print_summary()
    parser.export_to_json(output_dir)
    
    print("\n✓ 完成！")
    print(f"\n生成的文件可以用于:")
    print(f"  1. trigger_generator.py - 生成 trigger 代码")
    print(f"  2. effect_generator.py - 生成 effect 代码")


if __name__ == '__main__':
    main()
