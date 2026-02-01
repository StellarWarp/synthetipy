"""
批量代码生成器

扫描游戏文件夹，将 PDX 脚本批量转换为 Python 代码
保持目录结构映射
"""

import os
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from ..parser import parse
from ..config import get_config
from .python_generator import PythonCodeGenerator


@dataclass
class CodeGenConfig:
    """代码生成配置"""
    game_root: Optional[Path]  # None 表示使用环境变量
    output_root: Path
    include_paths: List[str]
    exclude_patterns: List[str]
    generation_options: Dict
    logging_config: Dict
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'CodeGenConfig':
        """从 YAML 文件加载配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # game_root 支持三种方式：
        # 1. 直接指定路径
        # 2. "${STELLARIS_ROOT}" - 使用环境变量
        # 3. null/None - 使用 config.game_dir
        game_root_str = data.get('game_root')
        if game_root_str and game_root_str.startswith('${') and game_root_str.endswith('}'):
            # 环境变量引用
            env_var = game_root_str[2:-1]
            env_value = os.environ.get(env_var)
            if not env_value:
                raise ValueError(f"环境变量未设置: {env_var}")
            game_root = Path(env_value)
        elif game_root_str:
            # 直接路径
            game_root = Path(game_root_str)
        else:
            # 使用全局配置
            game_root = None
        
        return cls(
            game_root=game_root,
            output_root=Path(data['output_root']),
            include_paths=data['include_paths'],
            exclude_patterns=data.get('exclude_patterns', []),
            generation_options=data.get('generation_options', {}),
            logging_config=data.get('logging', {})
        )
    
    def get_game_root(self) -> Path:
        """获取实际的游戏根目录"""
        if self.game_root:
            return self.game_root
        
        # 使用全局配置
        global_config = get_config()
        if not global_config.game_dir:
            raise ValueError(
                "游戏目录未配置。请在配置文件中指定 game_root，"
                "或设置环境变量 STELLARIS_GAME_DIR"
            )
        return global_config.game_dir


class BatchCodeGenerator:
    """批量代码生成器"""
    
    def __init__(self, config: CodeGenConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.stats = {
            'total_files': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []  # 记录错误详情
        }
    
    def _setup_logging(self) -> logging.Logger:
        """配置日志系统"""
        logger = logging.getLogger('BatchCodeGenerator')
        
        # 清除已有的 handler
        logger.handlers.clear()
        
        level = self.config.logging_config.get('level', 'INFO')
        logger.setLevel(getattr(logging, level))
        
        # 控制台输出
        if self.config.logging_config.get('console_output', True):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                logging.Formatter('%(levelname)s: %(message)s')
            )
            logger.addHandler(console_handler)
        
        # 文件输出
        log_file = self.config.logging_config.get('log_file')
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            logger.addHandler(file_handler)
        
        return logger
    
    def generate_all(self):
        """批量生成所有文件"""
        try:
            game_root = self.config.get_game_root()
        except ValueError as e:
            self.logger.error(str(e))
            return
        
        self.logger.info("=" * 70)
        self.logger.info("开始批量代码生成")
        self.logger.info("=" * 70)
        self.logger.info(f"游戏根目录: {game_root}")
        self.logger.info(f"输出目录: {self.config.output_root}")
        self.logger.info("")
        
        # 收集所有需要处理的文件
        all_files = self._collect_files(game_root)
        self.stats['total_files'] = len(all_files)
        
        if self.stats['total_files'] == 0:
            self.logger.warning("未找到需要处理的文件")
            return
        
        self.logger.info(f"找到 {len(all_files)} 个文件需要处理\n")
        
        # 创建输出根目录
        output_path = Path(self.config.output_root)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 处理每个文件
        for pdx_file in all_files:
            self._process_file(pdx_file, game_root)
        
        # 输出统计信息
        self._print_statistics()
    
    def _collect_files(self, game_root: str) -> List[Path]:
        """收集所有需要处理的 PDX 文件"""
        all_files = []
        game_root_path = Path(game_root)
        
        for include_path in self.config.include_paths:
            full_path = game_root_path / include_path
            
            if not full_path.exists():
                self.logger.warning(f"路径不存在，跳过: {full_path}")
                continue
            
            # 递归查找所有 .txt 文件
            if full_path.is_dir():
                for txt_file in full_path.rglob('*.txt'):
                    if not self._is_excluded(txt_file, game_root):
                        all_files.append(txt_file)
            elif full_path.is_file() and full_path.suffix == '.txt':
                if not self._is_excluded(full_path, game_root):
                    all_files.append(full_path)
        
        return sorted(all_files)
    
    def _is_excluded(self, file_path: Path, game_root: Path) -> bool:
        """检查文件是否应该被排除"""
        try:
            rel_path = file_path.relative_to(game_root)
            for pattern in self.config.exclude_patterns:
                if rel_path.match(pattern):
                    return True
        except ValueError:
            pass
        
        return False
    
    def _process_file(self, pdx_file: Path, game_root: Path):
        """处理单个 PDX 文件"""
        # 计算相对路径
        try:
            rel_path = pdx_file.relative_to(game_root)
        except ValueError:
            self.logger.error(f"文件不在游戏根目录下: {pdx_file}")
            self.stats['failed'] += 1
            return
        
        # 计算输出路径（.txt -> .py）
        output_root_path = Path(self.config.output_root)
        output_file = output_root_path / rel_path.with_suffix('.py')
        
        # 检查是否需要覆盖
        if output_file.exists() and not self.config.generation_options.get('overwrite_existing', True):
            self.logger.info(f"跳过已存在的文件: {output_file}")
            self.stats['skipped'] += 1
            return
        
        self.logger.info(f"处理: {rel_path}")
        
        try:
            # 读取并解析 PDX 文件
            with open(pdx_file, 'r', encoding='utf-8', errors='ignore') as f:
                pdx_code = f.read()
            
            # 解析 AST
            ast = parse(pdx_code)
            
            # 生成 Python 代码（传递相对路径用于类型推断）
            generator = PythonCodeGenerator(str(rel_path))
            python_code = generator.generate(ast)
            
            # 添加来源注释
            if self.config.generation_options.get('add_source_comments', True):
                header = self._generate_header(pdx_file, rel_path)
                python_code = header + python_code
            
            # 创建输出目录
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            encoding = self.config.generation_options.get('file_encoding', 'utf-8')
            with open(output_file, 'w', encoding=encoding) as f:
                f.write(python_code)
            
            self.logger.debug(f"  -> {output_file}")
            self.stats['success'] += 1
            
        except Exception as e:
            error_msg = f"{rel_path}: {e}"
            self.logger.error(f"处理失败: {error_msg}")
            self.stats['failed'] += 1
            self.stats['errors'].append(error_msg)
            
            if not self.config.generation_options.get('continue_on_error', True):
                raise
    
    def _generate_header(self, source_file: Path, rel_path: Path) -> str:
        """生成文件头部注释"""
        lines = [
            '"""',
            'Auto-generated from Stellaris game files',
            f'Source: {rel_path}',
            '',
            'DO NOT EDIT THIS FILE MANUALLY',
            'Changes will be overwritten on next generation',
            '"""',
            '',
            ''
        ]
        return '\n'.join(lines)
    
    def _print_statistics(self):
        """输出统计信息"""
        self.logger.info("")
        self.logger.info("=" * 70)
        self.logger.info("代码生成完成")
        self.logger.info("=" * 70)
        self.logger.info(f"总文件数:   {self.stats['total_files']}")
        self.logger.info(f"成功:       {self.stats['success']}")
        self.logger.info(f"失败:       {self.stats['failed']}")
        self.logger.info(f"跳过:       {self.stats['skipped']}")
        
        if self.stats['failed'] > 0:
            self.logger.warning(f"\n有 {self.stats['failed']} 个文件处理失败")
            if self.stats['errors']:
                self.logger.warning("错误详情:")
                for error in self.stats['errors'][:10]:  # 只显示前 10 个
                    self.logger.warning(f"  - {error}")
                if len(self.stats['errors']) > 10:
                    self.logger.warning(f"  ... 还有 {len(self.stats['errors']) - 10} 个错误")
        else:
            self.logger.info("\n✓ 所有文件处理成功!")


def generate_from_config(config_path: str):
    """
    从配置文件生成代码（便捷函数）
    
    Args:
        config_path: YAML 配置文件路径
    """
    config = CodeGenConfig.from_yaml(config_path)
    generator = BatchCodeGenerator(config)
    generator.generate_all()
