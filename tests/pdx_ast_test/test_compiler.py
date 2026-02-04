"""
测试编译器 - 解析并重新编译 Stellaris scripted_effects 文件
输出到 test_output/common/scripted_effects 目录
"""

import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import parse, compile_to_file
from synthetipy.ast_nodes import ObjectNode

# Stellaris 游戏目录
STELLARIS_ROOT = Path("D:/SteamLibrary/steamapps/common/Stellaris")
SCRIPTED_EFFECTS_PATH = STELLARIS_ROOT / "common" / "scripted_effects"

# 输出目录
OUTPUT_ROOT = Path(__file__).parent.parent / "test_output"
OUTPUT_PATH = OUTPUT_ROOT / "common" / "scripted_effects"


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


def main():
    """主函数"""
    print("=" * 60)
    print("测试编译器 - Scripted Effects")
    print("=" * 60)
    
    # 确保输出目录存在
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    
    # 获取所有 .txt 文件
    txt_files = sorted(SCRIPTED_EFFECTS_PATH.glob("*.txt"))
    
    if not txt_files:
        print(f"错误: 在 {SCRIPTED_EFFECTS_PATH} 中没有找到 .txt 文件")
        return
    
    print(f"\n找到 {len(txt_files)} 个文件")
    print(f"输入目录: {SCRIPTED_EFFECTS_PATH}")
    print(f"输出目录: {OUTPUT_PATH}")
    print()
    
    # 统计
    total_files = len(txt_files)
    success_count = 0
    fail_count = 0
    total_objects = 0
    
    # 逐个处理文件
    for i, filepath in enumerate(txt_files, 1):
        filename = filepath.name
        output_filepath = OUTPUT_PATH / filename
        
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
            print(f"  Error: {result}")
    
    # 输出统计
    print("\n" + "=" * 60)
    print("统计结果")
    print("=" * 60)
    print(f"总文件数: {total_files}")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"成功率: {success_count / total_files * 100:.1f}%")
    print(f"总对象数: {total_objects}")
    print(f"输出目录: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
