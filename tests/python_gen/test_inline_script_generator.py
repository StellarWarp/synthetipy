"""
测试 InlineScript 生成器
"""

import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy.config import config, set_game_dir
from synthetipy.codegen.inline_script_generator import (
    InlineScriptGenerator,
    InlineScriptContext,
)


def test_config():
    """测试配置模块"""
    print("=" * 60)
    print("测试配置模块")
    print("=" * 60)
    
    # 检查配置状态
    errors = config.validate()
    if errors:
        print("配置验证失败:")
        for err in errors:
            print(f"  - {err}")
        print("\n提示: 设置环境变量 STELLARIS_GAME_DIR 指向游戏目录")
        print("例如: set STELLARIS_GAME_DIR=D:\\SteamLibrary\\steamapps\\common\\Stellaris")
        return False
    
    print(f"游戏目录: {config.game_dir}")
    print(f"inline_scripts 目录: {config.inline_scripts_dir}")
    
    # 检查 inline_scripts 目录是否存在
    if config.inline_scripts_dir and config.inline_scripts_dir.exists():
        # 列出一些脚本
        scripts = list(config.inline_scripts_dir.rglob("*.txt"))[:5]
        print(f"\n找到 {len(list(config.inline_scripts_dir.rglob('*.txt')))} 个脚本文件")
        print("示例脚本:")
        for script in scripts:
            rel_path = script.relative_to(config.inline_scripts_dir)
            print(f"  - {rel_path}")
    
    return True


def test_inline_script_generator():
    """测试 InlineScript 生成器"""
    print("\n" + "=" * 60)
    print("测试 InlineScript 生成器")
    print("=" * 60)
    
    if not config.game_dir:
        print("跳过: 游戏目录未设置")
        return
    
    try:
        generator = InlineScriptGenerator()
    except ValueError as e:
        print(f"无法创建生成器: {e}")
        return
    
    # 测试常见的 inline_script
    test_scripts = [
        "buildings/clone_army_vat_output",
        "ai/ai_base",
        "buildings/on_all_capital_buildings",
    ]
    
    for script_path in test_scripts:
        print(f"\n--- 测试脚本: {script_path} ---")
        
        # 检查脚本是否存在
        full_path = config.get_inline_script_path(script_path)
        if full_path is None:
            print(f"  脚本不存在，跳过")
            continue
        
        print(f"  文件路径: {full_path}")
        
        # 在 effect 上下文中生成
        print("\n  【Effect 上下文生成】")
        try:
            lines = generator.generate_from_path(
                script_path=script_path,
                context=InlineScriptContext.EFFECT,
                parameters={"AMOUNT": 10},
                scope_var="scope"
            )
            for line in lines[:10]:  # 只显示前10行
                print(f"    {line}")
            if len(lines) > 10:
                print(f"    ... ({len(lines) - 10} more lines)")
        except Exception as e:
            print(f"  生成失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 在 trigger 上下文中生成
        print("\n  【Trigger 上下文生成】")
        try:
            lines = generator.generate_from_path(
                script_path=script_path,
                context=InlineScriptContext.TRIGGER,
                parameters={"AMOUNT": 10},
                scope_var="scope"
            )
            for line in lines[:5]:
                print(f"    {line}")
        except Exception as e:
            print(f"  生成失败: {e}")


def test_generate_from_node():
    """测试从 AST 节点生成"""
    print("\n" + "=" * 60)
    print("测试从 AST 节点生成")
    print("=" * 60)
    
    if not config.game_dir:
        print("跳过: 游戏目录未设置")
        return
    
    from synthetipy.parsing.lexer import Lexer
    from synthetipy import Parser
    from synthetipy.ast_nodes import ObjectNode
    
    # 测试代码
    pdx_code = """
test_effect = {
    inline_script = buildings/clone_army_vat_output
}
"""
    
    try:
        lexer = Lexer(pdx_code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        if ast.statements and isinstance(ast.statements[0], ObjectNode):
            obj = ast.statements[0]
            for stmt in obj.body.statements:
                if hasattr(stmt, 'key') and str(stmt.key) == 'inline_script':
                    print(f"找到 inline_script 节点")
                    
                    generator = InlineScriptGenerator()
                    lines = generator.generate_from_node(
                        node=stmt,
                        context=InlineScriptContext.EFFECT,
                        scope_var="planet"
                    )
                    
                    print("生成的代码:")
                    for line in lines[:15]:
                        print(f"  {line}")
                    if len(lines) > 15:
                        print(f"  ... ({len(lines) - 15} more lines)")
                    break
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主测试入口"""
    print("\n" + "=" * 70)
    print(" " * 15 + "INLINE SCRIPT GENERATOR 测试套件")
    print("=" * 70)
    
    # 测试配置
    config_ok = test_config()
    
    # 如果配置有效，测试生成器
    if config_ok:
        test_inline_script_generator()
        test_generate_from_node()
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == '__main__':
    main()
