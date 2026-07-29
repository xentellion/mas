import os
import logging

# import random
import secrets
from datetime import datetime

import yaml
from sqlalchemy import select

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QMainWindow,
    QDialogButtonBox,
    QFileDialog,
    QMessageBox,
)

from app.utils import load_ui
from app.utils.database import with_orm_session, Country, Company
from app.models.agents.simulation import Simulation

from app.models.qt import SelectCountry, SelectCompany, CompanyData
from app.core.global_states import global_state


RANDOM_MAX_ORDER = 31
PRESET_PATH = "data/simulation_presets"


class GeneratorWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(load_ui("generator.ui"), self)

        self.data_loaded: bool = False

        self.country_window = None
        self.company_window = None
        # Random seed
        self.randomSeed.setMaximum((1 << RANDOM_MAX_ORDER) - 1)
        self.randomSeedButton.clicked.connect(self.__generate_seed)

        # Select countries
        self.selected_countries = []
        self.selectCountryButton.clicked.connect(self.__open__select_country)

        # Select companies
        self.selected_companies = []
        self.selectCompaniesButton.setEnabled(False)
        self.selectCompaniesButton.clicked.connect(self.__open__select_companies)

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

    def __set_simulation_state(self) -> Simulation:
        new_sim: Simulation = Simulation(
            random_seed=self.randomSeed.value(),
            countries=self.selected_countries,
            companies=self.__serialize_companies(),
        )
        return new_sim

    def __generate_seed(self):
        new_seed = secrets.randbits(RANDOM_MAX_ORDER)
        self.randomSeed.setValue(new_seed)

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
            os.path.join(
                PRESET_PATH,
                f"{datetime.now().strftime("%Y%m%d_%H%M%S")}.json",
            ),
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
            path = os.path.join(
                dirpath,
                PRESET_PATH,
                f"{datetime.now().strftime("%Y%m%d_%H%M%S")}.json",
            )
        json_string = data.model_dump_json(indent=4)
        with open(path, "w", encoding="UTF-8") as f:
            f.write(json_string)

    def load(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open File", PRESET_PATH, "JSON (*.json);;All Files (*)"
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
        self.randomSeed.setValue(sim.random_seed)
        self.selected_countries = sim.countries
        self.selected_companies = list(sim.companies.keys())
        self.selectCompaniesButton.setEnabled(bool(self.selected_companies))
        self.__recieve_company()

        for index in range(self.companyTabs.count()):
            tab_name = self.companyTabs.tabText(index)
            tab_content = self.companyTabs.widget(index)
            tab_content.load_data(sim.companies[tab_name])

    def __load_file(self, filename: str, field: str):
        try:
            with open(f"data/{filename}.yaml", "r", encoding="utf-8") as file:
                return yaml.safe_load(file)[field]
        except FileNotFoundError:
            logging.error(f'File "{filename}" not found')
            return None

    def __open__select_country(self):
        if self.country_window is None:
            self.country_window = SelectCountry(
                self, self.__get_countries(), self.selected_countries
            )
            self.country_window.submitted.connect(self.__recieve_country)
            self.country_window.show()
        else:
            # self.country_window.raise_()
            self.country_window.activateWindow()

    def __open__select_companies(self):
        if self.company_window is None:
            self.company_window = SelectCompany(
                self, self.__get_companies(), self.selected_companies
            )
            self.company_window.submitted.connect(self.__recieve_company)
            self.company_window.show()
        else:
            # self.company_window.raise_()
            self.company_window.activateWindow()

    def __recieve_country(self, data_list):
        self.selected_countries = data_list
        self.selectCompaniesButton.setEnabled(bool(data_list))
        companies = self.__get_companies()
        for index in range(self.companyTabs.count() - 1, -1, -1):
            current_text = self.companyTabs.tabText(index)
            if current_text not in companies:
                widget_to_remove = self.companyTabs.widget(index)
                self.companyTabs.removeTab(index)
                widget_to_remove.deleteLater()
        self.selected_companies = [
            item for item in self.selected_companies if item in companies
        ]

    def __recieve_company(self, data_list=None):
        if data_list is not None:
            self.selected_companies = data_list

        for index in range(self.companyTabs.count() - 1, -1, -1):
            current_text = self.companyTabs.tabText(index)
            if current_text not in self.selected_companies:
                widget_to_remove = self.companyTabs.widget(index)
                self.companyTabs.removeTab(index)
                widget_to_remove.deleteLater()

        existing_tabs = {
            self.companyTabs.tabText(i) for i in range(self.companyTabs.count())
        }

        for tab_name in self.selected_companies:
            if tab_name not in existing_tabs:
                # !!!!!!!!!!!!!!!!!!!!!!!!!
                new_tab_widget = CompanyData(tab_name)
                self.companyTabs.addTab(new_tab_widget, tab_name)

    def __serialize_companies(self):
        all_data = {}
        for index in range(self.companyTabs.count()):
            tab_name = self.companyTabs.tabText(index)
            tab_content = self.companyTabs.widget(index)
            all_data[tab_name] = tab_content.save_data()
        return all_data

    def __deserialize_companies(self):
        pass

    # TODO
    # 3) Serialize that shit for Simulation class
    # 4) make Generate button actually make agents

    @with_orm_session
    def __get_countries(self, session=None):
        statement = select(Country)
        data = session.scalars(statement).all()
        result = sorted(set(x.name for x in data))
        return result

    @with_orm_session
    def __get_companies(self, session=None):
        statement = (
            select(Company)
            .join(Country)
            .where(Country.name.in_(self.selected_countries))
            .distinct()
        )
        data = session.scalars(statement).all()
        result = sorted(set(x.name for x in data))
        return result
