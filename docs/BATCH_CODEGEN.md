# 批量代码生成器使用指南

## 配置环境变量

建议使用环境变量设置游戏目录：

```bash
# Windows
set STELLARIS_GAME_DIR=D:\SteamLibrary\steamapps\common\Stellaris

# Linux/Mac
export STELLARIS_GAME_DIR=/path/to/Stellaris
```

或者在 Python 代码中设置：

```python
from src.synthetipy.config import set_game_dir
set_game_dir("D:/SteamLibrary/steamapps/common/Stellaris")
```

## 使用方法

### 1. 命令行方式

```bash
# 使用默认配置文件
python -m src.synthetipy.codegen.batch_generator

# 指定配置文件
python -m src.synthetipy.codegen.batch_generator codegen_config.yaml

# 命令行覆盖游戏目录
python -m src.synthetipy.codegen.batch_generator --game-dir "D:/Games/Stellaris"
```

### 2. Python 代码方式

```python
from src.synthetipy.codegen.batch_generator import generate_from_config

# 使用配置文件生成
generate_from_config('codegen_config.yaml')
```

### 3. 高级用法

```python
from src.synthetipy.codegen.batch_generator import BatchCodeGenerator, CodeGenConfig

# 加载配置
config = CodeGenConfig.from_yaml('codegen_config.yaml')

# 创建生成器
generator = BatchCodeGenerator(config)

# 运行生成
generator.generate_all()

# 查看统计信息
print(f"成功: {generator.stats['success']}")
print(f"失败: {generator.stats['failed']}")
```

## 配置文件说明

### game_root 配置

支持三种方式：

```yaml
# 方式 1: 使用环境变量（推荐）
game_root: "${STELLARIS_GAME_DIR}"

# 方式 2: 直接指定路径
game_root: "D:/SteamLibrary/steamapps/common/Stellaris"

# 方式 3: 使用 null（使用全局配置）
game_root: null
```

### 完整配置示例

```yaml
# 游戏根目录
game_root: "${STELLARIS_GAME_DIR}"

# 输出目录
output_root: "generated_python"

# 要转换的路径
include_paths:
  - "common/buildings"
  - "common/scripted_triggers"
  - "common/scripted_effects"
  - "common/scripted_variables"

# 排除模式
exclude_patterns:
  - "**/README.txt"
  - "**/*.md"

# 生成选项
generation_options:
  generate_type_hints: true
  generate_docstrings: true
  add_source_comments: true
  overwrite_existing: true
  continue_on_error: true

# 日志配置
logging:
  level: "INFO"
  log_file: "codegen.log"
  console_output: true
```

## 目录结构映射

生成的 Python 文件会保持相对路径结构：

```
游戏目录/common/buildings/00_capital_buildings.txt
  -> 输出目录/common/buildings/00_capital_buildings.py

游戏目录/common/scripted_triggers/00_scripted_triggers.txt
  -> 输出目录/common/scripted_triggers/00_scripted_triggers.py
```

## 测试

运行测试（使用本地测试文件）：

```bash
python test_batch_codegen.py
```

这会处理 `test_game_files/` 中的文件并输出到 `test_python_output/`。
