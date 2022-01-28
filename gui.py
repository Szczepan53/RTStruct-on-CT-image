import os
import random
import sys

import matplotlib
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

import utils

"""Moduł odpowiadający za graficzny interfejs użytkownika pozwalający na załadowanie pliku DICOM z danymi obrazowymi pojedynczego slice'a 
i pliku DICOM z danymi RTStruct w celu naniesienia konturów struktur na obraz załadowanego slice'a.

Wymagane zewnętrzne biblioteki
-----------------------------
PyQt5
matplotlib
"""

# Konfiguracja wykorzystywanego backendu matplotliba
matplotlib.use(backend="Qt5Agg")
# Konfiguracja stylu matplotliba
matplotlib.rc("axes", edgecolor="#dddddd", labelcolor="#dddddd", titlecolor="#dddddd")
matplotlib.rc("xtick", color="#dddddd")
matplotlib.rc("ytick", color="#dddddd")


def catch_exceptions(t, val, tb):
    """Wyświetla błędy w okienku dialogowym."""

    QMessageBox.critical(None, "An exception was raised", "Exception type: {}".format(t))
    old_hook(t, val, tb)


# Zgłoszonie błędu spowoduje wywołanie funkcji catch_exceptions
old_hook = sys.excepthook
sys.excepthook = catch_exceptions


class Canvas(FigureCanvasQTAgg):
    """Klasa obiektu płótna, na którym rysowane będą obrazy z konturami."""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        FigureCanvasQTAgg.__init__(self, fig)


