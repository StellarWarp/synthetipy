import os
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from collections import defaultdict
import logging

from synthetipy.parser import parse_file
from synthetipy.compiler import compile_to_file
from synthetipy.ast_nodes_basic import ASTNode, DocumentNode, ObjectNode
from synthetipy.script_merger.merge import three_way_merge

logger = logging.getLogger(__name__)

FOLDER_EXCLUDE = 'exclude'
FOLDER_ORDERED = 'ordered'
FOLDER_UNORDERED = 'unordered'



EXAMPLE_CONFIG = {
    'common': {
        # excluded folders
        'inline_scripts': FOLDER_EXCLUDE,
        "scripted_effects": FOLDER_EXCLUDE,
        "scripted_triggers": FOLDER_EXCLUDE,
        "script_values": FOLDER_EXCLUDE,
        "on_actions": FOLDER_EXCLUDE,
        "economic_plans": FOLDER_EXCLUDE,
        # ordered folders
        "colony_automation": FOLDER_ORDERED,
        "colony_automation_exceptions": FOLDER_ORDERED,
        # default: unordered merge (default behavior)
        "buildings": FOLDER_UNORDERED
    },
    # 'event': {}
}

class ObjectVersion:
    def __init__(self, source_name: str, node: ObjectNode, filename: str, doc_node: DocumentNode):
        self.source_name = source_name
        self.node = node
        self.filename = filename
        self.doc_node = doc_node # 需要保留整棵树的引用，以便 Ordered 模式下做模板
        

