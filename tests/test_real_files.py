"""
解析 Stellaris 游戏文件 - common/buildings 并生成 Python 代码
"""

import sys
from pathlib import Path
from collections import defaultdict

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import parse
from synthetipy.ast_nodes import ObjectNode
from synthetipy.codegen import generate_python_code

# Stellaris 游戏目录
STELLARIS_ROOT = Path("D:/SteamLibrary/steamapps/common/Stellaris")
BUILDINGS_PATH = STELLARIS_ROOT / "common" / "buildings"

# 输出目录 - 输出到工作目录的 test_python_output 文件夹
OUTPUT_ROOT = Path(__file__).parent.parent / "test_python_output"
OUTPUT_PATH = OUTPUT_ROOT / "buildings"


def parse_file(filepath):
    """解析单个文件并生成 Python 代码"""
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
        
        # 生成 Python 代码
        relative_path = f"common/buildings/{filepath.name}"
        python_code = generate_python_code(ast, relative_path)
        
        # 输出到文件
        output_file = OUTPUT_PATH / f"{filepath.stem}.py"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(python_code)
        
        print(f"[OK] 解析成功！")
        print(f"   文件大小: {len(content)} 字符")
        print(f"   对象数量: {len(objects)}")
        print(f"   输出文件: {output_file.relative_to(OUTPUT_ROOT)}")
        
        # 显示前几个对象
        if objects:
            print(f"\n   对象列表（前 5 个）:")
            for i, obj in enumerate(objects[:5]):
                print(f"     {i+1}. {obj.name}")
        
        return {
            'success': True,
            'objects': len(objects),
            'size': len(content),
            'output_size': len(python_code),
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
            'output_size': 0,
            'error': str(e)
        }


def main():
    """主函数：解析所有 buildings 文件 → Python 代码生成测试"""
    print("="*60)
    print("  Stellaris Buildings → Python 代码生成测试")
    print("="*60)
    print(f"\n游戏目录: {STELLARIS_ROOT}")
    print(f"Buildings 路径: {BUILDINGS_PATH}")
    print(f"输出目录: {OUTPUT_PATH}")
    
    # 检查目录是否存在
    if not BUILDINGS_PATH.exists():
        print(f"\n错误: Buildings 目录不存在!")
        print(f"   请检查游戏路径: {STELLARIS_ROOT}")
        return
    
    # 创建输出目录
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    print(f"✓ 输出目录已创建")
    
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
    total_output = sum(r['output_size'] for r in results.values())
    
    print(f"\n统计信息:")
    print(f"   总文件数: {len(results)}")
    print(f"   [OK] 成功: {success_count}")
    print(f"   [FAIL] 失败: {fail_count}")
    print(f"   总对象数: {total_objects}")
    print(f"   总输入大小: {total_size:,} 字符")
    print(f"   总输出大小: {total_output:,} 字符")
    
    # 失败文件详情
    if fail_count > 0:
        print(f"\n失败的文件:")
        for filename, result in results.items():
            if not result['success']:
                print(f"   - {filename}")
                if result.get('error'):
                    error_msg = result['error']
                    if len(error_msg) > 100:
                        error_msg = error_msg[:100] + "..."
                    print(f"     错误: {error_msg}")
    
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
    print(f"  测试完成！Python 文件已输出到: {OUTPUT_PATH}")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
