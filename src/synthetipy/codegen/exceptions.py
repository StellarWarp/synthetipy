"""
代码生成异常类
"""


class CodeGenerationError(Exception):
    """代码生成错误基类"""
    pass


class UnsupportedFeatureError(CodeGenerationError):
    """不支持的特性错误"""
    pass


class EmptyBlockError(CodeGenerationError):
    """空块错误"""
    pass


class MissingConditionError(CodeGenerationError):
    """缺失条件错误"""
    pass


class InvalidStructureError(CodeGenerationError):
    """无效结构错误"""
    pass
