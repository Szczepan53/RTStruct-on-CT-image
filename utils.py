import sys
from matplotlib import pyplot as plt
import numpy as np
import pydicom
import glob
import os
from shapely.geometry import Polygon

"""Moduł zajmujący się wczytywaniem, przetwarzaniem, kombinowaniem i rysowanie, danych obrazowych z DICOM i danych konturowych RTStruct.

Wymagane zewnętrzne biblioteki
-----------------------------
matplotlib
numpy
pydicom
shapely
"""

# Stałe ze ścieżkami do plików DICOM używane przy testowaniu biblioteki w konsoli pythona

# DICOM_DIR_PATH1 = r"Temat6/Pediatric-CT-SEG-02AC04B6/09-21-2005-NA-CT-35474/4.000000-CT-08387"
# RTSTRUCT_DIR_PATH1 = r"Temat6/Pediatric-CT-SEG-02AC04B6/09-21-2005-NA-CT-35474/2.000000-RTSTRUCT-86390"
#
# DICOM_DIR_PATH2 = r"Temat6/Pediatric-CT-SEG-02BA6CE5/02-12-2005-NA-CT-25835/4.000000-CT-82361"
# RTSTRUCT_DIR_PATH2 = r"Temat6/Pediatric-CT-SEG-02BA6CE5/02-12-2005-NA-CT-25835/2.000000-RTSTRUCT-77839"
#
# DICOM_DIR_PATH3 = r"Temat6/Pediatric-CT-SEG-0296A78B/02-22-2006-NA-CT-89856/4.000000-CT-91325"
# RTSTRUCT_DIR_PATH3 = r"Temat6/Pediatric-CT-SEG-0296A78B/02-22-2006-NA-CT-89856/2.000000-RTSTRUCT-49735"
#
# DIR1_DICOMS = glob.glob(os.path.join(DICOM_DIR_PATH1, "*dcm"))
# DIR1_RTSTRUCTS = glob.glob(os.path.join(RTSTRUCT_DIR_PATH1, "*dcm"))
# DIR2_DICOMS = glob.glob(os.path.join(DICOM_DIR_PATH2, "*dcm"))
# DIR2_RTSTRUCTS = glob.glob(os.path.join(RTSTRUCT_DIR_PATH2, "*dcm"))
# DIR3_DICOMS = glob.glob(os.path.join(DICOM_DIR_PATH3, "*dcm"))
# DIR3_RTSTRUCTS = glob.glob(os.path.join(RTSTRUCT_DIR_PATH3, "*dcm"))

"""Przetwarzanie RTStructu trwa długo dlatego raz wczytane przechowywane są w słowniku po nazwie pliku (taki jakby cache)
pozwalający znacznie przyspieszyć wymianę RTStructów w czasie działania programu."""
loaded_RTStructs = {}


class WrongDICOMFileException(Exception):
    """Superklasa wyjątków zgłaszanych w przypadku problemów z przetwarzaniem pliku DICOM."""
    pass


class NotRTStructFileException(WrongDICOMFileException):
    """Wyjątek zgłaszany w przypadku załadowania pliku DICOM niezawierającego danych RTStruct jako pliku RTStruct."""
    pass


class NotCTImageFileException(WrongDICOMFileException):
    """Wyjątek zgłaszany w przypadku załadowania pliku DICOM niezawierającego danych obrazowych jako pliku CT image."""
    pass


class Structure:
    """Klasa reprezentująca pojedynczą strukturę - np. kości, skóra, płuco lewe, pęcherz itp."""

    def __init__(self, name=None, color=None, number=None, contours=None):
        """
        Inicjalizacja obiektu klasy Structure
        :param name: nazwa struktury reprezentowanej przez przechowywane w obiekcie kontury
        :param color: preferowany kolor konturów struktury
        :param number: numer struktury w danym pliku RTStruct
        :param contours: kontury danej struktury w postaci macierzy 3D punktów (we współrzędnych odnoszących się
         do położenia pacjenta w przestrzeni, a nie we współrzędnych odnoszących się do pikseli obrazu)
        """
        self.name = name
        self.color = color
        self.number = number
        self.contours = contours

    def __repr__(self):
        len_points = len(self.contours) if self.contours is not None else 0
        return f"<name={self.name}, color={self.color}, number={self.number}, contours: {len_points} contours>"


