import os
import logging
from typing import Iterable
from datetime import datetime

import yaml
from sqlalchemy import select

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QTreeWidgetItem,
    QTreeWidget,
    QSizePolicy,
    QDialogButtonBox,
    QFileDialog,
    QMessageBox,
)

from app.utils import load_ui
from app.utils.database import with_orm_session, Country, Plane, TravelPurposes
from app.models.agents.simulation import Simulation

from app.models.qt import SelectCountry
from app.core.global_states import global_state


class GeneratorWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(load_ui("generator.ui"), self)

        self.data_loaded: bool = False

        margin: int = 12

        self.new_window = None
        self.selected_countries = []
        self.selectCountryButton.clicked.connect(self.__open__select_country)

        # Age
        self.ageSlider.setValue((25, 50, 75))
        self.__update_spinboxes(self.ageSlider.value())
        self.ageSlider.valueChanged.connect(self.__update_spinboxes)

        self.childSpin.valueChanged.connect(self.__update_slider_from_spins)
        self.youngSpin.valueChanged.connect(self.__update_slider_from_spins)
        self.middleSpin.valueChanged.connect(self.__update_slider_from_spins)
        self.elderSpin.valueChanged.connect(self.__update_slider_from_spins)

        # Gender
        self.genderSlider.valueChanged.connect(self.genderSpin.setValue)
        self.genderSpin.valueChanged.connect(self.genderSlider.setValue)

        self.agentCountSlider.valueChanged.connect(self.agentCountSpin.setValue)
        self.agentCountSpin.valueChanged.connect(self.agentCountSlider.setValue)

        if self.centralwidget.layout():
            self.centralwidget.layout().setContentsMargins(
                margin, margin, margin, margin
            )

        planes = self.__get_planes()
        purposes = self.__get_purposes()

        self.__make_ui_tree_collapsible(self.modelsTree)
        self.__populate_ui_tree(
            self.modelsTree, (x for x in planes), "Select used plane models"
        )

        # self.__make_ui_tree_collapsible(self.countriesTree)
        # self.__populate_ui_tree(
        #     self.countriesTree, countries, "Select available countries"
        # )

        self.__make_ui_tree_collapsible(self.purposesTree)
        self.__populate_ui_tree(
            self.purposesTree, purposes, "Select needed passenger purposes"
        )

        # Buttons
        ok = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        if ok:
            ok.clicked.connect(self.ok)

        save = self.buttonBox.button(QDialogButtonBox.StandardButton.Save)
        if save:
            save.clicked.connect(self.save)

        open_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Open)
        if open_button:
            open_button.clicked.connect(self.load)

        cancel = self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel:
            cancel.clicked.connect(self.cancel)

        discard_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Discard)
        if discard_button:
            discard_button.clicked.connect(self.discard)

        # Data
        self.default_state = self.__set_simulation_state()
        self.current_state = None

        self.actionSave.triggered.connect(self.save)
        self.actionLoad.triggered.connect(self.load)
        self.actionReset.triggered.connect(self.discard)

        # self.

    def __set_simulation_state(self) -> Simulation:
        ages = self.get_ages()
        newSim: Simulation = Simulation(
            planes_count=self.agentCountSlider.value(),
            average_time_between=self.agentCountSpin.value(),
            allowed_models=self.get_selected_items(self.modelsTree),
            arriving_part=self.arrivingSpin.value(),
            internal_route=self.internalSpin.value(),
            countries=self.selected_countries,
            # passengers
            children=ages[0],
            young=ages[1],
            middle=ages[2],
            elderly=ages[3],
            gender_ratio=self.genderSpin.value(),
            purposes=self.get_selected_items(self.purposesTree),
            random_seed=self.randomSeed.value(),
        )
        return newSim

    def __adjust_height(self, tree_widget: QTreeWidget):
        height = 0
        for i in range(tree_widget.topLevelItemCount()):
            item = tree_widget.topLevelItem(i)
            height += tree_widget.visualItemRect(item).height()
            if item.isExpanded():
                for j in range(item.childCount()):
                    child = item.child(j)
                    height += tree_widget.visualItemRect(child).height()
        border_padding = 6
        tree_widget.setFixedHeight(height + border_padding)

    def __make_ui_tree_collapsible(self, tree_widget: QTreeWidget):
        tree_widget.setHeaderHidden(True)
        tree_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tree_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        tree_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        try:
            tree_widget.itemCollapsed.disconnect()
            tree_widget.itemExpanded.disconnect()
        except TypeError:
            pass

        tree_widget.itemCollapsed.connect(lambda: self.__adjust_height(tree_widget))
        tree_widget.itemExpanded.connect(lambda: self.__adjust_height(tree_widget))

        self.__adjust_height(tree_widget)

    def __populate_ui_tree(
        self, tree_widget: QTreeWidget, data: Iterable, title: str = "Select item"
    ):
        parent = QTreeWidgetItem(tree_widget)
        parent.setText(0, title)

        for item in data:
            child = QTreeWidgetItem(parent)
            child.setText(0, item)
            child.setFlags(
                child.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
            )
            child.setCheckState(0, Qt.CheckState.Unchecked)

        self.__adjust_height(tree_widget)

    def get_selected_items(self, tree_widget: QTreeWidget) -> list:
        checked_items = []
        for i in range(tree_widget.topLevelItemCount()):
            root = tree_widget.topLevelItem(i)
            for j in range(root.childCount()):
                child = root.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    checked_items.append(child.text(0))
        return checked_items

    def __update_spinboxes(self, values):
        min_scale = int(self.ageSlider.minimum())
        max_scale = int(self.ageSlider.maximum())

        diff_child, diff_young, diff_middle, diff_elder = self.get_ages()

        self.childSpin.blockSignals(True)
        self.youngSpin.blockSignals(True)
        self.middleSpin.blockSignals(True)
        self.elderSpin.blockSignals(True)

        self.childSpin.setMaximum(max_scale - min_scale)
        self.youngSpin.setMaximum(max_scale - min_scale)
        self.middleSpin.setMaximum(max_scale - min_scale)
        self.elderSpin.setMaximum(max_scale - min_scale)

        self.childSpin.setValue(diff_child)
        self.youngSpin.setValue(diff_young)
        self.middleSpin.setValue(diff_middle)
        self.elderSpin.setValue(diff_elder)

        self.childSpin.blockSignals(False)
        self.youngSpin.blockSignals(False)
        self.middleSpin.blockSignals(False)
        self.elderSpin.blockSignals(False)

    def __update_slider_from_spins(self):
        min_scale = int(self.ageSlider.minimum())
        max_scale = int(self.ageSlider.maximum())

        pos_1 = min_scale + self.childSpin.value()
        pos_2 = pos_1 + self.youngSpin.value()
        pos_3 = pos_2 + self.middleSpin.value()

        if (pos_3 + self.elderSpin.value()) > max_scale:
            if pos_3 > max_scale:
                pos_3 = max_scale
            if pos_2 > pos_3:
                pos_2 = pos_3
            if pos_1 > pos_2:
                pos_1 = pos_2

        new_values = (pos_1, pos_2, pos_3)

        self.ageSlider.blockSignals(True)
        self.ageSlider.setValue(new_values)
        actual_values = self.ageSlider.value()
        self.ageSlider.blockSignals(False)

        if new_values != actual_values:
            self.__update_spinboxes(actual_values)

    def get_ages(self) -> tuple:
        min_scale = int(self.ageSlider.minimum())
        max_scale = int(self.ageSlider.maximum())
        values = self.ageSlider.value()

        pos1 = int(values[0])
        pos2 = int(values[1])
        pos3 = int(values[2])

        diff_child = pos1 - min_scale
        diff_young = pos2 - pos1
        diff_middle = pos3 - pos2
        diff_elder = max_scale - pos3

        return (diff_child, diff_young, diff_middle, diff_elder)

    def __get_root_folder(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = current_dir
        while not os.path.exists(os.path.join(root_dir, "main.py")):
            parent_dir = os.path.dirname(root_dir)
            if parent_dir == root_dir:
                raise FileNotFoundError(
                    "Could not find project root containing main.py"
                )
            root_dir = parent_dir
        return root_dir

    def ok(self):
        self.current_state = self.__set_simulation_state()
        global_state.simulation = self.current_state
        self.close()

    def cancel(self):
        if self.current_state is None:
            self.current_state = self.default_state
        self.__apply_data(self.current_state)
        self.close()

    def save(self):
        if self.data_loaded:
            self.__save_to_file(self.__set_simulation_state())
        else:
            self.save_as()
        self.close()

    def save_as(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Preset As",
            f"{datetime.now().strftime("%Y%m%d_%H%M%S")}.json",
            "JSON (*.json);;All Files (*)",
        )
        if filepath:
            self.__save_to_file(
                self.__set_simulation_state(),
                filepath,
            )
        self.close()

    def __save_to_file(self, data: Simulation, path: str = None):
        if not isinstance(data, Simulation):
            logging.error("Can't save sim preset")
            return
        if path is None:
            dirpath = self.__get_root_folder()
            path = os.path.join(dirpath, "data/simulation_presets")
            path = os.path.join(
                path, f"{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"
            )
        json_string = data.model_dump_json(indent=4)
        with open(path, "w", encoding="UTF-8") as f:
            f.write(json_string)

    def load(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "JSON (*.json);;All Files (*)"
        )
        if not filepath:
            return
        sim = None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                file_content = f.read()
            sim = Simulation.model_validate_json(file_content)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read file: {e}")
            self.close()
        self.__apply_data(sim)

    def discard(self):
        self.__apply_data(self.default_state)

    def __apply_data(self, sim: Simulation):
        if sim is None:
            logging.error("TRYING TO APPLY EMPTY SIMULATION")
            return
        self.agentCountSlider.setValue(sim.planes_count)
        self.agentCountSpin.setValue(sim.average_time_between)
        self.arrivingSpin.setValue(sim.arriving_part)
        self.internalSpin.setValue(sim.internal_route)
        self.genderSpin.setValue(sim.gender_ratio)

        self.childSpin.setValue(sim.children)
        self.youngSpin.setValue(sim.young)
        self.middleSpin.setValue(sim.middle)
        self.elderSpin.setValue(sim.elderly)

        self.__set_selected_items(self.modelsTree, sim.allowed_models)
        self.__set_selected_items(self.countriesTree, sim.countries)
        self.__set_selected_items(self.purposesTree, sim.purposes)

    def __load_file(self, filename: str, field: str):
        try:
            with open(f"data/{filename}.yaml", "r", encoding="utf-8") as file:
                return yaml.safe_load(file)[field]
        except FileNotFoundError:
            logging.error(f'File "{filename}" not found')
            return None

    def __open__select_country(self):
        if self.new_window is None:
            self.new_window = SelectCountry(self, self.__get_countries())
            self.new_window.submitted.connect(self.__receive_list)
            self.new_window.show()
        else:
            # self.new_window.raise_()
            self.new_window.activateWindow()

    def __receive_list(self, data_list):
        self.selected_countries = data_list

    # @with_orm_session
    # def __get_countries(self, session=None):
    #     statement = select(Company).options(joinedload(Company.country_name))
    #     data = session.scalars(statement).all()
    #     result = sorted(set(x.country_name.name for x in data))
    #     print(*result, sep="\n")
    #     return result

    # TODO
    # 1) Get companies selector
    # 2) Add tab for each company
    # 3) Serialize that shit for Simulation class
    # 4) make Generate button actually make agents

    @with_orm_session
    def __get_countries(self, session=None):
        statement = select(Country)
        data = session.scalars(statement).all()
        result = sorted(set(x.name for x in data))
        return result

    @with_orm_session
    def __get_planes(self, session=None):
        statement = select(Plane)
        data = session.scalars(statement).all()
        result = sorted(set(x.name for x in data))
        return result

    @with_orm_session
    def __get_purposes(self, session=None):
        statement = select(TravelPurposes)
        data = session.scalars(statement).all()
        result = sorted(set(x.purpose for x in data))
        return result

    def __set_selected_items(self, tree_widget: QTreeWidget, allowed_items: list[str]):
        tree_widget.blockSignals(True)

        def recursive_check(item: QTreeWidgetItem, depth: int):
            if depth == 0:
                item.setData(0, Qt.ItemDataRole.CheckStateRole, None)
            else:
                if item.text(0) in allowed_items:
                    item.setCheckState(0, Qt.CheckState.Checked)
                else:
                    item.setCheckState(0, Qt.CheckState.Unchecked)
            for i in range(item.childCount()):
                recursive_check(item.child(i), depth + 1)

        for i in range(tree_widget.topLevelItemCount()):
            recursive_check(tree_widget.topLevelItem(i), depth=0)

        tree_widget.blockSignals(False)
