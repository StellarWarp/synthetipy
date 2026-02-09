from pathlib import Path
from synthetipy.script_merger.interface import BatchMerger,EXAMPLE_CONFIG



def test_batch_merge():
    GAME_FOLDER = Path("D:/SteamLibrary/steamapps/common/Stellaris")
    MODS = [
        Path("C:/Users/Estelle/source/repos/pdxlang_patcher/test_mods/mod1"),
        Path("C:/Users/Estelle/source/repos/pdxlang_patcher/test_mods/mod2"),
    ]
    OUTPUT_FOLDER = Path("C:/Users/Estelle/source/repos/pdxlang_patcher/test_mods/merged_output")
    
    merger = BatchMerger(GAME_FOLDER, MODS, OUTPUT_FOLDER, EXAMPLE_CONFIG)
    merger.run()
    
test_batch_merge()