class Slice:
    """Klasa reprezentująca plik z danymi obrazowymi DICOM (pojedynczy slice) w kombinacji z pasującymi do niego
     strukturami z RTStruct."""

    def __init__(self, file_path: str = None):
        """
        Inicjalizacja obiektu klasy DicomFile
        :param file_path: ścieżka pliku DICOM zawierającego dane obrazowe
        """
        if file_path is not None:
            self.file_path = file_path
            self.dcm = pydicom.dcmread(file_path)
            try:
                self.dcm.PixelData  # Jeśli załadowany DICOM nie ma atrybutu PixelData to nie zawiera danych obrazowych
            except AttributeError:
                raise NotCTImageFileException("Passed DICOM file is not CT image data file")
            self.z = self.dcm.ImagePositionPatient[2]
            self.structures = {}
            self.axes = plt  # Podpięcie pyplota do utworzonego obiektu - wykorzystywane przy testowaniu modułu.

    def __repr__(self):
        return f"<file_path={self.file_path}, z={self.z}, structures={len(self.structures)}>"

    def add_structure(self, structure):
        """
        Metoda wybierająca z przekazanego obiektu struktury pasujące do slice'a reprezentowanego przez self.
        :param structure: obiekt klasy Structure, którego kontury próbujemy sparować ze slicem self
        :return: None
        """

        # Tworzymy nowy obiekt Structure, który będzie zawierał wyłącznie pasujące do slice'a self kontury
        newStructure = Structure(structure.name, np.divide(structure.color, 255), structure.number, [])

        for contour_z in structure.contours:
            """Sprawdzenie, czy kontur pasuje do slice'a self (porównanie składowej 'z' punktów konturu ze składową 'z'
            orientacji pacjenta danego slice'a z uwzględnieniem grubości slice'ów)."""
            if not np.isclose(contour_z, self.z, atol=self.dcm.SliceThickness / 2, rtol=0):
                print(f"contour_z = {contour_z} don't match file {self.file_path} | z coord: {self.z}", file=sys.stderr)
                continue
            print(f"contour_z = {contour_z} MATCHES file {self.file_path} | z coord: {self.z}")

            for contour in structure.contours[contour_z]:

                # Przekształcenie wektora punktów konturu w macierz 3D
                contour = np.array(contour).reshape(-1, 3)
                """Przejście ze współrzędnych 'przestrzennych' na odpowiadające punktom piksele 
                obrazu + opuszczenie składowej 'z' punktów konturu (sprawdziliśmy już, że dany kontur pasuje do slice'a
                więc składowe 'z' punktów są dalej zbędne)."""
                nodes2D = (contour[:, :2] - self.dcm.ImagePositionPatient[:2]) / self.dcm.PixelSpacing
                newStructure.contours.append(nodes2D)

        if len(newStructure.contours) > 0:
            """Jeśli nowa struktura zawiera kontury to dodaj ją do słownika struktur
             slice'a - jako klucz wykorzystaj numer struktury pobrany uprzednio z pliku RTStruct."""
            self.structures[newStructure.number] = newStructure

    def load_RTStruct(self, rtstruct, clear_current_structures: bool = True):
        """
        Metoda ładująca obiekt listę obiektów Structure do slice'a self.
        :param rtstruct: lista obiektów klasy Structure utworzona uprzednio na podstawie pliku DICOM z danymi RTStruct
        :param clear_current_structures: flaga decydująca, czy wyczyścić słownik z uprzednio załadowanych struktur
        :return: None
        """
        if clear_current_structures:
            # Wyczyść słownik struktur z załadowanych uprzednio struktur
            self.structures.clear()
        for struct in rtstruct:
            self.add_structure(struct)

    def draw_contour(self, contour, color='red', name: str = 'nolabel', lw: float = 0.5):
        """
        Metoda rysująca na obrazie pojedynczy kontur w postaci wielokątu przy wykorzystaniu pyplota.
        :param contour: kontur struktury reprezentowany przez macierz 2D punktów
        :param color: żądany kolor konturu dla danej struktury
        :param name: nazwa danej struktury do wyświetlenia w legendzie
        :param lw: grubość linii konturu
        :return: None
        """
        # Przekształcenie luźnych punktów z macierzy 2D na sekwencję wierzchołków wielokąta odpowiadającego konturowi
        x, y = Polygon(contour).exterior.xy

        if name == 'nolabel':
            return self.axes.plot(x, y, c=color, lw=lw)
        else:
            return self.axes.plot(x, y, c=color, label=name, lw=lw)

    def draw_structure(self, structure, lw: float = 0.5):
        """
        Metoda rysująca na obrazie wszystkie kontury zawarte w przekazanym obiekcie structure.
        :param structure: obiekt klasy Structure, którego kontury mają zostać narysowane na obrazie
        :param lw: grubość linii konturu
        :return: None
        """
        # Wyciągnięcie pierwszej macierzy 2D konturu w celu zapobiegnięcia duplikacji wpisów w legendzie.
        first_contour, *contours = structure.contours
        self.draw_contour(first_contour, structure.color, structure.name, lw) # Label ustawiany tylko raz na strukturę.
        for contour in contours:
            self.draw_contour(contour, structure.color, lw=lw) # W kolejnych konturach tej samej struktury nie ustawiamy labela.

    def draw_structures(self, lw: float = 0.9):
        """
        Metoda rysująca obraz slice'a + kontury wszystkich struktur skojarzonych ze slicem self (kontury wszystkich struktur
        załadowanych uprzednio do słownika self.contours przy wykorzystaniu metod self.loadRTStruct lub self.add_structure).
        :param lw: grubość linii konturu
        :return: None
        """
        self.axes.imshow(self.dcm.pixel_array, plt.cm.bone)
        for structure in self.structures.values():
            self.draw_structure(structure, lw)
        self.axes.legend()
        self.axes.set_xlabel("x [mm]")
        self.axes.set_ylabel("y [mm]")
        self.axes.set_title(f"{self.dcm.PatientName} | z = {self.z}mm")

    def draw_structures_separately(self, lw: float = 0.5):
        """
        Metoda rysująca kontury każdej struktury na oddzielnym obrazie slice'a - wykorzystywana przy testowaniu modułu.
        :param lw: grubość linii konturu
        :return: None
        """
        for structure in self.structures.values():
            self.draw_structure(structure, lw)

    def set_axes(self, axes):
        """
        Ustawienie obiektu odpowiadającego za rysowanie obrazu przez bibliotekę matplotplib.
        :param axes: obiekt odpowiadający za rysowanie obrazu przez bibliotekę matplotlib
        :return: None
        """
        self.axes = axes


