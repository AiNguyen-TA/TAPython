import unreal
from Utilities.Utils import Singleton
import json
import os
from .DataObject import DataObject, DataSubscriber

class BaseWizard(DataSubscriber):
    def __init__(self, jsonPath, config_path):
        self.jsonPath = jsonPath
        self.data = unreal.PythonBPLib.get_chameleon_data(self.jsonPath)
        self.asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        self.config = {}
        self.base_asset = None
        self.name = None
        self.objectDatas : dict[str, DataObject] = {}
        self.config_path = None
        self.load_config_file(config_path)

        content = self.create_json_content_from_data()
        self.data.set_content_from_json("main-content", content)
        self.hide_rename()
        self.hide_properties()

    def on_value_changed(self, id):
        try:
            self.data.set_text(id + "-text", self._get_asset_data(id).get_name())
            self.data.set_color_and_opacity(id + "-text", self._get_asset_data(id).get_text_color())
        except:
            pass
        
        if self.base_asset:
            unreal.EditorAssetLibrary.save_asset(self.base_asset, True)


    def load_config_file(self, config_path):
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), config_path))
        self.config_path = path
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                self.CONFIG = config.get("assetRefs")
                self.BASE_CLASS = config.get("baseClass").get("assetPath")
                self.DEFAULT_DIR = config.get("baseClass").get("defaultDirectory")
        except FileNotFoundError:
            unreal.log_error(f"Config file not found: {config_path}")
        except json.JSONDecodeError as e:
            unreal.log_error(f"Invalid JSON in config: {e}")

    def rename_asset(self, aka):
        asset = self._get_asset_data(aka)
        new_name = self.data.get_text(aka + "new-name")
        result = asset.rename(new_name)
        if not result:
            self.data.set_text(aka + "new-name", "")

    def on_request_create_base_asset(self):
        name = self.data.get_text("enemy-name")
        print(name)
        if not name:
            unreal.EditorDialog.show_message("Error", "Name is empty!", unreal.AppMsgType.OK)
            return
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        parent_class = unreal.EditorAssetLibrary.load_blueprint_class(self.BASE_CLASS)
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', parent_class)
        created_asset = asset_tools.create_asset(
            "BP_Enemy_" + name,
            self.DEFAULT_DIR,
            unreal.Blueprint,
            factory
        )
        if created_asset:
            asset_path = created_asset.get_path_name()
            unreal.EditorDialog.show_message("Error", "Created " + asset_path, unreal.AppMsgType.OK)
            unreal.EditorAssetLibrary.save_asset(asset_path, True)
        else:
            unreal.EditorDialog.show_message("Error", "Failed", unreal.AppMsgType.OK)

        self.load_base_class(created_asset.get_path_name())
    
    def on_request_create_default_asset(self, aka):
        property = self._get_asset_data(aka) 
        name = self.data.get_text("enemy-name")
        property.create_default_value(name)

    def duplicate_asset(self, name, save_path, source_asset_path):
        source_asset = unreal.EditorAssetLibrary.load_asset(source_asset_path)
        new_asset = self.asset_tools.duplicate_asset(name, save_path, source_asset)
        unreal.EditorAssetLibrary.save_loaded_asset(new_asset, True)
        return new_asset
    
    def load_base_class(self, asset_path):
        # DOTO: handle C++ because currently only load blueprint class
        if not asset_path:
            unreal.EditorDialog.show_message("Error", "Please provide valid base class!", unreal.AppMsgType.OK)
            return
        
        self.data.set_text("base-class-text", asset_path)
        for key in self.CONFIG:
            self.objectDatas[key] = DataObject(key, asset_path, self.config_path)
            self.objectDatas[key].register_subscriber(self)

            self.on_value_changed(key)
        
        self.show_properties()
        self.show_rename()
        self.update_asset_color()
        self.base_asset = asset_path

    def _get_asset_from_property(self, property_name):
        return unreal.load_asset(self.CONFIG.get(property_name).get("assetPath"))

    def on_drop_base_class(self, *args, **kwargs):
        assets = kwargs.get("assets", None)
        if assets:
            self.load_base_class(assets[0])

    def on_asset_clicked(self, aka):
        asset = self._get_asset_data(aka)
        asset.edit_asset()

    def on_drop_asset(self, aka, **kwargs):
        assets = kwargs.get("assets", None)
        if assets:
            new_asset = unreal.load_asset(assets[0])
            dataObject = self._get_asset_data(aka)
            if dataObject:
                dataObject.set_property(new_asset)

    def _get_asset_data(self, key) -> DataObject:
        if key:
            return self.objectDatas[key]

    def create_json_content_from_data(self):
        slots = []
        for key, value in self.CONFIG.items():
            slots.append(
                {
                    "Aka": key,
                    "AutoHeight": True,
                    "SHorizontalBox": {
                        "Slots": [
                            {
                                "AutoHeight": True,
                                "SHorizontalBox": {
                                    "Slots": [
                                        {
                                            "AutoWidth": True,
                                            "AutoHeight": True,
                                            "SColorBlock": {
                                                "Aka": key + "-color",
                                                "Size": [10, 30],
                                                "Color": [1, 0, 0, 1],
                                                "ColorIsHSV": False
                                            }
                                        },
                                        {
                                            "SButton": {
                                                "Content": {
                                                    "SDropTarget": {
                                                        "Content": {
                                                            "STextBlock":
                                                                {
                                                                    "Aka": key + "-text",
                                                                    "Text": key,
                                                                }
                                                        },
                                                        # TODO hard-coded
                                                        "OnDrop": f"boss_wizard.on_drop_asset('{key}', %**kwargs)"
                                                    }
                                                },
                                                # TODO hard-coded for now
                                                "OnClick": f"boss_wizard.on_asset_clicked('{key}')"
                                            }
                                        },
                                        {
                                            "AutoHeight": True,
                                            "AutoWidth": True,
                                            "SButton": {
                                                "ButtonColorAndOpacity": [0, 0.5, 1.5, 1],
                                                "Content": {
                                                    "SImage": {
                                                        "Image": {
                                                            "Style": "FEditorStyle",
                                                            "Brush": "SystemWideCommands.FindInContentBrowser.Small"
                                                        },
                                                        "DesiredSizeOverride": [23, 10]
                                                    }
                                                },
                                                "ToolTipText": "Browse to asset",
                                                "OnClick": f"boss_wizard.sync_to_editor('{key}')"
                                            }
                                        }
                                    ]
                                }
                            },
                            {
                                "AutoHeight": True,
                                "SHorizontalBox": {
                                    "Slots": [
                                        {
                                            "AutoWidth": True,
                                            "SBox": {
                                                "WidthOverride": 100,
                                                "Content": {
                                                    "SButton": {
                                                        "HAlign": "Center",
                                                        "VAlign": "Center",
                                                        "Text": "Create",
                                                        "ButtonColorAndOpacity": [0, 3, 0, 1],
                                                        "ToolTipText": "Create new asset based on template",
                                                        "OnClick": f"boss_wizard.on_request_create_default_asset('{key}')"
                                                    }
                                                }
                                            }
                                        },
                                        {
                                            "AutoHeight": True,
                                            "SHorizontalBox": {
                                                "Aka": key + "-rename",
                                                "Slots": [
                                                    {
                                                        "Padding": [10, 0, 0, 0],
                                                        "VAlign": "Center",
                                                        "AutoHeight": True,
                                                        "SEditableText": {
                                                            "Aka": key + "new-name",
                                                            "HAlign": "Center",
                                                            "HintText": "New name, don't add prefix"
                                                            }
                                                    },
                                                    {
                                                        "AutoWidth": True,
                                                        "SBox": {
                                                            "WidthOverride": 100,
                                                            "Content": {
                                                                "SButton": {
                                                                "AutoHeight": True,
                                                                "HAlign": "Center",
                                                                    "VAlign": "Center",
                                                                    "Text": "Rename 🤓",
                                                                    "ButtonColorAndOpacity": [3, 2.8, 0, 1],
                                                                    #TODO hard-coded
                                                                    "OnClick": f"boss_wizard.rename_asset('{key}')",
                                                                }
                                                            }
                                                        }
                                                    },
                                                ]
                                            }
                                        },
                                    ]
                                }   
                            },
                        ]
                }})

        structure = {
            "SVerticalBox": {
                "Slots": slots
            }
        }

        json_string = json.dumps(structure, indent=4)
        return json_string    

    def hide_rename(self):
        for key in self.CONFIG:
            self.data.set_visibility(key + "-rename", "Collapsed")
    
    def show_rename(self):
        for key in self.CONFIG:
            self.data.set_visibility(key + "-rename", "Visible")

    def hide_properties(self):
        for key in self.CONFIG:
            self.data.set_visibility(key, "Collapsed")

    def show_properties(self):
        for key in self.CONFIG:
            self.data.set_visibility(key, "Visible")
        self.data.set_visibility("browse-to-base-asset", "Visible")

    # for quick test random logics
    def sync_to_editor(self, aka):
        asset_path = self._get_asset_data(aka).get_path()
        if asset_path:
            unreal.EditorAssetLibrary.sync_browser_to_objects([asset_path])
    
    def update_asset_color(self):
        for key in self.CONFIG:
            data = self._get_asset_data(key)
            self.data.set_color(key + "-color", data.get_asset_color())

    def sync_browser_to_base(self):
        unreal.EditorAssetLibrary.sync_browser_to_objects([self.base_asset])