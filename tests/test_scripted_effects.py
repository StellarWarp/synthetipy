"""
测试解析 Stellaris common/script_values 文件
"""

import sys
from pathlib import Path
from collections import defaultdict

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import parse
from synthetipy.ast_nodes import ObjectNode

# Stellaris 游戏目录
STELLARIS_ROOT = Path("D:/SteamLibrary/steamapps/common/Stellaris")
SCRIPTED_EFFECTS_PATH = STELLARIS_ROOT / "common" / "script_values"


def parse_file(filepath: Path):
    """解析单个文件"""
    try:
        # 读取文件
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        # 解析
        ast = parse(content)
        
        # 统计
        objects = [s for s in ast.statements if isinstance(s, ObjectNode)]
        
        return {
            'success': True,
            'objects': len(objects),
            'size': len(content),
            'error': None,
            'object_names': [obj.name for obj in objects]
        }
        
    except Exception as e:
        # 只在失败时输出
        print(f"\n{'='*60}")
        print(f"[FAIL] {filepath.name}")
        print(f"{'='*60}")
        print(f"{str(e)}\n")
        return {
            'success': False,
            'objects': 0,
            'size': 0,
            'error': str(e),
            'object_names': []
        }


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  Stellaris Scripted Effects 文件解析测试")
    print("="*60)
    print(f"\n游戏目录: {STELLARIS_ROOT}")
    print(f"Scripted Effects 路径: {SCRIPTED_EFFECTS_PATH}")
    
    # 检查目录是否存在
    if not SCRIPTED_EFFECTS_PATH.exists():
        print(f"\n错误: Scripted Effects 目录不存在!")
        print(f"   请检查游戏路径: {STELLARIS_ROOT}")
        return
    
    # 获取所有 .txt 文件
    txt_files = list(SCRIPTED_EFFECTS_PATH.glob("*.txt"))
    
    if not txt_files:
        print(f"\n错误: 未找到任何 .txt 文件!")
        return
    
    print(f"\n找到 {len(txt_files)} 个文件")
    print(f"\n开始解析...")
    
    # 解析所有文件
    results = {}
    all_effects = []
    
    for filepath in sorted(txt_files):
        result = parse_file(filepath)
        results[filepath.name] = result
        if result['success']:
            all_effects.extend(result['object_names'])
    
    # 汇总统计
    print("\n" + "="*60)
    print("  解析结果汇总")
    print("="*60)
    
    success_count = sum(1 for r in results.values() if r['success'])
    fail_count = len(results) - success_count
    total_objects = sum(r['objects'] for r in results.values())
    total_size = sum(r['size'] for r in results.values())
    
    print(f"\n统计信息:")
    print(f"   总文件数: {len(results)}")
    print(f"   [OK] 成功: {success_count}")
    print(f"   [FAIL] 失败: {fail_count}")
    print(f"   总效果数: {total_objects}")
    print(f"   总文件大小: {total_size:,} 字符")
    
    # 失败文件详情
    if fail_count > 0:
        print(f"\n失败的文件:")
        for filename, result in results.items():
            if not result['success']:
                print(f"   - {filename}")
                print(f"     错误: {result['error'][:100]}...")
    
    # 成功率
    success_rate = (success_count / len(results)) * 100
    print(f"\n成功率: {success_rate:.1f}%")
    
    # 按效果数量排序
    if success_count > 0:
        print(f"\n效果最多的文件（Top 5）:")
        sorted_by_objects = sorted(
            [(name, r) for name, r in results.items() if r['success']],
            key=lambda x: x[1]['objects'],
            reverse=True
        )
        for i, (name, result) in enumerate(sorted_by_objects[:5]):
            print(f"   {i+1}. {name}: {result['objects']} 个效果")
    
    # 一些有趣的统计
    if all_effects:
        print(f"\n效果名称统计:")
        
        # 按前缀分组
        prefixes = defaultdict(int)
        for name in all_effects:
            if '_' in name:
                prefix = name.split('_')[0]
                prefixes[prefix] += 1
        
        if prefixes:
            print(f"   常见前缀（Top 10）:")
            sorted_prefixes = sorted(prefixes.items(), key=lambda x: x[1], reverse=True)
            for i, (prefix, count) in enumerate(sorted_prefixes[:10]):
                print(f"     {i+1}. {prefix}_*: {count} 个")
        
        # 最长和最短的名称
        shortest = min(all_effects, key=len)
        longest = max(all_effects, key=len)
        print(f"\n   最短效果名: {shortest} ({len(shortest)} 字符)")
        print(f"   最长效果名: {longest} ({len(longest)} 字符)")
    
    print("\n" + "="*60)
    print("  测试完成！")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
