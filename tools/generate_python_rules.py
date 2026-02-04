"""
将解析的 JSON 文档转换为 Python 代码

生成的 Python 模块可以被代码生成器直接导入使用
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any


class UsageParser:
    """解析 usage 字符串，提取参数信息"""
    
    @staticmethod
    def parse_usage(usage: str, name: str) -> Dict[str, Any]:
        """解析 usage 字符串"""
        if not usage:
            return {'format': 'simple', 'params': []}
        
        result = {
            'format': 'unknown',
            'params': [],
            'has_block': False,
            'alternatives': []
        }
        
        # 检查是否有多种调用格式（用 "or" 分隔）
        if '\nor\n' in usage or '\nor ' in usage:
            # 多种格式
            parts = re.split(r'\n\s*or\s*\n', usage, flags=re.IGNORECASE)
            result['format'] = 'alternatives'
            result['alternatives'] = [UsageParser._parse_single_format(p.strip(), name) for p in parts]
            return result
        
        # 单一格式
        return UsageParser._parse_single_format(usage, name)
    
    @staticmethod
    def _parse_single_format(usage: str, name: str) -> Dict[str, Any]:
        """解析单一格式的 usage"""
        result = {
            'format': 'unknown',
            'params': [],
            'has_block': False,
        }
        
        # 简单值： name = <value>
        simple_value_pattern = rf'^{re.escape(name)}\s*=\s*<(.+?)>$'
        if match := re.match(simple_value_pattern, usage.strip()):
            result['format'] = 'simple_value'
            result['value_type'] = match.group(1)
            return result
        
        # 比较： name > 10
        comparison_pattern = rf'^{re.escape(name)}\s*([<>=!]+)\s*(.+)$'
        if match := re.match(comparison_pattern, usage.strip()):
            result['format'] = 'comparison'
            result['operator'] = match.group(1)
            result['value'] = match.group(2).strip()
            return result
        
        # 块结构： name = { ... }
        if '{' in usage:
            result['format'] = 'block'
            result['has_block'] = True
            result['params'] = UsageParser._extract_block_params(usage)
            return result
        
        # 简单标志： name = yes/no
        if re.match(rf'^{re.escape(name)}\s*=\s*(yes|no)$', usage.strip()):
            result['format'] = 'flag'
            return result
        
        return result
    
    @staticmethod
    def _extract_block_params(usage: str) -> List[Dict[str, str]]:
        """从块结构中提取参数"""
        params = []
        
        # 匹配参数定义： param_name = <type> 或 param_name = value (default: ...)
        param_patterns = [
            r'(\w+)\s*=\s*<(.+?)>',  # key = <type>
            r'(\w+)\s*=\s*(.+?)\s*\(default:\s*(.+?)\)',  # key = value (default: ...)
            r'(\w+)\s*=\s*(yes|no|\d+|".+?")',  # key = yes/no/数字/字符串
        ]
        
        for pattern in param_patterns:
            for match in re.finditer(pattern, usage):
                param_name = match.group(1)
                if len(match.groups()) >= 2:
                    param_info = {
                        'name': param_name,
                        'type': match.group(2).strip() if '<' in pattern else 'value',
                    }
                    if len(match.groups()) >= 3:
                        param_info['default'] = match.group(3).strip()
                    params.append(param_info)
        
        # 检测 <triggers> 或 <effects> 占位符
        if '<triggers>' in usage:
            params.append({'name': 'body', 'type': 'triggers'})
        elif '<effects>' in usage:
            params.append({'name': 'body', 'type': 'effects'})
        
        return params


class PythonRulesGenerator:
    """生成 Python 规则代码"""
    
    def __init__(self, codegen_rules_dir: Path):
        self.rules_dir = Path(codegen_rules_dir)
        
        # 加载 JSON 数据
        self.triggers = self._load_json('triggers.json')
        self.effects = self._load_json('effects.json')
        self.scopes = self._load_json('scopes.json')
        self.modifiers = self._load_json('modifiers.json')
        self.localizations = self._load_json('localizations.json')
        self.special_blocks = self._load_json('special_blocks.json')
        
        # 跟踪生成的变量名
        self.modifier_vars = []
        
        # 分析共享和独占的标识符
        self.analyze_shared_identifiers()
    
    def _load_json(self, filename: str) -> Dict:
        """加载 JSON 文件"""
        path = self.rules_dir / filename
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def analyze_shared_identifiers(self):
        """分析 trigger 和 effect 之间共享的标识符"""
        trigger_names = set(self.triggers.keys())
        effect_names = set(self.effects.keys())
        scope_names = set(self.scopes.keys())
        
        self.shared_identifiers = trigger_names & effect_names
        self.trigger_identifiers_exclusive = trigger_names - effect_names
        self.effect_identifiers_exclusive = effect_names - trigger_names
        self.scopes_identifiers = scope_names
        
        print(f"共享标识符: {len(self.shared_identifiers)} 个")
        print(f"Trigger 独占: {len(self.trigger_identifiers_exclusive)} 个")
        print(f"Effect 独占: {len(self.effect_identifiers_exclusive)} 个")
        print(f"Scopes: {len(self.scopes_identifiers)} 个")
    
    def generate_all(self, output_dir: Path):
        """生成所有 Python 规则文件"""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # 1. 生成基础定义
        self._generate_identifiers_module(output_dir)
        
        # 2. 生成 trigger 规则
        self._generate_trigger_rules(output_dir)
        
        # 3. 生成 effect 规则
        self._generate_effect_rules(output_dir)
        
        # 4. 生成 scope 规则
        self._generate_scope_rules(output_dir)
        
        # 5. 生成 modifier 规则
        self._generate_modifier_rules(output_dir)
        
        # 6. 生成统一的 __init__.py
        self._generate_init_file(output_dir)
        
        print(f"\n✓ 所有规则文件已生成到: {output_dir}")
    
    def _generate_identifiers_module(self, output_dir: Path):
        """生成标识符分类模块"""
        lines = [
            '"""',
            'PDXLang 标识符分类',
            '',
            '此文件由 tools/generate_python_rules.py 自动生成',
            '不要手动编辑！',
            '"""',
            '',
            '# 共享标识符（同时存在于 trigger 和 effect 中）',
            f'SHARED_IDENTIFIERS = frozenset({self._format_set(self.shared_identifiers)})',
            '',
            '# Trigger 独占标识符',
            f'TRIGGER_IDENTIFIERS_EXCLUSIVE = frozenset({self._format_set(self.trigger_identifiers_exclusive)})',
            '',
            '# Effect 独占标识符',
            f'EFFECT_IDENTIFIERS_EXCLUSIVE = frozenset({self._format_set(self.effect_identifiers_exclusive)})',
            '',
            '# 所有 Scopes',
            f'SCOPES_IDENTIFIERS = frozenset({self._format_set(self.scopes_identifiers)})',
            '',
        ]
        
        self._write_file(output_dir / 'identifiers.py', lines)
    
    def _generate_trigger_rules(self, output_dir: Path):
        """生成 trigger 规则"""
        lines = [
            '"""',
            'PDXLang Trigger 规则',
            '',
            '此文件由 tools/generate_python_rules.py 自动生成',
            '"""',
            '',
            'from typing import Dict, List, Any',
            '',
        ]
        
        # 生成 ALL_TRIGGERS
        lines.append('# 所有 triggers')
        lines.append('ALL_TRIGGERS = {')
        
        for name, info in sorted(self.triggers.items()):
            # 解析 usage
            parsed_usage = UsageParser.parse_usage(info['usage'], name)
            
            lines.append(f'    {repr(name)}: {{')
            lines.append(f'        "description": {repr(info["description"])},')
            lines.append(f'        "scopes": {info["scopes"]},')
            lines.append(f'        "usage_format": {repr(parsed_usage["format"])},')
            if parsed_usage.get('params'):
                lines.append(f'        "params": {parsed_usage["params"]},')
            if parsed_usage.get('alternatives'):
                lines.append(f'        "alternatives": [')
                for alt in parsed_usage['alternatives']:
                    lines.append(f'            {alt},')
                lines.append(f'        ],')
            lines.append(f'    }},')
        
        lines.append('}')
        lines.append('')
        
        self._write_file(output_dir / 'trigger_rules.py', lines)
    
    def _generate_effect_rules(self, output_dir: Path):
        """生成 effect 规则（与 trigger 类似）"""
        lines = [
            '"""',
            'PDXLang Effect 规则',
            '',
            '此文件由 tools/generate_python_rules.py 自动生成',
            '"""',
            '',
            'from typing import Dict, List, Any',
            '',
        ]
        
        # 生成 ALL_EFFECTS
        lines.append('# 所有 effects')
        lines.append('ALL_EFFECTS = {')
        
        for name, info in sorted(self.effects.items()):
            parsed_usage = UsageParser.parse_usage(info['usage'], name)
            
            lines.append(f'    {repr(name)}: {{')
            lines.append(f'        "description": {repr(info["description"])},')
            lines.append(f'        "scopes": {info["scopes"]},')
            lines.append(f'        "usage_format": {repr(parsed_usage["format"])},')
            if parsed_usage.get('params'):
                lines.append(f'        "params": {parsed_usage["params"]},')
            if parsed_usage.get('alternatives'):
                lines.append(f'        "alternatives": [')
                for alt in parsed_usage['alternatives']:
                    lines.append(f'            {alt},')
                lines.append(f'        ],')
            lines.append(f'    }},')
        
        lines.append('}')
        lines.append('')
        
        self._write_file(output_dir / 'effect_rules.py', lines)
    
    def _generate_scope_rules(self, output_dir: Path):
        """生成 scope 规则"""
        lines = [
            '"""',
            'PDXLang Scope 规则',
            '',
            '此文件由 tools/generate_python_rules.py 自动生成',
            '"""',
            '',
            'SCOPES = {',
        ]
        
        for name, info in sorted(self.scopes.items()):
            lines.append(f'    {repr(name)}: {{')
            lines.append(f'        "description": {repr(info["description"])},')
            lines.append(f'        "input_scopes": {info["input_scopes"]},')
            lines.append(f'        "output_scope": {repr(info["output_scope"])},')
            lines.append(f'    }},')
        
        lines.append('}')
        lines.append('')
        
        self._write_file(output_dir / 'scope_rules.py', lines)
    
    def _generate_modifier_rules(self, output_dir: Path):
        """生成 modifier 规则"""
        lines = [
            '"""',
            'PDXLang Modifier 规则',
            '',
            '此文件由 tools/generate_python_rules.py 自动生成',
            f'共 {len(self.modifiers)} 个 modifiers',
            '"""',
            '',
        ]
        
        # 按类别分组
        by_category = {}
        for name, categories in self.modifiers.items():
            for cat in categories:
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(name)
        
        # 生成类别集合
        for category, modifiers in sorted(by_category.items()):
            var_name = f'MODIFIERS_{self._sanitize_name(category).upper()}'
            self.modifier_vars.append(var_name)
            lines.append(f'# {category}')
            lines.append(f'{var_name} = {self._format_set(set(modifiers))}')
            lines.append('')
        
        # 生成完整的 modifier -> categories 映射
        lines.append('# 完整的 modifier -> categories 映射')
        lines.append('MODIFIER_CATEGORIES = {')
        for name, categories in sorted(self.modifiers.items()):
            lines.append(f'    {repr(name)}: {categories},')
        lines.append('}')
        lines.append('')
        
        # 生成所有 modifiers 集合
        lines.append('# 所有 modifiers')
        lines.append(f'ALL_MODIFIERS = {self._format_set(set(self.modifiers.keys()))}')
        lines.append('')
        
        self._write_file(output_dir / 'modifier_rules.py', lines)
    
    def _generate_special_blocks_rules(self, output_dir: Path):
        """生成特殊块规则"""
        lines = [
            '"""',
            'PDXLang 特殊块规则',
            '',
            '此文件由 tools/generate_python_rules.py 自动生成',
            '"""',
            '',
        ]
        
        for category, blocks in sorted(self.special_blocks.items()):
            var_name = f'{category.upper()}_BLOCKS'
            lines.append(f'# {category}')
            lines.append(f'{var_name} = {self._format_set(set(blocks))}')
            lines.append('')
        
    def _generate_init_file(self, output_dir: Path):
        """生成 __init__.py"""
        lines = [
            '"""',
            'PDXLang 代码生成规则',
            '',
            '此模块包含从游戏官方文档自动生成的规则',
            '"""',
            '',
            '# 标识符分类',
            'from .identifiers import SHARED_IDENTIFIERS, TRIGGER_IDENTIFIERS_EXCLUSIVE, EFFECT_IDENTIFIERS_EXCLUSIVE, SCOPES_IDENTIFIERS',
            '',
            '# Trigger 和 Effect 规则',
            'from .trigger_rules import ALL_TRIGGERS',
            'from .effect_rules import ALL_EFFECTS',
            '',
            '# Scope 规则',
            'from .scope_rules import SCOPES',
            '',
            '# Modifier 规则',
            f'from .modifier_rules import MODIFIER_CATEGORIES, ALL_MODIFIERS, {", ".join(self.modifier_vars)}',
            '',
        ]
        
        self._write_file(output_dir / '__init__.py', lines)
    
    def _format_set(self, s: Set[str], max_line_length: int = 100) -> str:
        """格式化集合为多行字符串"""
        if not s:
            return 'set()'
        
        items = sorted(s)
        if len(items) <= 5 and sum(len(repr(i)) for i in items) < max_line_length:
            # 单行
            return '{' + ', '.join(repr(i) for i in items) + '}'
        
        # 多行
        lines = ['{']
        current_line = '    '
        for item in items:
            item_repr = repr(item) + ','
            if len(current_line) + len(item_repr) > max_line_length and current_line != '    ':
                lines.append(current_line)
                current_line = '    '
            current_line += item_repr + ' '
        
        if current_line.strip():
            lines.append(current_line.rstrip())
        lines.append('}')
        
        return '\n'.join(lines)
    
    def _sanitize_name(self, name: str) -> str:
        """清理名称为合法的 Python 标识符"""
        return re.sub(r'[^\w]', '_', name)
    
    def _write_file(self, path: Path, lines: List[str]):
        """写入文件"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"  ✓ {path.name}")


def main():
    """主函数"""
    rules_dir = Path(__file__).parent.parent / 'codegen_rules'
    output_dir = Path(__file__).parent.parent / 'src' / 'synthetipy' / 'game_definitions'
    
    if not rules_dir.exists():
        print(f"❌ 规则目录不存在: {rules_dir}")
        print("请先运行 tools/parse_game_docs.py")
        return
    
    print(f"从 {rules_dir} 生成 Python 规则...")
    print()
    
    generator = PythonRulesGenerator(rules_dir)
    generator.generate_all(output_dir)
    
    print()
    print("✓ 完成！")
    print()
    print("生成的模块可以这样使用:")
    print("  from synthetipy.game_definitions import ALL_TRIGGERS, ALL_EFFECTS")
    print("  from synthetipy.game_definitions import SHARED_IDENTIFIERS, TRIGGER_IDENTIFIERS_EXCLUSIVE")


if __name__ == '__main__':
    main()
