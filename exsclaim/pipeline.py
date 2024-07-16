from .figure import FigureSeparator
from .notifications import *
from .tool import ExsclaimTool, CaptionDistributor, JournalScraper, HTMLScraper
from .utilities import paths, PrinterFormatter, ExsclaimFormatter, convert_labelbox_to_coords, crop_from_geometry

import logging
import numpy as np

from csv import writer
from cv2 import imwrite as cv_imwrite
from datetime import datetime as dt
from enum import Flag, auto
from functools import reduce
from json import load, dump
from os.path import isfile, splitext
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from re import sub
from textwrap import wrap
from typing import Callable

__all__ = ["Pipeline", "SaveMethods"]


class SaveMethods(Flag):
    SUBFIGURES = auto()
    VISUALIZATION = auto()
    BOXES = auto()
    POSTGRES = auto()
    CSV = auto()
    MONGO = auto()

    @classmethod
    def from_str(cls, string:str):
        match(string):
            case "save_subfigures":
                return cls.SUBFIGURES
            case "visualization" | "visualize":
                return cls.VISUALIZATION
            case "boxes":
                return cls.BOXES
            case "postgres":
                return cls.POSTGRES
            case "csv":
                return cls.CSV
            case "mongo":
                return cls.MONGO
            case _:
                raise ValueError(f"There is no corresponding save_method to: {string}.")

    @classmethod
    def from_list(cls, lst:list[str]):
        def get_values(value:str):
            try:
                return cls.from_str(value)
            except ValueError:
                return None
        return reduce(lambda x, y: x | y, filter(lambda x: x is not None, map(get_values, lst)))


