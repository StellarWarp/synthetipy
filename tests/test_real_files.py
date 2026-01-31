"""
解析 Stellaris 游戏文件 - common/buildings
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
BUILDINGS_PATH = STELLARIS_ROOT / "common" / "buildings"


def parse_file(filepath: Path):
    """解析单个文件"""
    print(f"\n{'='*60}")
    print(f"解析文件: {filepath.name}")
    print(f"{'='*60}")
    
    try:
        # 读取文件
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        # 解析
        ast = parse(content)
        
        # 统计
        objects = [s for s in ast.statements if isinstance(s, ObjectNode)]
        print(f"[OK] 解析成功！")
        print(f"   文件大小: {len(content)} 字符")
        print(f"   对象数量: {len(objects)}")
        
        # 显示前几个对象
        if objects:
            print(f"\n   对象列表（前 10 个）:")
            for i, obj in enumerate(objects[:10]):
                print(f"     {i+1}. {obj.name}")
                # 统计属性
                props = [s for s in obj.body.statements if hasattr(s, 'key')]
                print(f"        - 属性数: {len(props)}")
        
        return {
            'success': True,
            'objects': len(objects),
            'size': len(content),
            'error': None
        }
        
    except Exception as e:
        print(f"[FAIL] 解析失败:")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   错误信息: {str(e)}")
        return {
            'success': False,
            'objects': 0,
            'size': 0,
            'error': str(e)
        }


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  Stellaris Buildings 文件解析测试")
    print("="*60)
    print(f"\n游戏目录: {STELLARIS_ROOT}")
    print(f"Buildings 路径: {BUILDINGS_PATH}")
    
    # 检查目录是否存在
    if not BUILDINGS_PATH.exists():
        print(f"\n错误: Buildings 目录不存在!")
        print(f"   请检查游戏路径: {STELLARIS_ROOT}")
        return
    
    # 获取所有 .txt 文件
    txt_files = list(BUILDINGS_PATH.glob("*.txt"))
    
    if not txt_files:
        print(f"\n错误: 未找到任何 .txt 文件!")
        return
    
    print(f"\n找到 {len(txt_files)} 个文件")
    print(f"\n开始解析...")
    
    # 解析所有文件
    results = {}
    for filepath in sorted(txt_files):
        result = parse_file(filepath)
        results[filepath.name] = result
    
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
    print(f"   总对象数: {total_objects}")
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
    
    # 按对象数量排序
    if success_count > 0:
        print(f"\n对象最多的文件（Top 5）:")
        sorted_by_objects = sorted(
            [(name, r) for name, r in results.items() if r['success']],
            key=lambda x: x[1]['objects'],
            reverse=True
        )
        for i, (name, result) in enumerate(sorted_by_objects[:5]):
            print(f"   {i+1}. {name}: {result['objects']} 个对象")
    
    print("\n" + "="*60)
    print("  测试完成！")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
