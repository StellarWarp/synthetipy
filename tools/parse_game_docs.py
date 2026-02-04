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
from typing import Dict, List, Set, Tuple


class GameDocParser:
    """游戏文档解析器"""
    
    def __init__(self, doc_dir: Path):
        self.doc_dir = Path(doc_dir)
        
        # 解析结果
        self.triggers: Dict[str, Dict] = {}
        self.effects: Dict[str, Dict] = {}
        self.scopes: Dict[str, Dict] = {}
        self.modifiers: Dict[str, List[str]] = {}  # modifier -> categories
        self.localizations: Dict[str, Dict] = {}   # scope -> {promotions, properties}
    
    def parse_all(self):
        """解析所有文档"""
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
                self.triggers[name] = {
                    'description': desc,
                    'usage': usage,
                    'scopes': scopes
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
                self.effects[name] = {
                    'description': desc,
                    'usage': usage,
                    'scopes': scopes
                }
    
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
        
        # 查找所有条目的起始位置（包含 " - " 的行）
        entry_starts = []
        for i, line in enumerate(content_lines):
            if ' - ' in line and not line.startswith(' '):
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
