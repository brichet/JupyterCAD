from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import tempfile

from pydantic import BaseModel, Extra

import y_py as Y
from ypywidgets.ypywidgets import Widget

from jupytercad.freecad.loader import fc

from .utils import normalize_path
from .objects import (
    Parts,
    IBox,
    ICone,
    ICut,
    ICylinder,
    IExtrusion,
    IFuse,
    IIntersection,
    Parts,
    ISphere,
    ITorus,
)

logger = logging.getLogger(__file__)


class CadDocument(Widget):
    def __init__(self, path: Optional[str] = None):
        comm_data = CadDocument.path_to_comm(path)

        super().__init__(name="@jupytercad:widget", open_comm=True, comm_data=comm_data)

        self._objects_array: Union[Y.YArray, None] = None
        if self.ydoc:
            self._objects_array = self.ydoc.get_array("objects")

    @property
    def objects(self) -> List[str]:
        if self._objects_array:
            return [x["name"] for x in self._objects_array]
        return []

    @classmethod
    def path_to_comm(cls, filePath: Optional[str]) -> Dict:
        path = None
        format = None
        contentType = None

        if filePath is not None:
            path = normalize_path(filePath)
            file_name = Path(path).name
            try:
                ext = file_name.split(".")[1].lower()
            except Exception:
                raise ValueError("Can not detect file extension!")
            if ext == "fcstd":
                if fc is None:
                    msg = 'FreeCAD is required to open FCStd files'
                    logger.warn(msg)
                    raise RuntimeError(msg)
                format = "base64"
                contentType = "FCStd"
            elif ext == "jcad":
                format = "text"
                contentType = "jcad"
            else:
                raise ValueError("File extension is not supported!")
        comm_data = {
            "path": path,
            "format": format,
            "contentType": contentType,
        }
        return comm_data

    def get_object(self, name: str) -> Optional["PythonJcadObject"]:
        if self.check_exist(name):
            data = json.loads(self._get_yobject_by_name(name).to_json())
            return OBJECT_FACTORY.create_object(data, self)

    def remove(self, name: str) -> CadDocument:
        index = self._get_yobject_index_by_name(name)
        if self._objects_array and index != -1:
            with self.ydoc.begin_transaction() as t:
                self._objects_array.delete(t, index)
        return self

    def add_object(self, new_object: "PythonJcadObject") -> CadDocument:
        if self._objects_array is not None and not self.check_exist(new_object.name):
            obj_dict = json.loads(new_object.json())
            obj_dict["visible"] = True
            new_map = Y.YMap(obj_dict)
            with self.ydoc.begin_transaction() as t:
                self._objects_array.append(t, new_map)
        else:
            logger.error(f"Object {new_object.name} already exists")
        return self

    def add_occ_shape(
        self,
        shape,
        name: str = "",
        position: List[float] = [0, 0, 0],
        rotation_axis: List[float] = [0, 0, 1],
        rotation_angle: float = 0,
    ) -> CadDocument:
        try:
            from OCC.Core.BRepTools import breptools_Write
        except ImportError:
            raise RuntimeError("Cannot add an OpenCascade shape if it's not installed.")

        with tempfile.NamedTemporaryFile() as tmp:
            breptools_Write(shape, tmp.name, True, False, 1)
            brepdata = tmp.read().decode("ascii")

        data = {
            "shape": "Part::Any",
            "name": name if name else self._new_name("Shape"),
            "parameters": {
                "Shape": brepdata,
                "Placement": {
                    "Position": position,
                    "Axis": rotation_axis,
                    "Angle": rotation_angle,
                },
            },
            "visible": True,
        }

        with self.ydoc.begin_transaction() as t:
            self._objects_array.append(t, Y.YMap(data))

        return self

    def add_box(
        self,
        name: str = "",
        length: float = 1,
        width: float = 1,
        height: float = 1,
        position: List[float] = [0, 0, 0],
        rotation_axis: List[float] = [0, 0, 1],
        rotation_angle: float = 0,
    ) -> CadDocument:
        data = {
            "shape": Parts.Part__Box.value,
            "name": name if name else self._new_name("Box"),
            "parameters": {
                "Length": length,
                "Width": width,
                "Height": height,
                "Placement": {
                    "Position": position,
                    "Axis": rotation_axis,
                    "Angle": rotation_angle,
                },
            },
        }
        return self.add_object(OBJECT_FACTORY.create_object(data, self))

    def add_cone(
        self,
        name: str = "",
        radius1: float = 1,
        radius2: float = 0.5,
        height: float = 1,
        angle: float = 360,
        position: List[float] = [0, 0, 0],
        rotation_axis: List[float] = [0, 0, 1],
        rotation_angle: float = 0,
    ) -> CadDocument:
        data = {
            "shape": Parts.Part__Cone.value,
            "name": name if name else self._new_name("Cone"),
            "parameters": {
                "Radius1": radius1,
                "Radius2": radius2,
                "Height": height,
                "Angle": angle,
                "Placement": {
                    "Position": position,
                    "Axis": rotation_axis,
                    "Angle": rotation_angle,
                },
            },
        }
        return self.add_object(OBJECT_FACTORY.create_object(data, self))

    def add_cylinder(
        self,
        name: str = "",
        radius: float = 1,
        height: float = 1,
        angle: float = 360,
        position: List[float] = [0, 0, 0],
        rotation_axis: List[float] = [0, 0, 1],
        rotation_angle: float = 0,
    ) -> CadDocument:
        data = {
            "shape": Parts.Part__Cylinder.value,
            "name": name if name else self._new_name("Cylinder"),
            "parameters": {
                "Radius": radius,
                "Height": height,
                "Angle": angle,
                "Placement": {
                    "Position": position,
                    "Axis": rotation_axis,
                    "Angle": rotation_angle,
                },
            },
        }
        return self.add_object(OBJECT_FACTORY.create_object(data, self))

    def add_sphere(
        self,
        name: str = "",
        radius: float = 5,
        angle1: float = -90,
        angle2: float = 90,
        angle3: float = 360,
        position: List[float] = [0, 0, 0],
        rotation_axis: List[float] = [0, 0, 1],
        rotation_angle: float = 0,
    ) -> CadDocument:
        data = {
            "shape": Parts.Part__Sphere.value,
            "name": name if name else self._new_name("Sphere"),
            "parameters": {
                "Radius": radius,
                "Angle1": angle1,
                "Angle2": angle2,
                "Angle3": angle3,
                "Placement": {
                    "Position": position,
                    "Axis": rotation_axis,
                    "Angle": rotation_angle,
                },
            },
        }
        return self.add_object(OBJECT_FACTORY.create_object(data, self))

    def add_torus(
        self,
        name: str = "",
        radius1: float = 10,
        radius2: float = 2,
        angle1: float = -180,
        angle2: float = 180,
        angle3: float = 360,
        position: List[float] = [0, 0, 0],
        rotation_axis: List[float] = [0, 0, 1],
        rotation_angle: float = 0,
    ) -> CadDocument:
        data = {
            "shape": Parts.Part__Torus.value,
            "name": name if name else self._new_name("Torus"),
            "parameters": {
                "Radius1": radius1,
                "Radius2": radius2,
                "Angle1": angle1,
                "Angle2": angle2,
                "Angle3": angle3,
                "Placement": {
                    "Position": position,
                    "Axis": rotation_axis,
                    "Angle": rotation_angle,
                },
            },
        }
        return self.add_object(OBJECT_FACTORY.create_object(data, self))

    def cut(
        self,
        name: str = "",
        base: str | int = None,
        tool: str | int = None,
        refine: bool = False,
        position: List[float] = [0, 0, 0],
        rotation_axis: List[float] = [0, 0, 1],
        rotation_angle: float = 0,
    ) -> CadDocument:
        base, tool = self._get_boolean_operands(base, tool)

        data = {
            "shape": Parts.Part__Cut.value,
            "name": name if name else self._new_name("Cut"),
            "parameters": {
                "Base": base,
                "Tool": tool,
                "Refine": refine,
                "Placement": {"Position": [0, 0, 0], "Axis": [0, 0, 1], "Angle": 0},
            },
        }
        self.set_visible(base, False)
        self.set_visible(tool, False)
        return self.add_object(OBJECT_FACTORY.create_object(data, self))

    def fuse(
        self,
        name: str = "",
        shape1: str | int = None,
        shape2: str | int = None,
        refine: bool = False,
        position: List[float] = [0, 0, 0],
        rotation_axis: List[float] = [0, 0, 1],
        rotation_angle: float = 0,
    ) -> CadDocument:
        shape1, shape2 = self._get_boolean_operands(shape1, shape2)

        data = {
            "shape": Parts.Part__MultiFuse.value,
            "name": name if name else self._new_name("Cut"),
            "parameters": {
                "Shapes": [shape1, shape2],
                "Refine": refine,
                "Placement": {"Position": [0, 0, 0], "Axis": [0, 0, 1], "Angle": 0},
            },
        }
        self.set_visible(shape1, False)
        self.set_visible(shape2, False)
        return self.add_object(OBJECT_FACTORY.create_object(data, self))

    def intersect(
        self,
        name: str = "",
        shape1: str | int = None,
        shape2: str | int = None,
        refine: bool = False,
        position: List[float] = [0, 0, 0],
        rotation_axis: List[float] = [0, 0, 1],
        rotation_angle: float = 0,
    ) -> CadDocument:
        shape1, shape2 = self._get_boolean_operands(shape1, shape2)

        data = {
            "shape": Parts.Part__MultiCommon.value,
            "name": name if name else self._new_name("Cut"),
            "parameters": {
                "Shapes": [shape1, shape2],
                "Refine": refine,
                "Placement": {"Position": [0, 0, 0], "Axis": [0, 0, 1], "Angle": 0},
            },
        }
        self.set_visible(shape1, False)
        self.set_visible(shape2, False)
        return self.add_object(OBJECT_FACTORY.create_object(data, self))

    def _get_boolean_operands(self, shape1: str | int | None, shape2: str | int | None):
        objects = self.objects

        if len(self.objects) < 2:
            raise ValueError(
                "Cannot apply boolean operator if there are less than two objects in the document."
            )

        if isinstance(shape1, str):
            if shape1 not in objects:
                raise ValueError(f"Unknown object {shape1}")
        elif isinstance(shape1, int):
            shape1 = objects[shape1]
        else:
            shape1 = objects[-2]

        if isinstance(shape2, str):
            if shape2 not in objects:
                raise ValueError(f"Unknown object {shape2}")
        elif isinstance(shape2, int):
            shape2 = objects[shape2]
        else:
            shape2 = objects[-1]

        return shape1, shape2

    def set_visible(self, name: str, value):
        obj: Optional[Y.YMap] = self._get_yobject_by_name(name)

        if obj is None:
            raise RuntimeError(f"No object named {name}")

        with self.ydoc.begin_transaction() as t:
            obj.set(t, "visible", False)

    def check_exist(self, name: str) -> bool:
        if self.objects:
            return name in self.objects
        return False

    def render(self) -> Dict:
        return {
            "application/FCStd": json.dumps({"commId": self.comm_id}),
        }

    def _get_yobject_by_name(self, name: str) -> Optional[Y.YMap]:
        if self._objects_array:
            for index, item in enumerate(self._objects_array):
                if item["name"] == name:
                    return self._objects_array[index]
        return None

    def _get_yobject_index_by_name(self, name: str) -> int:
        if self._objects_array:
            for index, item in enumerate(self._objects_array):
                if item["name"] == name:
                    return index
        return -1

    def _new_name(self, obj_type: str) -> str:
        n = 1
        name = f"{obj_type} 1"
        objects = self.objects

        while name in objects:
            name = f"{obj_type} {n}"
            n += 1

        return name

    def _repr_mimebundle_(self, **kwargs):
        return self.render()


