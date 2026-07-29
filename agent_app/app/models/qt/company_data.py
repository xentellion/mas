from typing import Iterable

from sqlalchemy import select
from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QTreeWidget,
    QSizePolicy,
    QTreeWidgetItem,
)

from app.utils import load_ui
from app.utils.database import with_orm_session, Plane, TravelPurposes
from app.models.agents.simulation import SimulationCompany


class CompanyData(QWidget):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(load_ui("company.ui"), self)

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

        planes = self.__get_planes()
        purposes = self.__get_purposes()

        self.__make_ui_tree_collapsible(self.modelsTree)
        self.__populate_ui_tree(
            self.modelsTree,
            (x for x in planes),
            "Select used plane models",
        )

        self.__make_ui_tree_collapsible(self.purposesTree)
        self.__populate_ui_tree(
            self.purposesTree,
            purposes,
            "Select needed passenger purposes",
        )

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

    def get_selected_items(self, tree_widget: QTreeWidget) -> list:
        checked_items = []
        for i in range(tree_widget.topLevelItemCount()):
            root = tree_widget.topLevelItem(i)
            for j in range(root.childCount()):
                child = root.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    checked_items.append(child.text(0))
        return checked_items

    def save_data(self):
        ages = self.get_ages()
        tab_data = SimulationCompany(
            # passengers
            children=ages[0],
            young=ages[1],
            middle=ages[2],
            elderly=ages[3],
            gender_ratio=self.genderSpin.value(),
            purposes=self.get_selected_items(self.purposesTree),
            # planes
            planes_count=self.agentCountSlider.value(),
            average_time_between=self.agentCountSpin.value(),
            allowed_models=self.get_selected_items(self.modelsTree),
            arriving_part=self.arrivingSpin.value(),
            internal_route=self.internalSpin.value(),
        )
        return tab_data

    def load_data(self, sim: SimulationCompany):
        self.childSpin.setValue(sim.children)
        self.youngSpin.setValue(sim.young)
        self.middleSpin.setValue(sim.middle)
        self.elderSpin.setValue(sim.elderly)
        self.genderSpin.setValue(sim.gender_ratio)
        self.__set_selected_items(self.purposesTree, sim.purposes)

        self.agentCountSlider.setValue(sim.planes_count)
        self.agentCountSpin.setValue(sim.average_time_between)
        self.__set_selected_items(self.modelsTree, sim.allowed_models)
        self.arrivingSpin.setValue(sim.arriving_part)
        self.internalSpin.setValue(sim.internal_route)
