import unreal
import os
from .BaseWizard import BaseWizard 

class BossWizard(BaseWizard):
    def __init__(self, jsonPath):
        super().__init__(jsonPath, "config_template_boss.json")

    def create_class(self):
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        parent_class = unreal.EditorAssetLibrary.load_blueprint_class(self.DEFAULT_ENEMY_CLASS)
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', parent_class)
        new_asset = asset_tools.create_asset(
            "BP_Enemy_" + self.data.get_text("asset_name"),
            self.DEFAULT_ENEMY_PATH,
            unreal.Blueprint,
            factory
        )
        unreal.EditorAssetLibrary.save_loaded_asset(new_asset, True)

    def create_behavior_tree(self):
        name = "BT_Enemy_" + self.data.get_text("asset_name")
        self.duplicate_asset(name, self.DEFAULT_ENEMY_PATH, self.DEFAULT_ENEMY_BT)

    def create_abp(self):
        name = "ABP_Enemy_" + self.data.get_text("asset_name")
        self.duplicate_asset(name, self.DEFAULT_ENEMY_PATH, self.DEFAULT_ENEMY_ABP)