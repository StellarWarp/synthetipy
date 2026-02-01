"""
代码生成命令行工具

使用方法:
    python -m src.synthetipy.codegen.batch_generator config.yaml
    
或者:
    from src.synthetipy.codegen.batch_generator import generate_from_config
    generate_from_config('config.yaml')
"""

import sys
import argparse
from pathlib import Path

from .batch_generator import generate_from_config


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='批量将 PDX 脚本转换为 Python 代码'
    )
    parser.add_argument(
        'config',
        help='YAML 配置文件路径',
        default='codegen_config.yaml',
        nargs='?'
    )
    parser.add_argument(
        '--game-dir',
        help='游戏根目录（覆盖配置文件和环境变量）',
        type=str
    )
    parser.add_argument(
        '--output-dir',
        help='输出目录（覆盖配置文件）',
        type=str
    )
    
    args = parser.parse_args()
    
    # 检查配置文件
    if not Path(args.config).exists():
        print(f"错误: 配置文件不存在: {args.config}")
        sys.exit(1)
    
    # 如果指定了命令行参数，临时设置环境变量
    import os
    if args.game_dir:
        os.environ['STELLARIS_GAME_DIR'] = args.game_dir
    
    # 运行代码生成
    try:
        generate_from_config(args.config)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