class BatchMerger:
    def __init__(self, game_root: Path, mod_roots: List[Path], output_root: Path, folder_config: Dict):
        # 统一把 game_root 作为来源列表的第一个
        self.sources = [("vanilla", Path(game_root))] + \
                       [(f"mod_{i+1}", Path(p)) for i, p in enumerate(mod_roots)]
        self.output_root = Path(output_root)
        self.folder_config = folder_config
        # 索引: logical_file_path -> object_key -> List[ObjectVersion]
        self.object_registry: Dict[str, Dict[str, List[ObjectVersion]]] = defaultdict(lambda: defaultdict(list))
        
        # 记录哪些文件其实只需要去原版里找（lazy loading）
        # 优化：我们可以在第一遍只扫 Mods，把需要去原版找的文件记录下来
        # 这里为了演示逻辑简洁，假设是先扫 Mods，再按需扫 Vanilla

    def run(self):
        # 1. Scan Mods (Skipping index 0 which is vanilla for now)
        logger.info("Scanning mods...")
        for i in range(1, len(self.sources)):
            name, path = self.sources[i]
            self._scan_source(path, name, is_vanilla=False)

        # 2. Identify Potential Conflicts & Load Vanilla
        # 找出那些至少有两个 Mod 修改的对象，或者虽然只有一个 Mod 改了但可能覆盖了原版（这个不用管，游戏自带覆盖）
        # 你的条件：至少出现 3 次。
        # 但现在还没加载 vanilla，所以我们看：如果有 >= 2 个 Mod 涉及该对象，必须加载 Vanilla 看看是否存在。
        # 如果只有 1 个 Mod 涉及，不需要合并，直接由该 Mod 覆盖 Vanilla（或者就是新增）。
        
        files_needing_vanilla = set()
        for fpath, file_objs in self.object_registry.items():
            for key, versions in file_objs.items():
                if len(versions) >= 2:
                    folder = Path(fpath).name
                    files_needing_vanilla.add(folder)
        
        logger.info(f"Loading base game files for {len(files_needing_vanilla)} conflict candidates...")
        # Load Vanilla selectively
        vanilla_name, vanilla_path = self.sources[0]
        self._scan_source(vanilla_path, vanilla_name, is_vanilla=True, whitelist_folder=files_needing_vanilla)
        
        # 3. Execute Merge
        logger.info("Executing merges...")
        self._execute_merges()
        
    def _get_folder_type(self, logical_path: str) -> str:
        folder = Path(logical_path).name
        for primary_folder, folder_config in self.folder_config.items():
            if folder in folder_config:
                return folder_config[folder]
        return FOLDER_UNORDERED # default
    
    def _scan_source(self, root: Path, source_name: str, is_vanilla: bool,
                     whitelist_folder: Optional[set] = None):
        """通用扫描函数"""
        # 如果提供了 whitelist，只扫描列表里的文件（用于 Vanilla 的按需加载）
        # 如果没提供，扫描所有 TXT
        for primary_folder, folder_config in self.folder_config.items():
                # Iterate folder in root/primary_folder
                folder_path: Path = root / primary_folder
                for folder in folder_path.iterdir():
                    if not folder.is_dir():
                        continue
                    if folder.name in folder_config:
                        if folder_config[folder.name] == FOLDER_EXCLUDE:
                            continue
                    if whitelist_folder and folder.name not in whitelist_folder:
                        continue       
                    for file in folder.iterdir():
                        if not file.name.endswith(".txt"): continue
                        full = file
                        rel_logical_path = folder.relative_to(root).as_posix() # e.g. "scripted_effects"
                        self._parse_and_extract(full, rel_logical_path, source_name)

    def _parse_and_extract(self, full_path: Path, rel_logical_path: str, source_name: str):
        ast = parse_file(full_path)
        top_objs = self._extract_objects(ast)
        file_name = full_path.name
        for key, node in top_objs.items():
            # 对于 Vanilla，我们要把它插入到列表最前面！
            # 对于 Mod，直接 append
            if source_name == "vanilla":
                self.object_registry[rel_logical_path][key].insert(0, ObjectVersion(source_name, node, file_name, ast))
            else:
                self.object_registry[rel_logical_path][key].append(ObjectVersion(source_name, node, file_name, ast))


    def _extract_objects(self, doc: DocumentNode) -> Dict[str, ObjectNode]:
        """从 DocumentNode 中提取顶层 ObjectNode，返回 key->node 映射"""
        objects = {}
        for stmt in doc.statements:
            if isinstance(stmt, ObjectNode):
                stmt.parent = None # disassociate from DocumentNode
                objects[str(stmt.name)] = stmt
        return objects

    def _execute_merges(self):
        # Buffer structures
        # key: (rel_dir, filename) -> List[Node]
        unordered_buffer: Dict[Tuple[str, str], List[ObjectNode]] = defaultdict(list)
        
        # key: (rel_dir, filename) -> (TemplateDocNode, Dict[obj_name, MergedNode])
        ordered_buffer: Dict[Tuple[str, str], Tuple[DocumentNode, Dict[str, ObjectNode]]] = {}

        for logical_path, file_objs in self.object_registry.items():
            # 确定当前文件夹类型
            folder_type = self._get_folder_type(logical_path)
            
            # 如果是 Exclude，早就在 scan 阶段过滤了，这里默认处理需要的
            
            for key, versions in file_objs.items():
                if len(versions) < 3: continue

                # 执行合并... (同之前逻辑)
                base = versions[0].node
                current_merged = versions[1].node
                for i in range(2, len(versions)):
                    theirs = versions[i].node
                    
                        
                    result_node, conflicts = three_way_merge(base, current_merged, theirs)
                    
                    if conflicts:
                        logger.warning(f"  Conflict in step {i}: {conflicts}")
                    
                    current_merged = result_node
                        

                
                result_node = current_merged
                
                # --- 分流逻辑 ---
                if folder_type == FOLDER_ORDERED:
                    # 锚定到最后一个版本
                    last_ver = versions[-1]
                    target_file = last_ver.filename
                    template_doc = last_ver.doc_node
                    
                    buffer_key = (logical_path, target_file)
                    if buffer_key not in ordered_buffer:
                        ordered_buffer[buffer_key] = (template_doc, {})
                    
                    ordered_buffer[buffer_key][1][key] = result_node
                    
                else: # UNORDERED
                    # 锚定到第一个版本 (或者是 Base)
                    # 你的需求：文件名被第一次出现这个mod的文件所定义
                    first_ver = versions[0] 
                    target_file = first_ver.filename
                    
                    buffer_key = (logical_path, target_file)
                    unordered_buffer[buffer_key].append(result_node)

        # --- Flush Unordered ---
        for (rel_dir, fname), nodes in unordered_buffer.items():
            # 构造新文件名
            stem = Path(fname).stem
            ext = Path(fname).suffix
            new_fname = f"{stem}_synthetipy_merge{ext}"
            
            # 创建干净的 Doc
            new_doc = DocumentNode(statements=nodes) # 假设构造函数支持
            self._write_ast(rel_dir, new_fname, new_doc)

        # --- Flush Ordered ---
        for (rel_dir, fname), (template_doc, replacements) in ordered_buffer.items():
            # 深拷贝模板 (因为同一个模板可能被用于多个对象的基底? 
            # 不，同一个文件只会被处理一次，但为了安全起见 copy 一下)
            import copy
            final_doc = copy.deepcopy(template_doc)
            
            # 在 AST 中执行替换
            # 这需要一个辅助函数：replace_top_level_objects(doc, replacements_dict)
            self._apply_replacements(final_doc, replacements)
            
            # 输出原文件名
            self._write_ast(rel_dir, fname, final_doc)

    def _apply_replacements(self, doc: DocumentNode, replacements: Dict[str, ASTNode]):
        # 遍历 doc.statements
        # 如果是 ObjectNode 且 name 在 replacements 里 -> 替换
        for i, stmt in enumerate(doc.statements):
            if isinstance(stmt, ObjectNode) and stmt.name in replacements:
                doc.statements[i] = replacements[stmt.name]

    def _write_ast(self, rel_dir: str, fname: str, doc: DocumentNode):
        output_path = self.output_root / rel_dir / fname
        output_path.parent.mkdir(parents=True, exist_ok=True)
        compile_to_file(doc, str(output_path))