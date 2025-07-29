"""Module for handling bounding box coordinates.

Throughout the models and data formats used in exsclaim, bounding boxes are sometimes stored as x1,y1,x2,y2
or 'coords' and sometimes as [{"x": x1, "y": y1}, ...] or 'labelbox'

In addition, we often want to check the relation of two bounding
boxes and their properties (like center point)
"""
from numpy import ndarray


__all__ = ["convert_coords_to_labelbox", "convert_labelbox_to_coords", "find_box_center", "crop_from_geometry", "is_contained"]


def convert_coords_to_labelbox(x1:int, y1:int, x2:int, y2:int):
    """Converts x1,y1,x2,y2 to [{"x": x1, "y": y1}, ...]"""
    return [
        {"x": x1, "y": y1},
        {"x": x1, "y": y2},
        {"x": x2, "y": y2},
        {"x": x2, "y": y1},
    ]


def convert_labelbox_to_coords(geometry:list[dict[str, float | int]]):
    """Converts from [{"x": x1, "y": y1}, ...] to (x1, y1, ...)"""
    # print(geometry)
    x1 = min([point["x"] for point in geometry])
    y1 = min([point["y"] for point in geometry])
    x2 = max([point["x"] for point in geometry])
    y2 = max([point["y"] for point in geometry])
    return x1, y1, x2, y2


def find_box_center(geometry):
    """Returns the center (x, y) coords of the box"""
    x1, y1, x2, y2 = convert_labelbox_to_coords(geometry)
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def crop_from_geometry(geometry:list[dict], image:ndarray) -> ndarray:
    """Returns an image cropped to include coordinates in geometry

    Args:
        geometry (list of dicts): Geometry JSON from exsclaim JSON.
            4 dicts, each having x and y coords for corners of bounding
            box. [Top left, bottom left, top right, bottom right]
        image (np.array): Numpy array representing an image to be cropped
    Returns:
        Cropped image according to geometry given as a numpy array
    """
    x1, y1 = geometry[0]["x"], geometry[0]["y"]
    x2, y2 = geometry[3]["x"], geometry[3]["y"]
    return image[y1:y2, x1:x2]


def is_contained(inner, outer, padding=0) -> bool:
    """tests whether one bounding box is within another"""
    inner_x1, inner_y1, inner_x2, inner_y2 = convert_labelbox_to_coords(inner)
    outer_x1, outer_y1, outer_x2, outer_y2 = convert_labelbox_to_coords(outer)
    outer_x1, outer_y1 = outer_x1 - padding, outer_y1 - padding
    outer_x2, outer_y2 = outer_x2 + padding, outer_y2 + padding

    return (
        inner_x1 > outer_x1
        and inner_x2 < outer_x2
        and inner_y1 > outer_y1
        and inner_y2 < outer_y2
    )
