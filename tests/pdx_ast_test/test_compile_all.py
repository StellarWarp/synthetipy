"""
通用编译测试 - 解析并重新编译 Stellaris 文件
支持多个子目录：scripted_effects, scripted_triggers, buildings 等
输出到 test_output/common/对应子目录
"""

import sys
from pathlib import Path
from collections import defaultdict

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import parse, compile_to_file
from synthetipy.ast_nodes import ObjectNode

# Stellaris 游戏目录
STELLARIS_ROOT = Path("D:/SteamLibrary/steamapps/common/Stellaris")

# 输出目录
OUTPUT_ROOT = Path(__file__).parent.parent / "test_output"


def compile_file(input_filepath: Path, output_filepath: Path):
    """编译单个文件"""
    try:
        # 读取文件
        with open(input_filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        # 解析
        ast = parse(content)
        
        # 编译输出
        compile_to_file(ast, str(output_filepath), indent_size=4, use_tabs=False)
        
        return True, len(ast.statements)
    except Exception as e:
        return False, str(e)


def compile_directory(subdir: str):
    """编译指定子目录的所有文件
    
    Args:
        subdir: common 下的子目录名，如 'scripted_effects', 'buildings' 等
    """
    # 输入和输出路径
    input_path = STELLARIS_ROOT / "common" / subdir
    output_path = OUTPUT_ROOT / "common" / subdir
    
    print("=" * 60)
    print(f"编译目录: {subdir}")
    print("=" * 60)
    
    # 检查输入目录是否存在
    if not input_path.exists():
        print(f"错误: 目录不存在 {input_path}")
        return
    
    # 确保输出目录存在
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 获取所有 .txt 文件
    txt_files = sorted(input_path.glob("*.txt"))
    
    if not txt_files:
        print(f"警告: 在 {input_path} 中没有找到 .txt 文件")
        return
    
    print(f"\n找到 {len(txt_files)} 个文件")
    print(f"输入目录: {input_path}")
    print(f"输出目录: {output_path}")
    print()
    
    # 统计
    total_files = len(txt_files)
    success_count = 0
    fail_count = 0
    total_objects = 0
    errors = []
    
    # 逐个处理文件
    for i, filepath in enumerate(txt_files, 1):
        filename = filepath.name
        output_filepath = output_path / filename
        
        print(f"[{i}/{total_files}] {filename}...", end=' ')
        
        success, result = compile_file(filepath, output_filepath)
        
        if success:
            object_count = result
            total_objects += object_count
            success_count += 1
            print(f"OK ({object_count} objects)")
        else:
            fail_count += 1
            print(f"FAILED")
            errors.append((filename, result))
    
    # 输出统计
    print("\n" + "=" * 60)
    print("统计结果")
    print("=" * 60)
    print(f"总文件数: {total_files}")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"成功率: {success_count / total_files * 100:.1f}%")
    print(f"总对象数: {total_objects}")
    
    # 显示错误
    if errors:
        print("\n错误详情:")
        for filename, error in errors:
            print(f"  - {filename}: {error}")
    
    print(f"\n输出目录: {output_path}")
    print()


def main():
    """主函数"""
    # 可以编译的目录列表
    subdirs = [
        'scripted_effects',
        'scripted_triggers',
        'buildings',
        'districts',
        'scripted_variables',
        # 可以添加更多...
    ]
    
    print("=" * 60)
    print("Synthetipy 编译器测试")
    print("=" * 60)
    print()
    
    # 统计所有目录
    total_stats = defaultdict(int)
    
    for subdir in subdirs:
        compile_directory(subdir)
        print()


if __name__ == '__main__':
    main()