def read_rtstruct(rt_structure_filename):
    """
    Funkcja wczytująca plik DICOM z danymi RTStruct do postaci listy obiektów Structure wyciągniętych z pliku.
    Przetworzenie pliku z danymi RTStruct jest czasochłonne, dlatego raz wyciągnięta z pliku lista struktur przechowywana
    jest w słowniku globalnym loaded_RTStructs - kluczem słownika jest ścieżka pliku z danymi RTStruct.
    :param rt_structure_filename: ścieżka do pliku DICOM z danymi RTStruct
    :return: lista_struktur, nazwa_pacjenta
    """
    rt_structure = pydicom.dcmread(rt_structure_filename)
    structures = []
    try:
        for roiContour, roiStructureSet in zip(rt_structure.ROIContourSequence, rt_structure.StructureSetROISequence):
            structure = Structure()
            try:
                structure.name = roiStructureSet.ROIName # Wyciągnięcie nazwy struktury (np. kości, płuco lewe itp.)
                structure.color = roiContour.ROIDisplayColor # Wyciągnięcie preferowanego koloru konturów struktury
                structure.number = roiContour.ReferencedROINumber # Wyciągnięcie numeru struktury w strukturze pliku RTStruct

                """Utworzenie słownika konturów indeksowanego po współrzędnej 'z' 
                punktów konturu {współrzędna_z_konturu: [lista wektorów punktów konturu]}."""
                structure.contours = {seq.ContourData[2]: [] for seq in roiContour.ContourSequence}
                for seq in roiContour.ContourSequence:
                    structure.contours[seq.ContourData[2]].append(seq.ContourData)
                # structure.contours = {seq.ContourData[2]: seq.ContourData for seq in roiContour.ContourSequence}

                structures.append(structure)
            except AttributeError:
                # Obsługa przypadku, gdy w strukturze brakuje danych konturowych
                print(f"Empty data for {structure}", file=sys.stderr)
    except AttributeError:
        raise NotRTStructFileException("Passed DICOM file is not RTStruct data file")

    # Zapamiętanie struktur z pliku w słowniku globalnym
    loaded_RTStructs[rt_structure_filename] = structures, rt_structure.PatientName

    return structures, rt_structure.PatientName


if __name__ == "__main__":
    read_rtstruct(
        pydicom.read_file(r"Temat6/Pediatric-CT-SEG-02AC04B6/09-21-2005-NA-CT-35474/2.000000-RTSTRUCT-86390/1-1.dcm"))
