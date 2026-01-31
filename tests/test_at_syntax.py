"""测试 @ 符号的各种用法"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from synthetipy import parse

def test_at_in_identifier():
    """测试标识符中的 @ 符号"""
    code = """
    event_target:cyberspecies@species = {
        save_event_target_as = cyberspecies_current
    }
    """
    ast = parse(code)
    print("✓ 解析成功: event_target:cyberspecies@species")
    print(f"  对象数: {len(ast.statements)}")

def test_inline_expression():
    """测试内联运算 @[ ... ]"""
    code = """
    test_effect = {
        planet_stability < @[ stabilitylevel2 + 10 ]
    }
    """
    try:
        ast = parse(code)
        print("✓ 解析成功: @[ stabilitylevel2 + 10 ]")
        print(f"  对象数: {len(ast.statements)}")
    except Exception as e:
        print(f"✗ 内联运算解析失败: {e}")

def test_variable_reference():
    """测试普通变量引用"""
    code = """
    @stabilitylevel2 = 50
    test_effect = {
        value = @stabilitylevel2
    }
    """
    ast = parse(code)
    print("✓ 解析成功: @stabilitylevel2 变量引用")
    print(f"  对象数: {len(ast.statements)}")

if __name__ == '__main__':
    print("测试 @ 符号的各种用法\n")
    test_at_in_identifier()
    test_inline_expression()
    test_variable_reference()