class PythonJcadObject(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True
        extra = Extra.allow

    name: str
    shape: Parts
    parameters: Union[
        IBox,
        ICone,
        ICut,
        ICylinder,
        IExtrusion,
        IIntersection,
        IFuse,
        ISphere,
        ITorus,
    ]

    _caddoc = Optional[CadDocument]
    _parent = Optional[CadDocument]

    def __init__(__pydantic_self__, parent, **data: Any) -> None:  # noqa
        super().__init__(**data)
        __pydantic_self__._caddoc = CadDocument()
        __pydantic_self__._caddoc.add_object(__pydantic_self__)
        __pydantic_self__._parent = parent

    def _repr_mimebundle_(self, **kwargs):
        return self._caddoc.render()


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class ObjectFactoryManager(metaclass=SingletonMeta):
    def __init__(self):
        self._factories: Dict[str, type[BaseModel]] = {}

    def register_factory(self, shape_type: str, cls: type[BaseModel]) -> None:
        if shape_type not in self._factories:
            self._factories[shape_type] = cls

    def create_object(
        self, data: Dict, parent: Optional[CadDocument] = None
    ) -> Optional[PythonJcadObject]:
        object_type = data.get("shape", None)
        name: str = data.get("name", None)
        if object_type and object_type in self._factories:
            Model = self._factories[object_type]
            args = {}
            params = data["parameters"]
            for field in Model.__fields__:
                args[field] = params.get(field, None)
            obj_params = Model(**args)
            return PythonJcadObject(
                parent=parent,
                name=name,
                shape=object_type,
                parameters=obj_params,
            )

        return None


OBJECT_FACTORY = ObjectFactoryManager()

OBJECT_FACTORY.register_factory(Parts.Part__Box.value, IBox)
OBJECT_FACTORY.register_factory(Parts.Part__Cone.value, ICone)
OBJECT_FACTORY.register_factory(Parts.Part__Cut.value, ICut)
OBJECT_FACTORY.register_factory(Parts.Part__Cylinder.value, ICylinder)
OBJECT_FACTORY.register_factory(Parts.Part__Extrusion.value, IExtrusion)
OBJECT_FACTORY.register_factory(Parts.Part__MultiCommon.value, IIntersection)
OBJECT_FACTORY.register_factory(Parts.Part__MultiFuse.value, IFuse)
OBJECT_FACTORY.register_factory(Parts.Part__Sphere.value, ISphere)
OBJECT_FACTORY.register_factory(Parts.Part__Torus.value, ITorus)