class MainWindow(QMainWindow):
    """Klasa reprezentująca okno główne programu.

    Atrybuty
    --------
    canvas: Canvas
        płótno na którym rysowane będą obrazy z nałożonymi konturami struktur
    currentRT: list
        lista obiektów utils.Structure wczytana z ostatniego, załadowanego pliku DICOM RTStruct
    dicom: utils.Slice
        obecnie załadowany slice danych obrazowych
    dicom_path: str
        ścieżka do pliku DICOM z ostatnio załadowanym slicem
    upperLabel: QLabel
        etykieta umieszczona na górze okna głównego, służy do wyświetlania użytkownikowi komunikatów
    toolbar: NavigationToolbar2QT
        pasek narzędziowy matplotliba do operowania na wyswietlanym wykresie/obrazie
    isImageSet: bool
        flaga używana przy wyświetlaniu bądź chowaniu etykiety upperLabel

    """

    def __init__(self, *args, **kwargs):
        """Inicjalizacja okna głównego, ustawienie wymiarów, osadzenie widgetów płótna, panelu sterowania obrazem, paska menu."""
        QMainWindow.__init__(self, *args, **kwargs)
        self.setGeometry(200, 200, 720, 720)
        self.setWindowTitle("RTStruct mapping app")

        self.canvas = FigureCanvasQTAgg(plt.figure(figsize=(10, 10), facecolor="#232326"))
        self.currentRT = self.currentPatientName = None
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        self.layout = QVBoxLayout()
        self.upperLabel = QLabel("Please load CT image or RTStruct file from File menu")
        self.upperLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.isImageSet = False
        self.layout.addWidget(self.upperLabel)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.dicom_path = None
        self.dicom = None
        self.setCentralWidget(self.canvas)
        self._createActions()
        self._createMenuBar()

        widget = QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

    def _createMenuBar(self):
        """Inicjalizacja menuBara na górze okna."""
        menubar = self.menuBar()
        fileMenu = QMenu("&File", self)
        menubar.addMenu(fileMenu)

        fileMenu.addAction(self.openCTAction)
        fileMenu.addAction(self.openRTStructAction)

    def _createActions(self):
        """Podpięcie metod obsługi wybranej opcji z menu File menuBara."""
        self.openCTAction = QAction("Open CT File...", self)
        self.openCTAction.triggered.connect(self.openCTFile)
        self.openRTStructAction = QAction("Open RTStruct File...", self)
        self.openRTStructAction.triggered.connect(self.openRTStructFile)

    def openCTFile(self):
        """Metoda odpowiadająca za załadowanie nowego pliku DICOM z danymi obrazowymi slice'a."""

        fileFilter = "DICOM File (*.dcm)"
        nextCTFile = QFileDialog.getOpenFileName(parent=self, caption="Select DICOM CT file", directory=os.getcwd(),
                                                 filter=fileFilter)[0]

        if nextCTFile == "":  # Nic nie rób w przypadku kliknięcia 'cancel' w oknie dialogowym wyboru pliku
            return

        self.setWindowTitle(self.windowTitle() + " - loading...")  # Daj znać użytkownikowi, że w tle trwa ładowanie
        self.repaint()

        try:
            self.plot_new_dicom_image(nextCTFile, self.currentRT)
        except utils.NotCTImageFileException as ex:
            self.wrongFileMessage(ex)

        finally:
            self.setWindowTitle(self.windowTitle().split("-")[0].rstrip())  # Ładowanie pliku zakończone

    def openRTStructFile(self):
        """Metoda odpowiadająca za załadowanie nowego pliku DICOM z RTStruct."""

        fileFilter = "DICOM File (*.dcm)"
        nextRTStructFile = QFileDialog.getOpenFileName(parent=self, caption="Select DICOM RTStruct file",
                                                       directory=os.getcwd(), filter=fileFilter)[0]

        if nextRTStructFile == "":  # Nic nie rób w przypadku kliknięcia 'cancel' w oknie dialogowym wyboru pliku
            return

        """Jeśli RTStruct istnieje był już wcześniej ładowany to pobierz go ze słownika w postaci krotki
         (lista obiektów Structure, nazwa pacjenta) lub pobierz krotke (None, None)."""
        previouslyLoaded = utils.loaded_RTStructs.get(nextRTStructFile, (None, None))
        newRT = previouslyLoaded[0]

        if newRT is None:  # Jeśli RTStruct nie był wcześniej ładowany to spróbuj go załadować
            try:
                newRT, rtPatientName = utils.read_rtstruct(nextRTStructFile)
            except utils.NotRTStructFileException as ex:
                self.wrongFileMessage(ex)
                return
            self.currentPatientName = rtPatientName
        else:
            self.currentPatientName = previouslyLoaded[1]

        self.currentRT = newRT
        if self.dicom is not None:  # Jest załadowany do pamięci jakiś plik DICOM z danymi obrazowymi?
            ctPatientName = self.dicom.dcm.PatientName
            if self.currentPatientName == ctPatientName:    # Plik RTStruct pasuje do pacjenta?
                # wykorzystaj załadowany plik ct
                self.plot_same_dicom_image(newRT)
                return
            else:
                # wyczyść obraz
                self.canvas.figure.clear()
                ax = self.canvas.figure.subplots()
                ax.set_facecolor("#232326")
                self.canvas.draw()
                print(f"Incompatible patient's names: CT={ctPatientName} | RT={self.currentPatientName}",
                      file=sys.stderr)

        # Wyświetl na upperLabel komunikat do użytkownika z prośbą o wczytanie
        self.upperLabel.setText(f"Please load CT image data for patient: {self.currentPatientName}")
        self.upperLabel.setVisible(True)
        self.isImageSet = False
        # Poproś o załadowanie pasującego do RTStructa pliku z danymi obrazowymi
        self.loadCTFileDialog(self.currentPatientName)

    def wrongFileMessage(self, ex):
        """Metoda wyświetlająca okienko dialogowe w przypadku załadowania nieprawidłowego pliku."""
        errorMessage = QMessageBox()
        errorMessage.setIcon(QMessageBox.Critical)
        errorMessage.setWindowTitle("Wrong DICOM File")
        errorMessage.setText(str(ex))
        errorMessage.exec()

    def loadCTFileDialog(self, rtPatientName):
        """
        Wyświetla dialog z prośbą o załadowanie pasującego pliku DICOM z danymi obrazowymi.
        :param rtPatientName: nazwa pacjenta, dla którego potrzebne są dane RTStruct
        :return: None
        """
        messageBox = QMessageBox()
        messageBox.setIcon(QMessageBox.Information)
        messageBox.setText(f"Please load CT image data for patient: {rtPatientName}")
        messageBox.setWindowTitle("RTStruct data patient changed")
        messageBox.setStandardButtons(QMessageBox.Open | QMessageBox.Cancel)
        messageBox.buttonClicked.connect(self.buttonClickHandlerCT)
        messageBox.exec()

    def loadRTStructFileDialog(self, ctPatientName):
        """
        Wyświetla dialog z prośbą o załadowanie pasującego pliku DICOM z danymi RTStruct.
        :param ctPatientName: nazwa pacjenta, dla którego potrzebne są dane obrazowe
        :return: None
        """
        messageBox = QMessageBox()
        messageBox.setIcon(QMessageBox.Information)
        messageBox.setText(f"Please load RTStruct contour data for patient: {ctPatientName}")
        messageBox.setWindowTitle("CT image data patient changed")
        messageBox.setStandardButtons(QMessageBox.Open | QMessageBox.Cancel)
        messageBox.buttonClicked.connect(self.buttonClickHandlerRT)
        messageBox.exec()

    def buttonClickHandlerCT(self, i):
        """Obsługa opcji open wybranej w oknie dialogowym powstałym w wyniku wywołania metody loadCTFileDialog."""
        if i.text() == "Open":
            i.close()
            self.openCTFile()

    def buttonClickHandlerRT(self, i):
        """Obsługa opcji open wybranej w oknie dialogowym powstałym w wyniku wywołania metody loadRTStructFileDialog."""
        if i.text() == "Open":
            self.openRTStructFile()

    def plot_new_dicom_image(self, dicom_path, rt_struct):
        """
        Metoda odpowiedzialna za załadowanie i wyświetlenie nowego slice'a wraz z konturami struktur pobranymi
        z pliku RTStruct.
        :param dicom_path: ścieżka do pliku DICOM z danymi obrazowymi
        :param rt_struct: ścieżka do pliku DICOM z danymi RTStruct
        :return: nowo utworzony obiekt klasy utils.Slice
        """
        # if not self.isImageSet:
            # self.upperLabel.setText("/".join(dicom_path.split("/")[-4:]))

        self.dicom = utils.Slice(dicom_path)
        self.dicom_path = dicom_path
        ctPatientName = self.dicom.dcm.PatientName
        if ctPatientName == self.currentPatientName:    # Pacjent w RTStruct zgodny za pacjentem z danych obrazowych?
            self.dicom.load_RTStruct(rt_struct)     # Wczytaj kontury struktur do utworzonego obiektu Slice
            self.canvas.figure.clear()
            ax = self.canvas.figure.subplots()
            self.dicom.set_axes(ax)
            self.dicom.draw_structures()    # Wyświetl obraz slice'a wraz z naniesionymi konturami struktur
            self.canvas.draw()
            self.setLabel(self.dicom_path)
        else:   # Wyczyść płótno i poproś o załadowanie pasującego pliku DICOM z danymi RTStruct
            self.currentPatientName = ctPatientName
            # wyczyść obraz
            self.canvas.figure.clear()
            ax = self.canvas.figure.subplots()
            ax.set_facecolor("#232326")
            self.upperLabel.setText(f"Please load RTStruct contour data for patient: {ctPatientName}")
            # self.upperLabel.setVisible(True)
            # self.isImageSet = False
            self.canvas.draw()
            print(f"Incompatible patient's names: CT={ctPatientName} | RT={self.currentPatientName}",
                  file=sys.stderr)
            self.loadRTStructFileDialog(ctPatientName)

        return self.dicom

    def plot_same_dicom_image(self, rt_struct):
        """Metoda odpowiedzialna za załadowanie danych RTStruct do obecnie załadowanego slice'a i wyświetlenie na nim
         nowo naniesionych konturów."""

        # if not self.isImageSet:
        self.setLabel(self.dicom_path)

        self.dicom.load_RTStruct(rt_struct)
        self.canvas.figure.clear()
        ax = self.canvas.figure.subplots()
        self.dicom.set_axes(ax)
        self.dicom.draw_structures(random.uniform(1, 2))  # losowa grubosc konturów żeby było widać zmianę RTStructa
        self.canvas.draw()

    def setLabel(self, path):
        """Ukryj upperLabel jeśli wyświetlany jest jakiś slice."""
        self.upperLabel.setText("/".join(path.split("/")[-4:]))
        self.isImageSet = True


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
