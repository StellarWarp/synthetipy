"""
PDXLang Patcher - Inline Script 解析器
处理 Stellaris 的 inline_script 引用和展开
"""

import re
from pathlib import Path
from typing import Dict, Optional, Union
from .parser import parse
from .ast_nodes import (
    ASTNode, DocumentNode, ObjectNode, PropertyNode, BlockNode, ValueNode,
    ComparisonNode, ConditionNode
)


class InlineScriptResolver:
    """Inline Script 解析和展开器"""
    
    def __init__(self, game_root: Union[str, Path]):
        """
        初始化解析器
        
        Args:
            game_root: Stellaris 游戏根目录
        """
        self.game_root = Path(game_root)
        self.scripts_root = self.game_root / "common" / "inline_scripts"
        self.scripts_cache: Dict[str, BlockNode] = {}  # 缓存已加载的脚本
        
    def load_script(self, script_path: str) -> Optional[BlockNode]:
        """
        加载 inline_script 文件
        
        Args:
            script_path: 脚本路径，例如 "jobs/roboticist_add" 或 "paragon/num_traits_with_modifier"
            
        Returns:
            解析后的代码块，如果文件不存在则返回 None
        """
        # 检查缓存
        if script_path in self.scripts_cache:
            return self.scripts_cache[script_path]
        
        # 构建文件路径
        script_file = self.scripts_root / f"{script_path}.txt"
        
        if not script_file.exists():
            print(f"Warning: Inline script not found: {script_path}")
            return None
        
        try:
            # 读取文件
            with open(script_file, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            
            # 解析文件（inline_script 文件没有顶层对象声明，直接是内容）
            # 我们需要包装一下让 parser 能解析
            wrapped_content = f"_inline_wrapper = {{\n{content}\n}}"
            ast = parse(wrapped_content)
            
            # 提取内容
            if ast.statements and isinstance(ast.statements[0], ObjectNode):
                block = ast.statements[0].body
                self.scripts_cache[script_path] = block
                return block
            
            return None
            
        except Exception as e:
            print(f"Error loading inline script {script_path}: {e}")
            return None
    
    def resolve_inline_script_property(
        self, 
        inline_prop: PropertyNode,
        params: Optional[Dict[str, str]] = None
    ) -> Optional[BlockNode]:
        """
        解析 inline_script 属性，返回展开后的代码块
        
        Args:
            inline_prop: inline_script 属性节点
            params: 额外的参数（如果 inline_prop 已经包含参数，会合并）
            
        Returns:
            展开后的代码块，参数已替换
        """
        if inline_prop.key != 'inline_script':
            return None
        
        script_path = None
        script_params = params or {}
        
        # 解析 inline_script 的值
        if isinstance(inline_prop.value, ValueNode):
            # 简单形式: inline_script = jobs/roboticist_add
            script_path = inline_prop.value.value
            
        elif isinstance(inline_prop.value, BlockNode):
            # 带参数形式: inline_script = { script = ... PARAM = value }
            script_prop = inline_prop.value.get_property('script')
            if script_prop and isinstance(script_prop.value, ValueNode):
                script_path = script_prop.value.value
            
            # 提取参数
            for stmt in inline_prop.value.statements:
                if isinstance(stmt, PropertyNode) and stmt.key != 'script':
                    # 参数值
                    if isinstance(stmt.value, ValueNode):
                        script_params[stmt.key] = str(stmt.value.value)
                    else:
                        # 复杂值暂时转为字符串
                        script_params[stmt.key] = str(stmt.value)
        
        if not script_path:
            return None
        
        # 加载脚本
        script_block = self.load_script(script_path)
        if not script_block:
            return None
        
        # 替换参数
        if script_params:
            script_block = self._replace_parameters(script_block, script_params)
        
        return script_block
    
    def _replace_parameters(self, block: BlockNode, params: Dict[str, str]) -> BlockNode:
        """
        替换代码块中的参数占位符 $PARAM$
        
        Args:
            block: 原始代码块
            params: 参数字典
            
        Returns:
            替换后的新代码块
        """
        # 深拷贝并替换
        new_statements = []
        
        for stmt in block.statements:
            new_stmt = self._replace_in_node(stmt, params)
            if new_stmt:
                new_statements.append(new_stmt)
        
        return BlockNode(new_statements)
    
    def _replace_in_node(self, node: ASTNode, params: Dict[str, str]) -> ASTNode:
        """递归替换节点中的参数"""
        if isinstance(node, PropertyNode):
            # 替换 key
            new_key = self._replace_string(node.key, params)
            # 递归替换 value
            new_value = self._replace_in_node(node.value, params)
            new_prop = PropertyNode(new_key, new_value)
            new_prop.line = node.line
            new_prop.column = node.column
            return new_prop
            
        elif isinstance(node, ValueNode):
            # 替换值
            new_val = self._replace_string(str(node.value), params)
            new_value = ValueNode(new_val, node.value_type)
            new_value.line = node.line
            new_value.column = node.column
            return new_value
            
        elif isinstance(node, BlockNode):
            new_statements = [
                self._replace_in_node(stmt, params) 
                for stmt in node.statements
            ]
            new_block = BlockNode(new_statements)
            new_block.line = node.line
            new_block.column = node.column
            return new_block
            
        elif isinstance(node, ComparisonNode):
            new_left = self._replace_string(node.left, params)
            new_right = self._replace_in_node(node.right, params)
            new_comp = ComparisonNode(new_left, node.operator, new_right)
            new_comp.line = node.line
            new_comp.column = node.column
            return new_comp
            
        elif isinstance(node, ConditionNode):
            new_body = self._replace_in_node(node.body, params)
            new_cond = ConditionNode(node.operator, new_body)
            new_cond.line = node.line
            new_cond.column = node.column
            return new_cond
            
        else:
            # 其他类型暂时原样返回
            return node
    
    def _replace_string(self, text: str, params: Dict[str, str]) -> str:
        """替换字符串中的 $PARAM$ 占位符"""
        result = text
        for key, value in params.items():
            # 替换 $KEY$ 格式
            result = result.replace(f"${key}$", value)
        return result
    
    def unpack_inline_scripts(self, node: ASTNode, recursive: bool = True) -> ASTNode:
        """
        展开节点中的所有 inline_script 引用
        
        Args:
            node: 要处理的 AST 节点
            recursive: 是否递归展开嵌套的 inline_script
            
        Returns:
            展开后的新节点
        """
        if isinstance(node, ObjectNode):
            # 处理对象的 body
            new_body = self.unpack_inline_scripts(node.body, recursive)
            new_obj = ObjectNode(node.name, new_body)
            new_obj.line = node.line
            new_obj.column = node.column
            return new_obj
            
        elif isinstance(node, BlockNode):
            new_statements = []
            
            for stmt in node.statements:
                if isinstance(stmt, PropertyNode) and stmt.key == 'inline_script':
                    # 展开 inline_script
                    expanded = self.resolve_inline_script_property(stmt)
                    
                    if expanded:
                        # 如果递归，继续展开嵌套的 inline_script
                        if recursive:
                            expanded = self.unpack_inline_scripts(expanded, recursive)
                        
                        # 添加展开后的语句
                        new_statements.extend(expanded.statements)
                    else:
                        # 如果无法展开，保留原样
                        new_statements.append(stmt)
                else:
                    # 递归处理其他语句
                    new_stmt = self.unpack_inline_scripts(stmt, recursive)
                    new_statements.append(new_stmt)
            
            new_block = BlockNode(new_statements)
            new_block.line = node.line
            new_block.column = node.column
            return new_block
            
        elif isinstance(node, PropertyNode):
            # 递归处理属性的值
            new_value = self.unpack_inline_scripts(node.value, recursive)
            new_prop = PropertyNode(node.key, new_value)
            new_prop.line = node.line
            new_prop.column = node.column
            return new_prop
            
        elif isinstance(node, ConditionNode):
            new_body = self.unpack_inline_scripts(node.body, recursive)
            new_cond = ConditionNode(node.operator, new_body)
            new_cond.line = node.line
            new_cond.column = node.column
            return new_cond
            
        elif isinstance(node, DocumentNode):
            new_statements = [
                self.unpack_inline_scripts(stmt, recursive) 
                for stmt in node.statements
            ]
            return DocumentNode(new_statements)
            
        else:
            # 其他类型原样返回
            return node
    
    def extract_inline_objects(self, script_path: str) -> list:
        """
        提取 inline_script 中定义的对象
        
        用于处理对象级别的 inline_script
        
        Args:
            script_path: 脚本路径
            
        Returns:
            对象列表
        """
        block = self.load_script(script_path)
        if not block:
            return []
        
        # 查找所有顶层定义的对象
        # inline_script 中的对象级定义通常直接在顶层
        objects = []
        
        for stmt in block.statements:
            # 查找形如 object_name = { ... } 的模式
            if isinstance(stmt, PropertyNode):
                # 检查值是否是 Block
                if isinstance(stmt.value, BlockNode):
                    # 转换为 Object
                    obj = ObjectNode(stmt.key, stmt.value)
                    obj.line = stmt.line
                    obj.column = stmt.column
                    objects.append(obj)
        
        return objects


# 便捷函数

def create_resolver(game_root: Union[str, Path]) -> InlineScriptResolver:
    """创建 inline script 解析器"""
    return InlineScriptResolver(game_root)


# 测试代码
if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    # 添加父目录到 sys.path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    print("=" * 60)
    print("测试 Inline Script Resolver")
    print("=" * 60)
    
    # 创建解析器
    game_root = Path("D:/SteamLibrary/steamapps/common/Stellaris")
    
    if not game_root.exists():
        print(f"\n错误: 游戏目录不存在: {game_root}")
        sys.exit(1)
    
    resolver = InlineScriptResolver(game_root)
    
    # 测试加载脚本
    print("\n测试 1: 加载 inline_script")
    print("-" * 60)
    
    script = resolver.load_script("jobs/roboticist_add")
    if script:
        print(f"✓ 成功加载 jobs/roboticist_add")
        print(f"  语句数: {len(script.statements)}")
    else:
        print("✗ 加载失败")
    
    # 测试参数替换
    print("\n测试 2: 参数替换")
    print("-" * 60)
    
    if script:
        params = {"AMOUNT": "5"}
        replaced = resolver._replace_parameters(script, params)
        print(f"✓ 参数替换完成")
        print(f"  原始语句数: {len(script.statements)}")
        print(f"  替换后语句数: {len(replaced.statements)}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