class Pipeline:
    """Defines the exsclaim! pipeline"""

    def __init__(self, query_path):
        """initialize a Pipeline to run on query path and save to exsclaim path

        Args:
            query_path (dict or path to json): An EXSCLAIM user query JSON
        """
        # Load Query on which Pipeline will run
        self.current_path = Path(__file__).resolve().parent
        if "test" == query_path:
            query_path = self.current_path / "tests" / "data" / "nature_test.json"

        if isinstance(query_path, dict):
            self.query_dict = query_path
            self.query_path = ""
        else:
            assert isfile(query_path), f"query path must be a dict, query path, or 'test', was {query_path}."
            self.query_path = query_path
            with open(self.query_path) as f:
                # Load query file to dict
                self.query_dict = load(f)

        # Set up file structure
        base_results_dir = paths.initialize_results_dir(self.query_dict.get("results_dir", None))
        
        self.results_directory = base_results_dir / self.query_dict["name"]
        self.results_directory.mkdir(exist_ok=True)

        # region Set up logging
        handlers = []
        for log_output in self.query_dict.get("logging", []):
            if log_output.lower() == "print":
                handler = logging.StreamHandler()
                handler.setFormatter(PrinterFormatter())
            else:
                log_output = self.results_directory / log_output
                handler = logging.FileHandler(filename=log_output, mode="w+")
                handler.setFormatter(ExsclaimFormatter())
            handlers.append(handler)

        logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Results will be located in: `{self.results_directory}`.")
        # endregion

        # region Check for an existing exsclaim json
        self.exsclaim_path = self.results_directory / "exsclaim.json"

        if self.exsclaim_path.exists():
            with open(self.exsclaim_path, "r") as f:
                # Load configuration file values
                self.exsclaim_dict = load(f)
        else:
            self.logger.info("No exsclaim.json file found, starting a new one.")
            # Keep preset values
            self.exsclaim_dict = {}
        # endregion

        # region Set up notifications
        exsclaim_notifications = self.query_dict.get("notifications", {})
        notifications = (_class.from_json(json)
                         for key, _class in notifiers.items()
                         for json in exsclaim_notifications.get(key, []))
        self.notifications:tuple[Notifications] = tuple(notifications)
        # endregion

    def display_info(self, info):
        """Display information to the user as the specified in the query

        Args:
            info (str): A string to display (either to stdout, a log file)
        """
        self.logger.info(info)

    def run(self, tools:list[ExsclaimTool]=None, figure_separator=True, caption_distributor=True, journal_scraper=True, html_scraper=True) -> dict:
        """Run EXSCLAIM pipeline on Pipeline instance's query path

        Args:
            tools (list of ExsclaimTools): list of ExsclaimTool objects
                to run on query path in the order they will run. Default
                argument is JournalScraper, CaptionDistributor,
                FigureSeparator
            journal_scraper (boolean): true if JournalScraper should
                be included in tools list. Overridden by a tools argument
            caption_distributor (boolean): true if CaptionDistributor should
                be included in tools list. Overridden by a tools argument
            figure_separator (boolean): true if FigureSeparator should
                be included in tools list. Overridden by a tools argument
            html_scraper (boolean): true if HTMLScraper should
                be included in tools list. Overridden by a tools argument
        Returns:
            exsclaim_dict (dict): an exsclaim json
        Modifies:
            self.exsclaim_dict
        """
        exsclaim_art = """
        @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
        @@@@@@@@@@@@@@@@@@@&   /&@@@(   /@@@@@@@@@@@@@@@@@@@
        @@@@@@@@@@@@@@@ %@@@@@@@@@@@@@@@@@@@ *@@@@@@@@@@@@@@
        @@@@@@@@@@@@ @@@@@@@@@@@@@@,  .@@@@@@@@ *@@@@@@@@@@@
        @@@@@@@@@.#@@@@@@@@@@@@@@@@,    @@@@@@@@@@ @@@@@@@@@
        @@@@@@@&,@@@@@@@@@@@@@@@@@@.    @@@@@@@@@@@@ @@@@@@@
        @@@@@@ @@@@@@@@@@@@@@@@@@@@     @@@@@@@@@@@@@ @@@@@@
        @@@@@ @@@@@@@@@@@@@@@@@@@@@    *@@@@@@@@@@@@@@/@@@@@
        @@@@ @@@@@@@@@@@@@@@@@@@@@@    @@@@@@@@@@@@@@@@,@@@@
        @@@ @@@@@@@@@@@@@@@@@@@@@@&    @@@@@@@@@@@@@@@@@ @@@
        @@@,@@@@@@@@@@@@@@@@@@@@@@*   (@@@@@@@@@@@@@@@@@@%@@
        @@.@@@@@@@@@@@@@@@@@@@@@@@    @@@@@@@@@@@@@@@@@@@ @@
        @@ @@@@@@@@@@@@@@@@@@@@@@@    @@@@@@@@@@@@@@@@@@@ @@
        @@ @@@@@@@@@@@@@@@@@@@@@@/   &@@@@@@@@@@@@@@@@@@@ @@
        @@,@@@@@@@@@@@@@@@@@@@@@@    @@@@@@@@@@@@@@@@@@@@ @@
        @@@.@@@@@@@@@@@@@@@@@@@@&   @@@@@@@@@@@@@@@@@@@@@%@@
        @@@ @@@@@@@@@@@@@@@@@@@@@  /@@@@@@@@@@@@@@@@@@@@ @@@
        @@@@ @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@,@@@@
        @@@@@ @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@*@@@@@
        @@@@@@ @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ @@@@@@
        @@@@@@@@ @@@@@@@@@@@@    @@@@@@@@@@@@@@@@@@@ @@@@@@@
        @@@@@@@@@.(@@@@@@@@@@     @@@@@@@@@@@@@@@@ @@@@@@@@@
        @@@@@@@@@@@@ @@@@@@@@@#   #@@@@@@@@@@@@ /@@@@@@@@@@@
        @@@@@@@@@@@@@@@ ,@@@@@@@@@@@@@@@@@@@ &@@@@@@@@@@@@@@
        @@@@@@@@@@@@@@@@@@@@   ,%@@&/   (@@@@@@@@@@@@@@@@@@@
        @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
        """
        self.display_info(exsclaim_art)
        _id = self.query_dict.get("id", None)
        try:
            # set default values
            if tools is None:
                tools = []
                if journal_scraper:
                    tools.append(JournalScraper(self.query_dict, logger=self.logger))
                if html_scraper:
                    tools.append(HTMLScraper(self.query_dict, logger=self.logger))
                if caption_distributor:
                    tools.append(CaptionDistributor(self.query_dict, logger=self.logger))
                if figure_separator:
                    tools.append(FigureSeparator(self.query_dict, logger=self.logger))

            # run each ExsclaimTool on search query
            for tool in tools:
                self.exsclaim_dict = tool.run(self.query_dict, self.exsclaim_dict)

            # group unassigned objects
            self.group_objects()

            # Save results as specified
            save_methods = self.query_dict.get("save_format", None)
            if save_methods is not None:
                save_methods = SaveMethods.from_list(save_methods)

                if SaveMethods.SUBFIGURES in save_methods:
                    self.to_file()

                if SaveMethods.VISUALIZATION in save_methods:
                    for figure in self.exsclaim_dict:
                        self.make_visualization(figure)

                if SaveMethods.BOXES in save_methods:
                    for figure in self.exsclaim_dict:
                        self.draw_bounding_boxes(figure)

                if SaveMethods.POSTGRES in save_methods:
                    csv_dir = self.to_csv()
                    self.to_postgres(csv_dir)

                elif SaveMethods.CSV in save_methods and SaveMethods.POSTGRES not in save_methods:
                    self.to_csv()

                if SaveMethods.MONGO in save_methods:
                    try:
                        import pymongo
                    except ImportError | ModuleNotFoundError:
                        from os import system
                        system("pip install pymongo==4.7.3")
                        import pymongo

                    db_client = pymongo.MongoClient(self.query_dict["mongo_connection"])
                    db = db_client["materialeyes"]
                    collection = db[self.query_dict["name"]]
                    db_push = list(self.exsclaim_dict.values())
                    collection.insert_many(db_push)

            # Creates success messages to be sent to the notifiers
            message = f"EXSCLAIM! query{f' `{_id}`' if _id is not None else ''} finished at: {dt.now():%Y-%m-%dT%H:%M%z}."
        except Exception as e:
            self.logger.exception(e)
            message = f"An error occurred at {dt.now():%Y-%m-%dT%H:%M%z} running{' the' if _id is None else ''} EXSCLAIM! query{f' `{_id}`' if _id is not None else ''}."

        for notifier in self.notifications:
            notifier.notify(message, name=self.query_dict["name"])

        return self.exsclaim_dict

    @staticmethod
    def assign_captions(figure) -> tuple[list[dict], dict]:
        """Assigns all captions to master_images JSONs for single figure

        Args:
            figure (dict): a Figure JSON
        Returns:
            masters (list of dicts): list of master_images JSONs
            unassigned (dict): the updated unassigned JSON
        """
        unassigned = figure.get("unassigned", {})
        masters = []

        captions = unassigned.get("captions", {})
        not_assigned = {a["label"] for a in captions}

        for index, master_image in enumerate(figure.get("master_images", [])):
            label_json = master_image.get("subfigure_label", {})
            subfigure_label = label_json.get("text", index)

            # remove periods or commas from around subfigure label
            processed_label = sub(r"[().,]", "", subfigure_label)
            paired = False

            for caption_label in captions:
                # remove periods or commas from around caption label
                processed_caption_label = sub(r"[().,]", "", caption_label["label"])

                # check if caption label and subfigure label match and caption label has not already been matched
                if (processed_caption_label.lower() != processed_label.lower() or processed_caption_label.lower() not in [a.lower() for a in not_assigned]):
                    continue

                print(f"Caption_label: {caption_label['description']}")
                master_image |= {
                    "caption": caption_label["description"], # .replace("\n", " ").strip()
                    "keywords": caption_label["keywords"],
                    # "context": caption_label["context"],
                    # "general": caption_label["general"],
                }

                masters.append(master_image)

                not_assigned.remove(caption_label["label"])
                # break to next master image if a pairing was found
                paired = True
                break

            if paired:
                continue
            # no pairing found, create empty fields
            master_image.setdefault("caption", [])
            master_image.setdefault("keywords", [])
            # master_image.setdefault("context", [])
            # master_image.setdefault("general", [])
            masters.append(master_image)

        # update unassigned captions
        unassigned["captions"] = [caption_label for caption_label in captions if caption_label["label"] in not_assigned]

        return masters, unassigned

    def group_objects(self):
        """Pair captions with subfigures for each figure in exsclaim json"""
        self.display_info("Matching Image Objects to Caption Text\n")
        figures = +len(self.exsclaim_dict)
        for counter, figure in enumerate(self.exsclaim_dict, start=1):
            self.display_info(f">>> ({counter:,} of {figures:,}) Matching objects from figure: {figure}")

            figure_json = self.exsclaim_dict[figure]
            masters, unassigned = self.assign_captions(figure_json)

            figure_json |= {
                "master_images": masters,
                "unassigned": unassigned
            }

        self.display_info(">>> SUCCESS!\n")
        with open(self.results_directory / "exsclaim.json", "w") as f:
            dump(self.exsclaim_dict, f, indent=3)

        return self.exsclaim_dict

    # ## Save Methods ## #

    def to_file(self):
        """ Saves data to a csv and saves subfigures as individual images
        
        Modifies:
            Creates directories to save each subfigure
        """
        def write(image:dict, directory:Path, name_generator:Callable[[str], list[str]], order_c_copy=False):
            """
            An inner function designed to reduce the amount of needed code in the to_file function.

            :param dict image: The image JSON object.
            :param pathlib.Path directory: The directory where the image should be written.
            :param Callable[[str], list[str]] name_generator: How the names of the image files should be generated.
            The only parameter is the determined classification of the image.
            :param bool order_c_copy: If the path should be copied with order='C' as the only parameter.
            Added so the call for the master image would be the same as before.
            """
            directory.mkdir(exist_ok=True, parents=True)
            _class = image.get("classification", "uas")[:3].lower()
            _name = '_'.join(name_generator(_class)) + figure_extension

            # save image to file
            patch = crop_from_geometry(image['geometry'], figure)
            if order_c_copy:
                patch = patch.copy(order='C')

            try:
                cv_imwrite(str(directory / _name), patch)
            except Exception as err:
                self.logger.exception((f"Error in saving cropped master image of figure: {figure_root_name}. {err}"))

        self.display_info(f"Printing Master Image Objects to: {self.results_directory / 'images'}\n")
        for figure_name in self.exsclaim_dict:
            figure_root_name, figure_extension = splitext(figure_name) # figure_name is <figure_root_name>.<figure_extension>
            try:
                figure = np.asarray(Image.open(self.results_directory / "figures" / figure_name))
            except Exception as e:
                self.logger.exception((f"Error printing {figure_name} to file. It may be damaged! {e}"))
                figure = np.zeros((256,256))

            # save each master, inset, and dependent image as their own file in a directory according to label
            figure_dict = self.exsclaim_dict[figure_name]
            for master_image in figure_dict.get("master_images", []):
                # create a directory for each master image in <results_dir>/images/<figure_name>/<subfigure_label>
                directory = self.results_directory / "images" / figure_root_name / master_image['subfigure_label']['text']
                write(master_image, directory,
                      lambda _class: [figure_root_name, master_image['subfigure_label']['text'], _class], order_c_copy=True)

                # Repeat for dependents of the master image to file
                for dependent_id, dependent_image in enumerate(master_image.get("dependent_images", [])):
                    dependent_root_name = directory / "dependent"
                    write(dependent_image, dependent_root_name,
                          lambda _class: [master_name.split('par')[0] + f"dep{dependent_id}", _class])

                    # Repeat for insets of dependents of master image to file
                    for inset_id, inset_image in enumerate(dependent_image.get("inset_images", [])):
                        inset_root_name = dependent_root_name / "inset"
                        write(inset_root_name, inset_image,
                              lambda _class: [dependent_name.split(figure_extension)[0][0:-3] + f"ins{inset_id}", _class])

                # Write insets of masters to file
                for inset_id, inset_image in enumerate(master_image.get("inset_images", [])):
                    inset_root_name = directory / "inset"
                    write(inset_root_name, inset_image,
                          lambda _class: [master_name.split(figure_extension)[0][0:-3] + f"ins{inset_id}", _class])

        self.display_info(">>> SUCCESS!\n")

    def make_visualization(self, figure_name):
        """Save subfigures and their labels as images

        Args:
            figure_name (str): A path to the image (.png, .jpg, or .gif)
                file containing the article figure
        Modifies:
            Creates images and text files in <save_path>/extractions folders
            showing details about each subfigure
        """
        def draw_box(geometry, width=2, outline="green", **kwargs):
            coords = convert_labelbox_to_coords(geometry)
            bounding_box = tuple(map(int, coords))
            draw_full_figure.rectangle(bounding_box, width=width, outline=outline, **kwargs)
        
        (self.results_directory / "extractions").mkdir(exist_ok=True)
        figure_json = self.exsclaim_dict[figure_name]
        master_images = figure_json.get("master_images", [])
        # to handle older versions that didn't store height and width
        for master_image in master_images:
            if "height" not in master_image or "width" not in master_image:
                x1, y1, x2, y2 = convert_labelbox_to_coords(master_image["geometry"])
                master_image["height"] = y2 - y1
                master_image["width"] = x2 - x1

        image_buffer = 150
        height = int(sum([master["height"] + image_buffer for master in master_images]))
        width = int(max([master["width"] for master in master_images]))
        image_width = max(width, 500)
        image_height = height

        # Make and save images
        labeled_image = Image.new(mode="RGB", size=(image_width, image_height))
        draw = ImageDraw.Draw(labeled_image)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        except OSError as e:
            self.display_info(f"Could not create font DejaVuSans.ttf, using default. {e}")
            font = ImageFont.load_default()

        figures_path = self.results_directory / "figures"
        full_figure = Image.open(figures_path / figure_json["figure_name"]).convert("RGB")
        draw_full_figure = ImageDraw.Draw(full_figure)

        image_y = 0
        for subfigure_json in master_images:
            x1, y1, x2, y2 = convert_labelbox_to_coords(subfigure_json["geometry"])
            classification = subfigure_json["classification"]
            caption = "\n".join(subfigure_json.get("caption", []))
            caption = "\n".join(wrap(caption, width=100))

            subfigure_label = subfigure_json["subfigure_label"]["text"]
            scale_bar_label = subfigure_json.get("scale_label", "None")
            scale_bars = subfigure_json.get("scale_bars", [])

            # Draw bounding boxes on detected objects
            for scale_bar in scale_bars:
                draw_box(scale_bar["geometry"])
                if scale_bar["label"]:
                    draw_box(scale_bar["label"]["geometry"])

            label_geometry = subfigure_json["subfigure_label"]["geometry"]
            if label_geometry:
                draw_box(label_geometry)
            # Draw image
            subfigure = full_figure.crop((int(x1), int(y1), int(x2), int(y2)))
            text = f"Subfigure Label: {subfigure_label}\nClassification: {classification}\nScale Bar Label: {scale_bar_label}\nCaption:\n{caption}"
            text.encode("utf-8")
            labeled_image.paste(subfigure, box=(0, image_y))
            image_y += int(subfigure_json["height"])
            draw.text((0, image_y), text, fill="white", font=font)
            image_y += image_buffer

        del draw
        labeled_image.save(self.results_directory / "extractions" / figure_name)

    def draw_bounding_boxes(self, figure_name:str, draw_scale=True, draw_labels=False, draw_subfigures=False):
        """Save figures with bounding boxes drawn

        Args:
            figure_name (str): A path to the image (.png, .jpg, or .gif) file containing the article figure
            draw_scale (bool): If True, draws scale object bounding boxes
            draw_labels (bool): If True, draws subfigure label bounding boxes
            draw_subfigures (bool): If True, draws subfigure bounding boxes
        Modifies:
            Creates images and text files in <save_path>/boxes folders
            showing details about each subfigure
        """
        def append_bbox(geometry, lst:list):
            coords = convert_labelbox_to_coords(geometry)
            bounding_box = tuple(map(int, coords))
            lst.append(bounding_box)

        (self.results_directory / "boxes").mkdir(exist_ok=True)
        figure_json = self.exsclaim_dict[figure_name]
        master_images = figure_json.get("master_images", [])

        figures_path = self.results_directory / "figures"
        full_figure = Image.open(figures_path / figure_json["figure_name"]).convert("RGB")
        draw_full_figure = ImageDraw.Draw(full_figure)

        scale_objects = []
        subfigure_labels = []
        subfigures = []
        for subfigure_json in master_images:
            # collect subfigures
            subfigures.append(convert_labelbox_to_coords(subfigure_json["geometry"]))

            # Collect scale bar objects
            for scale_bar in subfigure_json.get("scale_bars", []):
                append_bbox(scale_bar["geometry"], scale_objects)
                if scale_bar["label"]:
                    append_bbox(scale_bar["label"]["geometry"], scale_objects)

            # Collect subfigure labels
            label_geometry = subfigure_json["subfigure_label"]["geometry"]
            if label_geometry:
                append_bbox(label_geometry, subfigure_labels)

        unassigned_scale = figure_json.get("unassigned", {}).get("scale_bar_objects", [])
        for scale_object in unassigned_scale:
            if "geometry" in scale_object:
                geometry = scale_object["geometry"]
            elif scale_object.get("label") is not None:
                geometry = scale_object["label"]["geometry"]
            else:
                continue

            append_bbox(geometry, scale_objects)

        # Draw desired bounding boxes
        if draw_scale:
            for bounding_box in scale_objects:
                draw_full_figure.rectangle(bounding_box, width=2, outline="green")

        if draw_labels:
            for bounding_box in subfigure_labels:
                draw_full_figure.rectangle(bounding_box, width=2, outline="green")

        if draw_subfigures:
            for bounding_box in subfigures:
                draw_full_figure.rectangle(bounding_box, width=2, outline="red")

        del draw_full_figure
        full_figure.save(self.results_directory / "boxes" / figure_name)

    def to_csv(self):
        """Places data in a set of csv's ready for database upload

        Modifies:
            Creates csv/ folder with article, figure, scalebar, scalebarlabel, subfigure, and subfigurelabel csvs.
        """
        exsclaim_json = self.exsclaim_dict
        csv_dir = self.results_directory / "csv"
        csv_dir.mkdir(exist_ok=True)

        articles = set()
        subfigures = set()
        classification_codes = {
            "microscopy": "MC",
            "diffraction": "DF",
            "graph": "GR",
            "basic_photo": "PH",
            "illustration": "IL",
            "unclear": "UN",
            "parent": "PT",
        }

        csv_info = {
           "article": [],
           "figure": [],
           "subfigure": [],
           "subfigure_label": [],
           "scale_label": [],
           "scale": []
        }

        for figure_name, figure_json in exsclaim_json.items():
            # create row for unique articles
            article_id = figure_json["article_name"]
            if article_id not in articles:
                csv_info["article"].append([
                    article_id,
                    figure_json["title"],
                    figure_json["article_url"],
                    figure_json["license"],
                    figure_json["open"],
                    figure_json.get("authors", ""),
                    figure_json.get("abstract", ""),
                ])
                articles.add(article_id)

            base_name = ".".join(figure_name.split(".")[:-1])
            figure_id = sub("_fig", "-fig", base_name)

            # create row for figure.csv
            csv_info["figure"].append([
                figure_id,
                figure_json["full_caption"],
                figure_json["caption_delimiter"],
                figure_json["image_url"],
                figure_json["figure_path"],
                figure_json["article_name"],
            ])

            # loop through subfigures
            for master_image in figure_json.get("master_images", []):
                subfigure_label = master_image["subfigure_label"]["text"]
                subfigure_coords = convert_labelbox_to_coords(master_image["geometry"])
                subfigure_id = f"{figure_id}-{subfigure_label}"
                if subfigure_id in subfigures:
                    continue

                subfigures.add(subfigure_id)
                csv_info["subfigure"].append([
                    subfigure_id,
                    classification_codes[master_image["classification"]],
                    master_image.get("height", None),
                    master_image.get("width", None),
                    master_image.get("nm_height", None),
                    master_image.get("nm_width", None),
                    *subfigure_coords,
                    "\t".join(master_image["caption"]),
                    str(master_image["keywords"]).replace("[", "{").replace("]", "}"),
                    # str(master_image["general"]).replace("[", "{").replace("]", "}"),
                    figure_id,
                ])

                if master_image["subfigure_label"].get("geometry", None):
                    subfigure_label_coords = convert_labelbox_to_coords(master_image["subfigure_label"]["geometry"])
                    csv_info["subfigure_label"].append([
                        master_image["subfigure_label"]["text"],
                        *subfigure_label_coords,
                        master_image["subfigure_label"].get(
                            "label_confidence", None
                        ),
                        master_image["subfigure_label"].get("box_confidence", None),
                        subfigure_id,
                    ])

                for i, scale_bar in enumerate(master_image.get("scale_bars", [])):
                    scale_bar_id = f"{subfigure_id}-{i}"
                    scale_bar_coords = convert_labelbox_to_coords(scale_bar["geometry"])
                    csv_info["scale"].append([
                        scale_bar_id,
                        *scale_bar_coords,
                        scale_bar.get("length", None),
                        scale_bar.get("label_line_distance", None),
                        scale_bar.get("confidence", None),
                        subfigure_id,
                    ])

                    if scale_bar.get("label", None) is None:
                        continue

                    scale_label = scale_bar["label"]
                    scale_label_coords = convert_labelbox_to_coords(scale_label["geometry"])
                    csv_info["scale_label"].append([
                        scale_label["text"],
                        *scale_label_coords,
                        scale_label.get("label_confidence", None),
                        scale_label.get("box_confidence", None),
                        scale_label.get("nm", None),
                        scale_bar_id,
                    ])

        # Save lists of rows to csvs
        for _type, rows in csv_info.items():
            with open(csv_dir / f"{sub('_', '', _type)}.csv", "w", encoding="utf-8", newline="") as file:
                csv_writer = writer(file)
                csv_writer.writerows(rows)

        return csv_dir

    def to_postgres(self, csv_dir):
        """Send csv files to a postgres database

        Modifies:
            Fills an existing postgres database with data from csv/ dir
        """
        from .utilities.postgres import Database

        with Database("exsclaim") as db:
            for table_name in ("article", "figure", "subfigure", "scale", "scalelabel", "subfigurelabel"):
                db.copy_from(csv_dir / f"{table_name}.csv", f"results.{table_name}")
                db.commit()
