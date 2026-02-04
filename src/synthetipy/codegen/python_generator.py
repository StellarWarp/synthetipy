"""
Python 代码生成器
将 PDX AST 转换为 Python DSL 代码
"""

from typing import List, Optional, Union
from ..ast_nodes import *
from .block_classifier import BlockClassifier
from .formatters import Formatter
from .trigger_generator import TriggerGenerator
from .effect_generator import EffectGenerator
from .value_generator import ValueGenerator

class PythonCodeGenerator:
    """AST → Python 代码生成器"""
    
    def __init__(self, file_path: str):
        """
        Initialize code generator
        
        Args:
            file_path: Source file path (used to determine object type)
        """
        self.file_path = file_path
        self.classifier = BlockClassifier(file_path)
        self.formatter = Formatter()
        self.trigger_gen = TriggerGenerator()
        self.effect_gen = EffectGenerator()
        self.value_gen = ValueGenerator()
        self.indent_level = 0
        self.lines: List[str] = []
        self.inline_script_counter = 0  # inline_script 计数器
    
    def generate(self, ast: DocumentNode) -> str:
        """
        生成完整的 Python 代码
        
        Args:
            ast: 文档 AST
        
        Returns:
            生成的 Python 代码
        """
        self.lines = []
        self.indent_level = 0
        
        # 导入语句
        self._add_imports()
        self._add_line("")
        
        # 生成每个顶层对象
        for stmt in ast.statements:
            if isinstance(stmt, ObjectNode):
                self._generate_object(stmt)
                self._add_line("")
        
        return '\n'.join(self.lines)
    
    def _add_imports(self):
        """添加导入语句"""
        self._add_line("from synthetipy import objects, scope")
        # TODO: 根据需要动态添加其他导入
    
    def _generate_object(self, obj: ObjectNode):
        """
        生成顶层对象
        
        Args:
            obj: 对象节点
        """
        # 获取对象名称
        name = self._get_identifier(obj.name)
        
        # 根据文件类型决定如何生成
        if self.classifier.file_type == 'trigger':
            # 生成 trigger 函数
            trigger_code = self.trigger_gen.generate(name, obj.body, 'scope')
            for line in trigger_code:
                self._add_line(line)
            return
        
        elif self.classifier.file_type == 'effect':
            # 生成 effect 函数
            effect_code = self.effect_gen.generate(name, obj.body, 'scope')
            for line in effect_code:
                self._add_line(line)
            return
        
        elif self.classifier.file_type == 'value':
            # 生成 value 函数
            value_code = self.value_gen.generate(name, obj.body, 'scope')
            for line in value_code:
                self._add_line(line)
            return
        
        # 普通对象，生成类
        if self.classifier.file_type == 'object':
            # 普通对象，需要装饰器
            category = self._guess_category_from_path()
            self._add_line(f"@objects.{category}")
        
        # 类定义
        self._add_line(f"class {name}:")
        self._indent()
        
        # 生成类体
        self.classifier.push_context(name)
        self._generate_block_body(obj.body)
        self.classifier.pop_context()
        
        self._dedent()
    
    def _generate_block_body(self, block: BlockNode):
        """
        生成块的内容
        
        Args:
            block: 块节点
        """
        if not block.statements:
            self._add_line("pass")
            return
        
        has_content = False
        
        for stmt in block.statements:
            if isinstance(stmt, PropertyNode):
                self._generate_property(stmt)
                has_content = True
            # TODO: 处理其他类型的语句
        
        if not has_content:
            self._add_line("pass")
    
    def _generate_property(self, prop: PropertyNode):
        """
        Generate property
        
        Args:
            prop: Property node
        """
        key = self.formatter.get_identifier(prop.key)
        value = prop.value
        
        # 特殊处理 inline_script
        if key == 'inline_script':
            self._generate_inline_script(prop)
            return
        
        # 如果值是块，需要判断类型
        if isinstance(value, BlockNode):
            block_type = self.classifier.classify_block(key, value)
            
            if block_type == 'trigger':
                # 生成 trigger 方法
                self._generate_trigger_method(key, value)
            elif block_type == 'effect':
                # 生成 effect 方法
                self._generate_effect_method(key, value)
            elif block_type == 'value':
                # 生成 value 方法
                self._generate_value_method(key, value)
            else:
                # 嵌套类
                self._generate_nested_class(key, value)
        
        elif isinstance(value, ListNode):
            # 列表
            formatted_list = self.formatter.format_list(value)
            self._add_line(f"{key} = {formatted_list}")
        
        else:
            # 简单属性
            formatted_value = self._format_literal(value)
            self._add_line(f"{key} = {formatted_value}")
    
    def _generate_nested_class(self, name: str, block: BlockNode):
        """
        生成嵌套类
        
        Args:
            name: 类名
            block: 块节点
        """
        self._add_line(f"class {name}:")
        self._indent()
        
        self.classifier.push_context(name)
        self._generate_block_body(block)
        self.classifier.pop_context()
        
        self._dedent()
    
    def _generate_trigger_method(self, name: str, block: BlockNode):
        """生成 trigger 方法"""
        method_lines = self.trigger_gen.generate(name, block, add_decorator=False)
        # 子生成器返回的代码已经包含缩进，需要加上当前缩进级别
        current_indent = "    " * self.indent_level
        for line in method_lines:
            if line:  # 非空行需要添加当前缩进
                self.lines.append(current_indent + line)
            else:  # 空行直接添加
                self.lines.append("")
    
    def _generate_effect_method(self, name: str, block: BlockNode):
        """生成 effect 方法"""
        method_lines = self.effect_gen.generate(name, block, add_decorator=False)
        current_indent = "    " * self.indent_level
        for line in method_lines:
            if line:
                self.lines.append(current_indent + line)
            else:
                self.lines.append("")
    
    def _generate_value_method(self, name: str, block: BlockNode):
        """生成 value 方法"""
        method_lines = self.value_gen.generate(name, block, add_decorator=False)
        current_indent = "    " * self.indent_level
        for line in method_lines:
            if line:
                self.lines.append(current_indent + line)
            else:
                self.lines.append("")
    
    def _generate_inline_script(self, prop: PropertyNode):
        """
        生成 inline_script 调用
        
        Args:
            prop: inline_script 属性节点
        """
        from ..inline_script_utils import extract_script_info, format_meta_inline_script
        
        script_path, params = extract_script_info(prop)
        if script_path:
            self.inline_script_counter += 1
            meta_call = format_meta_inline_script(script_path, params)
            self._add_line(f"inline_{self.inline_script_counter} = {meta_call}")
        else:
            self._add_line("# ERROR: Could not extract inline_script path")
    
    def _format_literal(self, value: ASTNode) -> str:
        """Format value (delegate to Formatter)"""
        return self.formatter.format_literal(value)
    
    def _format_list(self, lst: ListNode) -> str:
        """Format list (delegate to Formatter)"""
        return self.formatter.format_list(lst)
    
    def _get_identifier(self, node: Union[str, ASTNode]) -> str:
        """Get identifier (delegate to Formatter)"""
        return self.formatter.get_identifier(node)
    
    def _guess_category_from_path(self) -> str:
        """
        Guess object category from file path
        
        Returns:
            Category name (e.g. 'building', 'technology')
        """
        path = self.file_path.replace('\\', '/')
        
        if 'buildings' in path:
            return 'building'
        elif 'districts' in path:
            return 'district'
        elif 'technolog' in path:  # technology 或 technologies
            return 'technology'
        elif 'edicts' in path:
            return 'edict'
        elif 'decisions' in path:
            return 'decision'
        elif 'traits' in path:
            return 'trait'
        else:
            return 'object'  # 通用
    
    # ============================================
    # 辅助方法
    # ============================================
    
    def _add_line(self, line: str = ""):
        """
        Add a line (with auto-indent)
        
        Args:
            line: Code line
        """
        if line:
            indent = "    " * self.indent_level
            self.lines.append(indent + line)
        else:
            self.lines.append("")
    
    def _indent(self):
        """增加缩进"""
        self.indent_level += 1
    
    def _dedent(self):
        """减少缩进"""
        if self.indent_level > 0:
            self.indent_level -= 1


def generate_python_code(ast: DocumentNode, file_path: str) -> str:
    """
    便捷函数：从 AST 生成 Python 代码
    
    Args:
        ast: 文档 AST
        file_path: 源文件路径
    
    Returns:
        生成的 Python 代码
    """
    generator = PythonCodeGenerator(file_path)
    return generator.generate(ast)
