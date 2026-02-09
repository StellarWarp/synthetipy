# Synthetipy

A Python library for Stellaris modding

---

## Mod Merger

### Overview
- The Mod Merger auto merges the **resolvable edit conflicts** in multiple Stellaris mod script files (Paradox Script) into a patch mod.
- It uses **AST-based** (gumtree algorithm) matching and edit generation to combine changes from different mods while preserving the original structure and logic and minimizing conflicts as much as possible.

### Key features
- Scans and merges script files from multiple mods while preserving directory structure.
- Uses normalization + AST matching for accurate diffs and edits.
- Produces merge outputs suitable for testing or as a final merged mod directory.

### Quick start
```python
from pathlib import Path
from synthetipy.script_merger.interface import *

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
}


GAME_FOLDER = Path("D:/SteamLibrary/steamapps/common/Stellaris")
MODS = [
    Path("path_to_mod1"),
    Path("path_to_mod2")
    ]
OUTPUT_FOLDER = Path("path_to_output_folder")

merger = BatchMerger(GAME_FOLDER, MODS, OUTPUT_FOLDER, EXAMPLE_CONFIG)
merger.run()
```

### Limitations

What is **resolvable edit conflicts**？

- Stellaris and other Paradox games use a "**last one wins**" approach to mod loading, which means that if two mods modify the same script object (e.g., a building, or a technology), the one that is loaded last will overwrite the changes of the previous one. This can lead to conflicts when multiple mods try to modify the same object, and it can be difficult for modders to resolve these conflicts manually.
- The Mod Merger is designed to automatically resolve some of these conflicts by **merging the changes from multiple mods into a single patch mod**. However, there are some limitations to what the Mod Merger can do:
- The Mod Merger can only merge changes that are **not structurally conflicting on the same object**. 
    - e.g., if two mods add properties to the same building, the Mod Merger can merge those changes together. But if one mod deletes some properties of the building, while another mod modifies those properties, the Mod Merger will report a conflict that requires manual resolution.
- The Mod Merger may not be able to resolve **conflicts that involve complex logic or interactions** between different objects. In such cases, manual review and editing may be necessary to ensure that the merged mod functions correctly.
- The Mod Merger currently **not support merging of certain types of script files**, such as event, inline scripts, on_actions, economic_plans etc. These files do not define top-level objects.
- **Currently the merge conflict print is not very user-friendly**.




### Important modules
- Entry & config: synthetipy.script_merger.interface (BatchMerger, EXAMPLE_CONFIG)
- Merge core: synthetipy.script_merger.merge
- Matching & hashing: synthetipy.script_merger.matcher, gumtree_hash
- Edit & ops: synthetipy.script_merger.edits, ops
- Utilities: synthetipy.script_merger.utils

### Notes
- Ensure GAME_FOLDER points to your Stellaris installation when needed.
- Merge outputs include generated edits and merged files; review before publishing.
- To change merge behavior, update interface configuration and relevant modules.

# Contributing
- Add tests for new features or bug fixes and submit a PR.