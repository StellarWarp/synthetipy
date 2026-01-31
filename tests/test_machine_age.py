"""测试 02_machine_age_effects.txt 解析问题"""
import sys
from pathlib import Path
# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from synthetipy import parse

def main():
    path = 'D:/SteamLibrary/steamapps/common/Stellaris/common/scripted_effects/astral_planes_effects.txt'
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"文件大小: {len(content)} 字符")
        print(f"前 500 字符:\n{content[:500]}")
        print("\n开始解析...")
        
        ast = parse(content)
        
        print(f"\n解析成功！")
        print(f"对象数: {len(ast.statements)}")
        for i, obj in enumerate(ast.statements[:10], 1):
            print(f"  {i}. {obj.name}")
            
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n解析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
