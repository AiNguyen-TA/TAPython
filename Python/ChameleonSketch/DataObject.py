import unreal
from abc import ABC, abstractmethod
import json

class DataSubscriber(ABC):
    @abstractmethod
    def on_value_changed(self, id: str):
        pass

#add comment to test submodule
#add comment to test submodule

class DataObject():
    def __init__(self, id: str, parent_path: str, config_path: str):
        self._id = id
        self._outerObject = None
        self._asset = None
        self._default_asset_path = None
        self._default_save_path = None
        self._is_generated = False
        self._subscribers : list[DataSubscriber] = []
        if not parent_path:
            return

        blueprint_asset = unreal.EditorAssetLibrary.load_blueprint_class(parent_path)
        self._outerObject = unreal.get_default_object(blueprint_asset)
        
        try:
            self._asset = self._outerObject.get_editor_property(id)
        except:
            #tip from random stanger to get all components (included blueprint components)
            subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
            loaded_asset = unreal.load_asset(parent_path)
            data_handles = subsystem.k2_gather_subobject_data_for_blueprint(loaded_asset)
            for handle in data_handles:
                data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
                object = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data)
                try:
                    self._asset = object.get_editor_property(id)

                    # handle generated class asset because it is not the same
                    asset_path = self._asset.get_path_name()
                    if asset_path.endswith("_C"):
                        blueprint_path = asset_path.rsplit("_C", 1)[0]
                        blueprint_asset = unreal.load_asset(blueprint_path)
                        self._asset = blueprint_asset
                        self._is_generated = True

                    self._outerObject = object
                except Exception as e:
                    pass
        self.load_config_path(config_path)

    def load_config_path(self, config_path):
        if not config_path:
            return

        with open(config_path, 'r') as f:
            config = json.load(f)
            self._default_asset_path = config.get("assetRefs").get(self._id).get("assetPath")
            self._default_save_path = config.get("assetRefs").get(self._id).get("defaultDirectory")
            # else just get the default path of base class
            if not self._default_save_path:
                self._default_save_path = config.get("baseClass").get("defaultDirectory")

    def get_path(self) -> str:
        if self._asset:
            return self._asset.get_path_name()
        
    def get_outer(self) -> unreal.Object:
        return self._outerObject

    def set_property(self, new_property: unreal.Object):
        if new_property:
            valid_class = None
            valid_class = self._asset.static_class()
            if not valid_class:
                valid_class = unreal.load_asset(self._default_asset_path).static_class() 

            if not valid_class == new_property.static_class():
                unreal.EditorDialog.show_message("Error",
                                                 "Asset should be of type " + valid_class.get_name(),
                                                 unreal.AppMsgType.OK)
                return
            
            property_to_change = new_property
            if self._is_generated:
                property_to_change = new_property.generated_class()

            try:
                self._outerObject.set_editor_property(self._id, property_to_change)
                unreal.log(f"Successfully set property '{self._id}' to {new_property}")
                self._asset = new_property
                self.on_value_changed()
            except Exception as e:
                unreal.log_error(f"Failed to set property '{self._id}': {e}")

    def get_name(self) -> str:
        if self._asset:
            return self._asset.get_name()
        else:
            return "<missing asset> " + self._id

    def get_text_color(self):
        return [1, 1, 1, 1] if self._asset else [1, 0, 0, 1]

    def register_subscriber(self, sub: DataSubscriber):
        if sub:
            self._subscribers.append(sub)

    def create_default_value(self, name):
        if not name:
            unreal.EditorDialog.show_message("Error", "Name is empty!", unreal.AppMsgType.OK)
            return
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        if self._default_asset_path:
            loaded_asset = unreal.load_asset(self._default_asset_path)
            saved_name = self.get_prefix() + name
            new_asset = asset_tools.duplicate_asset(saved_name, self._default_save_path, loaded_asset)
        if new_asset:
            unreal.EditorAssetLibrary.save_asset(new_asset.get_path_name(), True)
            self.set_property(new_asset)
    
    def rename(self, new_name):
        if not new_name:
            unreal.EditorDialog.show_message("Error 🤣", "New name is empty 🤣", unreal.AppMsgType.OK)
            return False
        
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        package_path = unreal.Paths.get_path(self._asset.get_path_name())
        asset_rename_data = unreal.AssetRenameData(self._asset, package_path, self.get_prefix() + new_name)
        result = asset_tools.rename_assets([asset_rename_data])

        if result: 
            self.on_value_changed()
        return result

    def on_value_changed(self):
        for sub in self._subscribers:
            sub.on_value_changed(self._id)
    
    def get_asset_color(self):
        asset = self._asset if self._asset else unreal.load_asset(self._default_asset_path)
        if asset:
            if isinstance(asset, unreal.BehaviorTree):
                return [0.3, 0.06, 1, 1]
            if isinstance(asset, unreal.AnimBlueprint):
                return [0.58, 0.17, 0, 1]
            if isinstance(asset, unreal.AnimMontage):
                return [0.13, 0.13, 1, 1]
            if isinstance(asset, unreal.SkeletalMesh):
                return [0.88, 0.37, 0.88, 1]
            if isinstance(asset, unreal.Blueprint):
                return [0.05, 0.2, 1, 1]

        return [255, 255, 255, 1]
    
    def edit_asset(self):
        if self._asset:
            asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
            asset_tools.open_editor_for_assets([self._asset])
        else:
            unreal.EditorDialog.show_message("Error", "There is no asset to edit!", unreal.AppMsgType.OK)
    
    def get_prefix(self) -> str:
        if not self._asset:
            unreal.EditorDialog.show_message("Error", "No asset to rename 😒", unreal.AppMsgType.OK)
            return
        if isinstance(self._asset, unreal.BehaviorTree):
            return "BT_"
        if isinstance(self._asset, unreal.AnimBlueprint):
            return "ABP_"
        if isinstance(self._asset, unreal.AnimMontage):
            return "AMT_"
        if isinstance(self._asset, unreal.Blueprint):
            return "BP_"
        if isinstance(self._asset, unreal.SkeletalMesh):
            return "SK_"
        unreal.EditorDialog.show_message("Warning", "Coudn't find suitable prefix, will use undefined_", unreal.AppMsgType.OK)
        return "undefined_"